"""Named publishing settings; saving configuration never grants operation consent."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import TypedDict, cast
import unicodedata
import uuid

from .errors import RiposteError
from .publication import PublishRecipe
from .quality import QualityLimits
from .release_guard import ReleaseConfig
from .store import check_root, safe_child, state_relative, workspace_lock

MAX_RECIPES = 64
MAX_BYTES = 262_144
SETTINGS = frozenset({'edges', 'epsilon', 'steps', 'restarts', 'seed', 'preserve_white', 'delta_e76_p95', 'rms_fraction'})


class RecipeSettings(TypedDict):
    edges: list[int]
    epsilon: int
    steps: int
    restarts: int
    seed: int
    preserve_white: bool
    delta_e76_p95: float
    rms_fraction: float


class RecipeEntry(TypedDict):
    name: str
    settings: RecipeSettings


class RecipeSummary(RecipeEntry):
    recipe_revision: str


class RecipeReport(TypedDict):
    mode: str
    version: int
    revision: str
    writes: bool
    status: str
    recipes: list[RecipeSummary]
    name: str | None
    settings: RecipeSettings | None
    recipe_revision: str | None
    processing_started: bool


@dataclass(frozen=True)
class RecipeLibrary:
    entries: tuple[RecipeEntry, ...]
    revision: str


def defaults() -> RecipeSettings:
    return {'edges': [1536], 'epsilon': 4, 'steps': 24, 'restarts': 2, 'seed': 7,
            'preserve_white': True, 'delta_e76_p95': 6.0, 'rms_fraction': .95}


def recipe_name(value: object) -> str:
    if not isinstance(value, str):
        raise RiposteError('RECIPE_NAME_INVALID')
    name = unicodedata.normalize('NFKC', value).strip()
    if (not 1 <= len(name) <= 64 or not name[0].isalnum()
            or any(not (unicodedata.category(c)[0] in 'LNM' or c in ' _-') for c in name)):
        raise RiposteError('RECIPE_NAME_INVALID')
    return name


def checked_settings(value: object, *, partial: bool = False) -> RecipeSettings:
    """Reject unknown/private fields and coercion before using engine validation."""
    if not isinstance(value, Mapping) or not set(value) <= SETTINGS or (not partial and set(value) != SETTINGS):
        raise RiposteError('RECIPE_SETTINGS_INVALID')
    data: dict[str, object] = {**defaults(), **value}
    if (not isinstance(data['edges'], (list, tuple))
            or any(type(data[k]) is not int for k in ('epsilon', 'steps', 'restarts', 'seed'))
            or type(data['preserve_white']) is not bool
            or any(type(data[k]) not in (int, float) for k in ('delta_e76_p95', 'rms_fraction'))):
        raise RiposteError('RECIPE_SETTINGS_INVALID')
    settings = cast(RecipeSettings, data)
    settings['edges'] = list(settings['edges'])
    try:
        if not math.isfinite(settings['delta_e76_p95']) or not math.isfinite(settings['rms_fraction']):
            raise ValueError()
        to_recipe(settings)
    except (RiposteError, TypeError, ValueError, OverflowError):
        raise RiposteError('RECIPE_SETTINGS_INVALID') from None
    return settings


def to_recipe(settings: RecipeSettings) -> PublishRecipe:
    return PublishRecipe(tuple(settings['edges']),
                         ReleaseConfig(steps=settings['steps'], restarts=settings['restarts'], seed=settings['seed']),
                         QualityLimits(epsilon_255=settings['epsilon'], preserve_white=settings['preserve_white'],
                                       delta_e76_p95=settings['delta_e76_p95'], rms_fraction=settings['rms_fraction']))


def _bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2, allow_nan=False) + '\n').encode('utf-8')


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise RiposteError('RECIPE_LIBRARY_INVALID')
        result[key] = value
    return result


def load_library(root: Path) -> RecipeLibrary:
    """Bounded read only; validate the entire library, including unselected rows."""
    root = check_root(root)
    path = safe_child(root, state_relative(root, 'publishing-recipes.json'))
    try:
        info = path.lstat()
    except FileNotFoundError:
        return RecipeLibrary((), 'missing')
    except OSError:
        raise RiposteError('RECIPE_LIBRARY_UNREADABLE') from None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_BYTES:
        raise RiposteError('RECIPE_LIBRARY_INVALID')
    try:
        with path.open('rb') as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise RiposteError('RECIPE_LIBRARY_INVALID')
        document = json.loads(raw.decode('utf-8'), object_pairs_hook=_unique)
        if (not isinstance(document, dict) or set(document) != {'version', 'recipes'}
                or type(document['version']) is not int or document['version'] != 1):
            raise RiposteError('RECIPE_LIBRARY_INVALID')
        rows = document['recipes']
        if not isinstance(rows, list) or len(rows) > MAX_RECIPES:
            raise RiposteError('RECIPE_LIBRARY_INVALID')
        entries: list[RecipeEntry] = []
        names: set[str] = set()
        for row in rows:
            if not isinstance(row, dict) or set(row) != {'name', 'settings'}:
                raise RiposteError('RECIPE_LIBRARY_INVALID')
            name = recipe_name(row['name'])
            if name != row['name'] or name.casefold() in names:
                raise RiposteError('RECIPE_LIBRARY_INVALID')
            names.add(name.casefold())
            entries.append({'name': name, 'settings': checked_settings(row['settings'])})
    except (RiposteError, UnicodeError, ValueError, TypeError, RecursionError, OverflowError):
        raise RiposteError('RECIPE_LIBRARY_INVALID') from None
    except OSError:
        raise RiposteError('RECIPE_LIBRARY_UNREADABLE') from None
    return RecipeLibrary(tuple(sorted(entries, key=lambda r: r['name'].casefold())), hashlib.sha256(raw).hexdigest())


def _entry(library: RecipeLibrary, name: str) -> RecipeEntry | None:
    return next((row for row in library.entries if row['name'].casefold() == name.casefold()), None)


def _report(library: RecipeLibrary, entry: RecipeEntry | None = None, *, writes: bool = False, stored: bool = True) -> RecipeReport:
    return {'mode': 'PUBLISHING_RECIPES', 'version': 1, 'revision': library.revision, 'writes': writes,
            'status': 'SAVED' if writes else 'STORED' if stored else 'DRAFT',
            'recipes': [{'name': row['name'], 'settings': row['settings'], 'recipe_revision': hashlib.sha256(_bytes(row)).hexdigest()} for row in library.entries],
            'name': entry['name'] if entry else None, 'settings': entry['settings'] if entry else None,
            'recipe_revision': hashlib.sha256(_bytes(entry)).hexdigest() if entry else None,
            'processing_started': False}


def inspect_recipes(root: Path, name: str | None = None, *, settings: Mapping[str, object] | None = None) -> RecipeReport:
    library = load_library(root)
    if name is None:
        if settings is not None:
            raise RiposteError('RECIPE_NAME_REQUIRED')
        return _report(library)
    name = recipe_name(name)
    old = _entry(library, name)
    if settings is None:
        if old is None:
            raise RiposteError('RECIPE_NOT_FOUND')
        return _report(library, old)
    supplied = checked_settings(settings, partial=True)
    supplied_values: Mapping[str, object] = supplied
    merged = checked_settings({**(old['settings'] if old else defaults()), **{k: supplied_values[k] for k in settings}})
    return _report(library, {'name': name, 'settings': merged}, stored=False)


def save_recipe(root: Path, name: str, settings: Mapping[str, object], *, expected_revision: str) -> RecipeReport:
    """Save one reviewed named entry, preserving unrelated recipes and media."""
    name = recipe_name(name)
    checked = checked_settings(settings)
    if (not isinstance(expected_revision, str)
            or expected_revision != 'missing' and not re.fullmatch(r'[0-9a-f]{64}', expected_revision)):
        raise RiposteError('RECIPE_REVISION_REQUIRED')
    root = check_root(root)
    if load_library(root).revision != expected_revision:
        raise RiposteError('RECIPE_LIBRARY_CHANGED')
    with workspace_lock(root):
        library = load_library(root)
        if library.revision != expected_revision:
            raise RiposteError('RECIPE_LIBRARY_CHANGED')
        entry: RecipeEntry = {'name': name, 'settings': checked}
        entries = [row for row in library.entries if row['name'].casefold() != name.casefold()] + [entry]
        if len(entries) > MAX_RECIPES:
            raise RiposteError('RECIPE_LIBRARY_FULL')
        entries.sort(key=lambda row: row['name'].casefold())
        data = _bytes({'version': 1, 'recipes': entries})
        if len(data) > MAX_BYTES:
            raise RiposteError('RECIPE_LIBRARY_FULL')
        relative = state_relative(root, 'publishing-recipes.json')
        dest = safe_child(root, relative)
        temporary = dest.parent / ('.publishing-recipes-' + uuid.uuid4().hex + '.tmp')
        try:
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            if load_library(root).revision != expected_revision:
                raise RiposteError('RECIPE_LIBRARY_CHANGED')
            safe_child(root, relative)
            os.replace(temporary, dest)
        except OSError:
            raise RiposteError('RECIPE_SAVE_FAILED') from None
        finally:
            temporary.unlink(missing_ok=True)
    return _report(RecipeLibrary(tuple(entries), hashlib.sha256(data).hexdigest()), entry, writes=True)


def resolve_recipe(root: Path, name: str | None = None, *, revision: str | None = None,
                   overrides: Mapping[str, object] | None = None) -> PublishRecipe:
    """Resolve a fresh named snapshot and explicit edits before any processing."""
    base = defaults()
    if name is not None:
        report = inspect_recipes(root, name)
        if revision is not None and revision != report['recipe_revision']:
            raise RiposteError('RECIPE_CHANGED')
        base = cast(RecipeSettings, report['settings'])
    elif revision is not None:
        raise RiposteError('RECIPE_NAME_REQUIRED')
    edits = dict(overrides or {})
    checked_settings(edits, partial=True)
    return to_recipe(checked_settings({**base, **edits}))
