"""Bounded, deterministic filename evidence. Abstention never blocks sorting.

NPMI anchor neighbourhoods are a lexical heuristic, not semantic communities or
calibrated probabilities. No filesystem writes, external models or dependencies.
"""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
import hashlib
from itertools import combinations
import json
import math
import re
import unicodedata
from pathlib import Path

from .errors import RiposteError
from .policy import category_slug
from .title_categories import DEFAULT_FILLERS, GENERATED_TITLE, Progress, title_terms, title_tokens

VERSION = "filename-corpus-1"
MIN_SUPPORT = 3
MIN_FAMILIES = 6
MAX_COVERAGE = .8
MIN_ASSOCIATION = .3
MIN_SCORE = .6
MIN_MARGIN = .15
MAX_FAMILIES = 50_000
MAX_VOCABULARY = 100_000
MAX_PAIRS = 200_000
MAX_FILE_TERMS = 48
MAX_GROUPS = 32
NOISE = frozenset((*DEFAULT_FILLERS, "", "img", "dsc", "dscf", "pxl", "image", "photo",
                   "copy", "edit", "edited", "final", "export", "tmp", "temp"))
NOISE_PATTERN = re.compile(r"(?:v[0-9]{1,4}|final[0-9]*|copy[0-9]*|[0-9]{3,5}x[0-9]{3,5}|"
                           r"(?:2|4|8|16)k|(?:img|dsc|dscf|pxl)[0-9]+|[a-f0-9]{16,})\Z")


def filename_tokens(stem: str) -> tuple[str, ...]:
    """Keep product identifiers and Unicode; split visible CamelCase boundaries."""
    text = unicodedata.normalize("NFKC", stem)
    text = re.sub(r"(?<=[A-Z])(?=[A-Z][a-z])", " ", text)
    text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    return title_tokens(text)


def rule_terms(stem: str) -> set[str]:
    """Preserve existing explicit-rule matches while adding CamelCase matches."""
    return {" ".join(tokens[start:start + length])
            for tokens in (title_tokens(stem), filename_tokens(stem))
            for start in range(len(tokens)) for length in range(1, 4)
            if start + length <= len(tokens)}


def semantic_terms(stem: str) -> frozenset[str]:
    if GENERATED_TITLE.fullmatch(unicodedata.normalize("NFKC", stem)):
        return frozenset()
    text = re.sub(r"(?i)(?<![a-z0-9])[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}(?![a-z0-9])", " 0 ", stem)
    tokens = tuple("" if NOISE_PATTERN.fullmatch(t) else t for t in filename_tokens(text))
    return frozenset(title_terms(tokens, 3, NOISE))


def association(joint: int, left: int, right: int, total: int) -> float:
    """NPMI with explicit absent and ubiquitous-pair handling."""
    if not joint or not total:
        return -1.0
    if joint == total:
        return 0.0  # Universal terms provide no partition evidence.
    return math.log(joint * total / (left * right)) / -math.log(joint / total)


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
    score: float = 0.0
    margin: float = 0.0
    matched_terms: tuple[str, ...] = ()
    alternatives: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class CorpusModel:
    status: str
    categories: tuple[CorpusCategory, ...]
    weights: dict[str, float]
    families: int
    titles: int
    pairs: int
    revision: str

    def report(self) -> dict[str, object]:
        return {"version": VERSION, "status": self.status, "revision": self.revision,
                "normalized_families": self.families, "titles": self.titles, "observed_pairs": self.pairs,
                "categories": [{**asdict(c), "terms": list(c.terms)} for c in self.categories],
                "score_kind": "IDF_COVERAGE_NOT_PROBABILITY",
                "settings": {"min_support": MIN_SUPPORT, "min_families": MIN_FAMILIES,
                             "max_coverage": MAX_COVERAGE, "min_npmi": MIN_ASSOCIATION,
                             "min_score": MIN_SCORE, "min_margin": MIN_MARGIN,
                             "max_families": MAX_FAMILIES, "max_vocabulary": MAX_VOCABULARY,
                             "max_pairs": MAX_PAIRS, "max_file_terms": MAX_FILE_TERMS, "max_groups": MAX_GROUPS},
                "fallback": "Ordinary year/month/media/size; existing categories remain."}

    def match(self, stem: str) -> CorpusMatch:
        if self.status != "READY":
            return CorpusMatch(self.status, None)
        terms = semantic_terms(stem)
        if len(terms) > MAX_FILE_TERMS:
            return CorpusMatch("TITLE_LIMIT", None)
        observed = terms.intersection(self.weights)
        total = math.fsum(self.weights[t] for t in sorted(observed))
        if not total:
            return CorpusMatch("NO_EVIDENCE", None)
        ranked = sorted(((math.fsum(self.weights[t] for t in c.terms if t in observed) / total, c)
                         for c in self.categories), key=lambda row: (-row[0], row[1].slug))
        score, best = ranked[0]
        margin = score - (ranked[1][0] if len(ranked) > 1 else 0.0)
        matched = tuple(t for t in best.terms if t in observed)
        # Association alone needs at least two independently present words.
        anchored = best.label in matched or len({w for t in matched for w in t.split()}) >= 2
        status = "MATCHED" if anchored and score >= MIN_SCORE and margin >= MIN_MARGIN else "UNCERTAIN"
        return CorpusMatch(status, best if status == "MATCHED" else None, round(score, 6), round(margin, 6),
                           matched, tuple((c.slug, round(s, 6)) for s, c in ranked[:3] if s > 0))


def build_corpus(titles: Iterable[str], *, excluded: Iterable[str] = (), preferred: Iterable[str] = (),
                 progress: Progress | None = None) -> CorpusModel:
    """Sparse observed pairs, deduplicated normalized families, bounded storage.

    A limit discards automatic proposals, never returns a truncated authoritative
    taxonomy. Explicit rules and ordinary sorting remain available to the caller.
    """
    families: set[frozenset[str]] = set()
    frequencies: Counter[str] = Counter()
    pairs: Counter[tuple[str, str]] = Counter()
    seen = 0

    def finish(status: str, categories: tuple[CorpusCategory, ...] = ()) -> CorpusModel:
        weights = {t: math.log((1 + len(families)) / (1 + frequencies[t])) + 1
                   for t in sorted({t for c in categories for t in c.terms})}
        basis = [VERSION, status, [asdict(c) for c in categories], weights, len(families), seen, len(pairs),
                 MIN_SUPPORT, MIN_FAMILIES, MAX_COVERAGE, MIN_ASSOCIATION, MIN_SCORE, MIN_MARGIN,
                 MAX_FAMILIES, MAX_VOCABULARY, MAX_PAIRS, MAX_FILE_TERMS, MAX_GROUPS]
        revision = hashlib.sha256(json.dumps(basis, ensure_ascii=True, sort_keys=True).encode()).hexdigest()
        return CorpusModel(status, categories, weights, len(families), seen, len(pairs), revision)

    for title in titles:
        seen += 1
        if progress and seen % 128 == 1:
            progress({"phase": "Reading filename patterns", "processed": seen})
        terms = semantic_terms(Path(title).stem)
        if len(terms) > MAX_FILE_TERMS:
            return finish("LIMIT_REACHED")
        if not terms or terms in families:
            continue
        if len(families) >= MAX_FAMILIES:
            return finish("LIMIT_REACHED")
        families.add(terms)
        frequencies.update(terms)
        if len(frequencies) > MAX_VOCABULARY:
            return finish("LIMIT_REACHED")
    n = len(families)
    if n < MIN_FAMILIES:
        return finish("INSUFFICIENT_EVIDENCE")
    excluded_terms = set(excluded)
    preferred_terms = {t.replace("-", " ") for t in preferred}
    valid = {t for t, count in frequencies.items() if MIN_SUPPORT <= count
             and (count <= n * MAX_COVERAGE or t in preferred_terms)
             and t not in excluded_terms}
    words = {t: frozenset(t.split()) for t in valid}
    # No dense V*V graph and no tautological phrase/constituent edges.
    for index, terms in enumerate(families):
        if progress and index % 128 == 0:
            progress({"phase": "Comparing filename patterns", "processed": index})
        for left, right in combinations(sorted(terms & valid), 2):
            if words[left] & words[right]:
                continue
            pairs[left, right] += 1
            if len(pairs) > MAX_PAIRS:
                return finish("LIMIT_REACHED")
    graph: dict[str, dict[str, float]] = {t: {} for t in sorted(valid)}
    for (left, right), joint in sorted(pairs.items()):
        weight = association(joint, frequencies[left], frequencies[right], n)
        if joint >= MIN_SUPPORT and weight >= MIN_ASSOCIATION:
            graph[left][right] = weight
            graph[right][left] = weight
    ranked = sorted(valid, key=lambda t: (t not in preferred_terms, -frequencies[t], -math.fsum(graph[t].values()), -len(words[t]), t))
    used: set[str] = set()
    covered: dict[str, int] = {}
    categories: list[CorpusCategory] = []
    for anchor in ranked:
        if anchor in used:
            continue
        owners = {covered.get(word) for word in words[anchor]}
        if (anchor not in preferred_terms and len(words[anchor]) > 1
                and len(owners) == 1 and None not in owners
                and all(frequencies[word] == frequencies[anchor] for word in words[anchor])):
            # A phrase whose equally frequent words already share one group is
            # the same evidence, not a second competing folder proposal.
            continue
        try:
            slug = category_slug(anchor.replace(" ", "-"))
        except RiposteError:
            continue
        if slug == "uncategorized" or slug in excluded_terms:
            continue
        neighbours = sorted((t for t in graph[anchor] if t not in used and t not in preferred_terms),
                            key=lambda t: (-graph[anchor][t], -frequencies[t], t))[:11]
        members = tuple(sorted({anchor, *neighbours}))
        used.update(members)
        covered.update((term, len(categories)) for term in members)
        # Equivalent constituent features should not create duplicate categories.
        for term in members:
            parts = term.split()
            equivalents = {" ".join(parts[start:start + length]) for start in range(len(parts))
                           for length in range(1, len(parts))
                           if start + length <= len(parts)
                           and " ".join(parts[start:start + length]) not in preferred_terms
                           and frequencies[" ".join(parts[start:start + length])] == frequencies[term]}
            used.update(equivalents)
            covered.update((term, len(categories)) for term in equivalents)
        identifier = hashlib.sha256((VERSION + ":" + anchor).encode()).hexdigest()[:16]
        categories.append(CorpusCategory(identifier, anchor, slug, members, frequencies[anchor]))
        if len(categories) > MAX_GROUPS:
            return finish("LIMIT_REACHED")
    return finish("READY" if categories else "INSUFFICIENT_EVIDENCE", tuple(sorted(categories, key=lambda c: c.slug)))
