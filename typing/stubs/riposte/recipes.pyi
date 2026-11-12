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
    ...

def recipe_name(value: object) -> str:
    ...

def checked_settings(value: object, *, partial: bool=False) -> RecipeSettings:
    ...

def to_recipe(settings: RecipeSettings) -> PublishRecipe:
    ...

def _bytes(value: object) -> bytes:
    ...

def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    ...

def load_library(root: Path) -> RecipeLibrary:
    ...

def _entry(library: RecipeLibrary, name: str) -> RecipeEntry | None:
    ...

def _report(library: RecipeLibrary, entry: RecipeEntry | None=None, *, writes: bool=False, stored: bool=True) -> RecipeReport:
    ...

def inspect_recipes(root: Path, name: str | None=None, *, settings: Mapping[str, object] | None=None) -> RecipeReport:
    ...

def save_recipe(root: Path, name: str, settings: Mapping[str, object], *, expected_revision: str) -> RecipeReport:
    ...

def resolve_recipe(root: Path, name: str | None=None, *, revision: str | None=None, overrides: Mapping[str, object] | None=None) -> PublishRecipe:
    ...
MAX_RECIPES: int
MAX_BYTES: int
SETTINGS: frozenset[str]
