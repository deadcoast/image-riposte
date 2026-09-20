"""Private reusable filename rules. Saving rules never authorizes sorting media."""
from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
from typing import Any
import unicodedata
import uuid

from .errors import RiposteError
from .store import check_root, safe_child, state_relative, workspace_lock
from .title_categories import (GENERATED_TITLE, MAX_CATEGORIES, Progress,
                               _media_titles, category_drafts, title_tokens)

MAX_RULE_BYTES = 1_048_576
MISSING_REVISION = "missing"
RESERVED_SLUGS = frozenset({"uncategorized", "con", "prn", "aux", "nul",
                           *(f"com{i}" for i in range(1, 10)), *(f"lpt{i}" for i in range(1, 10))})


@dataclass(frozen=True)
class CategoryRule:
    label: str
    slug: str
    terms: tuple[str, ...]
    exclusions: tuple[str, ...] = ()
    priority: int = 0


@dataclass(frozen=True)
class RuleSet:
    rules: tuple[CategoryRule, ...]
    revision: str


def _slug(value: str) -> str:
    if (not isinstance(value, str) or not 1 <= len(value) <= 80
            or value != "-".join(title_tokens(value)) or value in RESERVED_SLUGS):
        raise RiposteError("CATEGORY_SLUG_INVALID")
    return value


def _terms(values: Any, *, required: bool) -> tuple[str, ...]:
    if not isinstance(values, (list, tuple)) or not int(required) <= len(values) <= 32:
        raise RiposteError("CATEGORY_RULES_INVALID")
    result: set[str] = set()
    for value in values:
        if (not isinstance(value, str) or len(value) > 255
                or any(unicodedata.category(c)[0] == "C" for c in value)):
            raise RiposteError("CATEGORY_RULES_INVALID")
        tokens = title_tokens(value)
        if not 1 <= len(tokens) <= 3 or all(t.isnumeric() for t in tokens):
            raise RiposteError("CATEGORY_RULES_INVALID")
        result.add(" ".join(tokens))
    return tuple(sorted(result))


def rules_document(rules: Sequence[CategoryRule]) -> dict[str, Any]:
    return {"version": 1, "categories": [{**asdict(rule), "terms": list(rule.terms),
                                         "exclusions": list(rule.exclusions)} for rule in rules]}


def _parse_document(document: Any) -> tuple[CategoryRule, ...]:
    if (not isinstance(document, dict) or set(document) != {"version", "categories"}
            or type(document["version"]) is not int or document["version"] != 1
            or not isinstance(document["categories"], list) or len(document["categories"]) > MAX_CATEGORIES):
        raise RiposteError("CATEGORY_RULES_INVALID")
    result: list[CategoryRule] = []
    labels: set[str] = set()
    slugs: set[str] = set()
    for row in document["categories"]:
        if not isinstance(row, dict) or set(row) != {"label", "slug", "terms", "exclusions", "priority"}:
            raise RiposteError("CATEGORY_RULES_INVALID")
        label = row["label"]
        if (not isinstance(label, str) or not 1 <= len(label) <= 80
                or label != unicodedata.normalize("NFKC", label).strip()
                or any(unicodedata.category(c)[0] == "C" for c in label)
                or label.casefold() in labels or label.casefold() == "uncategorized"
                or type(row["priority"]) is not int or not -1_000_000 <= row["priority"] <= 1_000_000):
            raise RiposteError("CATEGORY_RULES_INVALID")
        slug = _slug(row["slug"])
        if slug in slugs:
            raise RiposteError("CATEGORY_SLUG_DUPLICATE")
        labels.add(label.casefold())
        slugs.add(slug)
        terms = _terms(row["terms"], required=True)
        exclusions = _terms(row["exclusions"], required=False)
        if set(terms) & set(exclusions):
            raise RiposteError("CATEGORY_RULE_CONTRADICTION")
        result.append(CategoryRule(label, slug, terms, exclusions, row["priority"]))
    return tuple(sorted(result, key=lambda rule: rule.slug))


def build_rules(categories: Sequence[str], *, exclusions: Sequence[str] = (),
                priorities: Sequence[str] = (), slugs: Sequence[str] = ()) -> tuple[CategoryRule, ...]:
    """Compile explicit groups and Label=value overrides; never infer synonyms."""
    drafts = category_drafts(categories)
    overrides: dict[str, dict[str, str]] = {}
    labels = {draft.label.casefold() for draft in drafts}
    for key, specs in (("exclusions", exclusions), ("priority", priorities), ("slug", slugs)):
        if isinstance(specs, str) or len(specs) > MAX_CATEGORIES:
            raise RiposteError("CATEGORY_RULES_INVALID")
        values: dict[str, str] = {}
        for spec in specs:
            if not isinstance(spec, str) or len(spec) > 8192:
                raise RiposteError("CATEGORY_RULES_INVALID")
            label, separator, value = spec.partition("=")
            label = unicodedata.normalize("NFKC", label.strip()).casefold()
            if not separator or label not in labels or label in values:
                raise RiposteError("CATEGORY_OVERRIDE_INVALID")
            values[label] = value.strip()
        overrides[key] = values
    rules = []
    for draft in drafts:
        label = draft.label.casefold()
        priority = overrides["priority"].get(label, "0")
        if not re.fullmatch(r"-?[0-9]{1,7}", priority):
            raise RiposteError("CATEGORY_PRIORITY_INVALID")
        rules.append(CategoryRule(draft.label, overrides["slug"].get(label, "-".join(title_tokens(draft.label))),
                                  draft.terms, tuple(overrides["exclusions"][label].split(";"))
                                  if label in overrides["exclusions"] else (), int(priority)))
    return _parse_document(rules_document(rules))


def _unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise RiposteError("CATEGORY_RULES_INVALID")
        result[key] = value
    return result


def load_rules(root: Path) -> RuleSet:
    """Read bounded private state without creating a workspace or following links."""
    root = check_root(root)
    path = safe_child(root, state_relative(root, "category-rules.json"))
    try:
        info = path.lstat()
    except FileNotFoundError:
        return RuleSet((), MISSING_REVISION)
    except OSError:
        raise RiposteError("CATEGORY_RULES_UNREADABLE") from None
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size > MAX_RULE_BYTES:
        raise RiposteError("CATEGORY_RULES_INVALID")
    try:
        with path.open("rb") as stream:
            data = stream.read(MAX_RULE_BYTES + 1)
        if len(data) > MAX_RULE_BYTES:
            raise RiposteError("CATEGORY_RULES_INVALID")
        document = json.loads(data.decode("utf-8"), object_pairs_hook=_unique_pairs)
        rules = _parse_document(document)
    except (UnicodeError, ValueError, RecursionError, TypeError):
        raise RiposteError("CATEGORY_RULES_INVALID") from None
    except OSError:
        raise RiposteError("CATEGORY_RULES_UNREADABLE") from None
    return RuleSet(rules, hashlib.sha256(data).hexdigest())


def save_rules(root: Path, rules: Sequence[CategoryRule], *, expected_revision: str) -> RuleSet:
    """Atomically replace only rules after checking the reviewed revision under lock."""
    checked = _parse_document(rules_document(rules))
    if (not isinstance(expected_revision, str)
            or expected_revision != MISSING_REVISION and not re.fullmatch(r"[0-9a-f]{64}", expected_revision)):
        raise RiposteError("CATEGORY_REVISION_REQUIRED")
    root = check_root(root)
    # A stale request must not even create state in a fresh workspace.
    if load_rules(root).revision != expected_revision:
        raise RiposteError("CATEGORY_RULES_CHANGED")
    data = (json.dumps(rules_document(checked), ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(data) > MAX_RULE_BYTES:
        raise RiposteError("CATEGORY_RULES_INVALID")
    with workspace_lock(root):
        if load_rules(root).revision != expected_revision:
            raise RiposteError("CATEGORY_RULES_CHANGED")
        relative = state_relative(root, "category-rules.json")
        dest = safe_child(root, relative)
        temp = dest.parent / (".category-rules-" + uuid.uuid4().hex + ".tmp")
        try:
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Check again after persistence yields to other processes.
            if load_rules(root).revision != expected_revision:
                raise RiposteError("CATEGORY_RULES_CHANGED")
            safe_child(root, relative)
            os.replace(temp, dest)
        finally:
            temp.unlink(missing_ok=True)
    return RuleSet(checked, hashlib.sha256(data).hexdigest())


def match_title(stem: str, rules: Sequence[CategoryRule]) -> dict[str, Any]:
    """Match whole words/phrases; absent or tied matches have no category."""
    if GENERATED_TITLE.fullmatch(unicodedata.normalize("NFKC", stem)):
        return {"status": "ORIGINAL_TITLE_UNAVAILABLE", "category": None, "matches": []}
    tokens = title_tokens(stem)
    terms = {" ".join(tokens[start:start + length]) for start in range(len(tokens))
             for length in range(1, 4) if start + length <= len(tokens)}
    matches: list[dict[str, Any]] = [{"label": rule.label, "slug": rule.slug, "priority": rule.priority,
                "matched_terms": sorted(terms.intersection(rule.terms))}
               for rule in rules if terms.intersection(rule.terms) and not terms.intersection(rule.exclusions)]
    matches.sort(key=lambda row: (-row["priority"], row["slug"]))
    if not matches:
        return {"status": "UNMATCHED", "category": None, "matches": []}
    winners = [row for row in matches if row["priority"] == matches[0]["priority"]]
    return {"status": "MATCHED" if len(winners) == 1 else "AMBIGUOUS",
            "category": {"label": winners[0]["label"], "slug": winners[0]["slug"]} if len(winners) == 1 else None,
            "matches": matches}


def review_matches(root: Path, rules: Sequence[CategoryRule], *, sample_limit: int = 3,
                   progress: Progress | None = None) -> dict[str, Any]:
    """Review filename matches only; bounded examples never become saved assignments."""
    if type(sample_limit) is not int or not 0 <= sample_limit <= 10:
        raise RiposteError("CATEGORY_OPTIONS_INVALID")
    checked = _parse_document(rules_document(rules))
    root = check_root(root)
    counts: Counter[str] = Counter()
    assignments: Counter[str] = Counter()
    samples: dict[str, list[dict[str, Any]]] = {}
    for path in _media_titles(root, counts, progress):
        match = match_title(path.stem, checked)
        status = match["status"]
        counts["analyzed_files"] += 1
        counts[status.lower() + "_files"] += 1
        if match["category"] is not None:
            assignments[match["category"]["slug"]] += 1
        rows = samples.setdefault(status, [])
        if len(rows) < sample_limit:
            rows.append({"filename": path.relative_to(root).as_posix(), **match})
    return {"checkpoint": "INCOMPLETE" if counts["unreadable_files"] or counts["unreadable_directories"] else "COMPLETE",
            "basis": "FILENAME_STEMS_BY_MEDIA_EXTENSION", "media_validated": False,
            "counts": dict(counts), "assignments": dict(assignments), "examples": samples,
            "title_policy": "Generated names do not supply category evidence. Sorting can continue without a category; manual assignment is optional."}


def category_rules(root: Path, *, categories: Sequence[str] = (), exclusions: Sequence[str] = (),
                   priorities: Sequence[str] = (), slugs: Sequence[str] = (), clear: bool = False,
                   save: bool = False, expected_revision: str | None = None, review: bool = False,
                   progress: Progress | None = None) -> dict[str, Any]:
    """Shared CLI/service entry: inspect stored rules, preview a replacement, or save it."""
    if any(type(option) is not bool for option in (clear, save, review)):
        raise RiposteError("CATEGORY_OPTIONS_INVALID")
    supplied = bool(categories) or clear
    if (clear and (categories or exclusions or priorities or slugs)
            or not supplied and (exclusions or priorities or slugs or save)
            or not save and expected_revision is not None):
        raise RiposteError("CATEGORY_OPTIONS_INVALID")
    stored = load_rules(root)
    rules = build_rules(categories, exclusions=exclusions, priorities=priorities, slugs=slugs) if supplied else stored.rules
    if save and expected_revision is None:
        raise RiposteError("CATEGORY_REVISION_REQUIRED")
    # Review/cancellation completes before any explicitly requested save.
    matching = review_matches(root, rules, progress=progress) if review else None
    if save:
        stored = save_rules(root, rules, expected_revision=expected_revision or "")
    return {"mode": "CATEGORY_RULES", "writes": save, "rules_saved": save,
            "status": "SAVED" if save else "DRAFT" if supplied else "STORED" if stored.revision != MISSING_REVISION else "ABSENT",
            "revision": stored.revision, "rules": rules_document(rules), "review": matching,
            "unmatched": None,
            "sorting_enabled": False,
            "next": "Save a reviewed replacement with --save --expected-revision. Then preview sort --categories; applying requires --apply --plan-id from that unchanged preview."}
