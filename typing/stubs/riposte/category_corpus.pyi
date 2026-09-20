"""Source-derived lexical heuristics, bounded evidence and non-blocking abstention."""
from collections.abc import Iterable
from dataclasses import dataclass
import re
from .title_categories import Progress as Progress

VERSION: str
MIN_SUPPORT: int
MIN_FAMILIES: int
MAX_COVERAGE: float
MIN_ASSOCIATION: float
MIN_SCORE: float
MIN_MARGIN: float
MAX_FAMILIES: int
MAX_VOCABULARY: int
MAX_PAIRS: int
MAX_FILE_TERMS: int
MAX_GROUPS: int
NOISE: frozenset[str]
NOISE_PATTERN: re.Pattern[str]

def filename_tokens(stem: str) -> tuple[str, ...]: ...
def rule_terms(stem: str) -> set[str]: ...
def semantic_terms(stem: str) -> frozenset[str]: ...
def association(joint: int, left: int, right: int, total: int) -> float: ...

@dataclass(frozen=True)
class CorpusCategory:
    identifier: str
    label: str
    slug: str
    terms: tuple[str, ...]
    support: int

@dataclass(frozen=True)
class CorpusMatch:
    status: str
    category: CorpusCategory | None
    score: float = ...
    margin: float = ...
    matched_terms: tuple[str, ...] = ...
    alternatives: tuple[tuple[str, float], ...] = ...

@dataclass(frozen=True)
class CorpusModel:
    status: str
    categories: tuple[CorpusCategory, ...]
    weights: dict[str, float]
    families: int
    titles: int
    pairs: int
    revision: str
    def report(self) -> dict[str, object]: ...
    def match(self, stem: str) -> CorpusMatch: ...

def build_corpus(titles: Iterable[str], *, excluded: Iterable[str] = ..., preferred: Iterable[str] = ..., progress: Progress | None = ...) -> CorpusModel: ...
