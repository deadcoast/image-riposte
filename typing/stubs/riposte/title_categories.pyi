"""Source-reviewed filename discovery contracts; reports are session-only."""
from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeAlias
import re
from .errors import RiposteError as RiposteError
from .policy import IMAGE_SUFFIXES as IMAGE_SUFFIXES
from .store import check_root as check_root
from .video import VIDEO_SUFFIXES as VIDEO_SUFFIXES

DEFAULT_FILLERS: tuple[str, ...]
MAX_TERMS: int
MAX_CATEGORIES: int
GENERATED_TITLE: re.Pattern[str]
Progress: TypeAlias = Callable[[dict[str, Any]], None]

def title_tokens(text: str) -> tuple[str, ...]: ...
def title_terms(tokens: tuple[str, ...], max_words: int, fillers: frozenset[str]) -> set[str]: ...

@dataclass(frozen=True)
class CategoryDraft:
    label: str
    terms: tuple[str, ...]

def category_drafts(specs: Sequence[str]) -> tuple[CategoryDraft, ...]: ...
def _media_titles(root: Path, counts: Counter[str], progress: Progress | None) -> Iterator[Path]: ...
def discover_categories(root: Path, *, min_count: int=..., max_words: int=..., limit: int=..., sample_limit: int=...,
                        fillers: Sequence[str]=..., ignore: Sequence[str]=..., categories: Sequence[str]=...,
                        progress: Progress | None=...) -> dict[str, Any]: ...
