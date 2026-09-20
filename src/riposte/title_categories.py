"""Read-only filename discovery and session drafts; no sorting or rule storage."""
from __future__ import annotations

from collections import Counter
from collections.abc import Callable, Iterator, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import re
import stat
import unicodedata

from .errors import RiposteError
from .policy import IMAGE_SUFFIXES
from .store import check_root
from .video import VIDEO_SUFFIXES

DEFAULT_FILLERS = ("a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to", "with")
MAX_TERMS = 100_000
MAX_CATEGORIES = 32
GENERATED_TITLE = re.compile(r"(?:sml|med|lrg|xtl)[0-9]+", re.IGNORECASE)
Progress = Callable[[dict[str, Any]], None]


def title_tokens(text: str) -> tuple[str, ...]:
    """NFKC/casefold words, including combining marks; punctuation is a boundary."""
    normalized = unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", text).casefold())
    words: list[str] = []
    token = ""
    for char in normalized:
        kind = unicodedata.category(char)[0]
        if kind in {"L", "N"} or kind == "M" and token:
            token += char
        elif token:
            words.append(token)
            token = ""
    if token:
        words.append(token)
    return tuple(words)


def title_terms(tokens: tuple[str, ...], max_words: int, fillers: frozenset[str]) -> set[str]:
    """Ignored words/numbers break phrases instead of joining distant words."""
    terms: set[str] = set()
    run: list[str] = []
    for token in tokens:
        if token.isnumeric() or token in fillers:
            run.clear()
            continue
        run.append(token)
        if len(run) > max_words:
            del run[0]
        for length in range(1, len(run) + 1):
            terms.add(" ".join(run[-length:]))
    return terms


@dataclass(frozen=True)
class CategoryDraft:
    label: str
    terms: tuple[str, ...]


def category_drafts(specs: Sequence[str]) -> tuple[CategoryDraft, ...]:
    """Explicit label=term;alias groups. These are not persisted sorting rules."""
    if isinstance(specs, str) or len(specs) > MAX_CATEGORIES:
        raise RiposteError("CATEGORY_DRAFT_INVALID")
    result: list[CategoryDraft] = []
    labels: set[str] = set()
    for spec in specs:
        if not isinstance(spec, str) or len(spec) > 4096 or any(unicodedata.category(c)[0] == "C" for c in spec):
            raise RiposteError("CATEGORY_DRAFT_INVALID")
        label, separator, matchers = spec.partition("=")
        label = unicodedata.normalize("NFKC", label.strip())
        if not separator:
            matchers = label
        if not label or len(label) > 80 or label.casefold() in labels:
            raise RiposteError("CATEGORY_DRAFT_INVALID")
        labels.add(label.casefold())
        terms: set[str] = set()
        for matcher in matchers.split(";"):
            tokens = title_tokens(matcher)
            if not 1 <= len(tokens) <= 3 or all(t.isnumeric() for t in tokens):
                raise RiposteError("CATEGORY_DRAFT_INVALID")
            terms.add(" ".join(tokens))
        if len(terms) > 32:
            raise RiposteError("CATEGORY_DRAFT_INVALID")
        result.append(CategoryDraft(label, tuple(sorted(terms))))
    return tuple(result)


def _media_titles(root: Path, counts: Counter[str], progress: Progress | None) -> Iterator[Path]:
    """Inspect names/stat only, prune private state before descending, fail visibly."""
    from .policy import FLOAT_DIRECTORIES, sort_excluded
    if sort_excluded(root.resolve()):
        return
    def unreadable(_error: OSError) -> None:
        counts["unreadable_directories"] += 1

    def inspect(path: Path, directory: bool) -> os.stat_result | None:
        try:
            info = path.lstat()
        except OSError:
            counts["unreadable_directories" if directory else "unreadable_files"] += 1
            return None
        if stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400):
            counts["linked_paths"] += 1
            return None
        return info

    for directory, dirs, names in os.walk(root, followlinks=False, onerror=unreadable):
        if progress:
            progress({"phase": "Discovering filename categories", "processed": counts["scanned_files"]})
        current = Path(directory)
        if any(inspect(p, True) is None for p in (current, *current.parents)):
            dirs.clear()
            continue
        for name in dirs.copy():
            if name.casefold() in FLOAT_DIRECTORIES:
                dirs.remove(name)
            elif name.casefold() in {".riposte", ".shroud"}:
                dirs.remove(name)
                counts["private_directories"] += 1
            elif inspect(current / name, True) is None:
                dirs.remove(name)
        dirs.sort()
        for name in sorted(names):
            counts["scanned_files"] += 1
            if progress:
                progress({"phase": "Discovering filename categories", "processed": counts["scanned_files"]})
            path = current / name
            info = inspect(path, False)
            if info is None:
                continue
            if not stat.S_ISREG(info.st_mode):
                counts["other_files"] += 1
                continue
            suffix = path.suffix.lower()
            if suffix not in IMAGE_SUFFIXES | VIDEO_SUFFIXES:
                counts["other_files"] += 1
                continue
            counts["eligible_files"] += 1
            counts["videos" if suffix in VIDEO_SUFFIXES else "images"] += 1
            if GENERATED_TITLE.fullmatch(unicodedata.normalize("NFKC", path.stem)):
                counts["original_title_required"] += 1
                continue
            yield path


def discover_categories(root: Path, *, min_count: int = 2, max_words: int = 3,
                        limit: int = 100, sample_limit: int = 3,
                        fillers: Sequence[str] = DEFAULT_FILLERS,
                        ignore: Sequence[str] = (), categories: Sequence[str] = (),
                        progress: Progress | None = None) -> dict[str, Any]:
    """Suggest terms and inspect explicit category drafts without writing anything.

    Eligibility is by image/video extension, not decoding or protection readiness.
    Reports intentionally contain local filename samples; callers must not publish them.
    """
    for option, low, high in ((min_count, 1, 1_000_000_000), (max_words, 1, 3),
                             (limit, 1, 500), (sample_limit, 0, 10)):
        if type(option) is not int or not low <= option <= high:
            raise RiposteError("CATEGORY_OPTIONS_INVALID")
    if isinstance(fillers, str) or isinstance(ignore, str) or len(fillers) > 1000 or len(ignore) > 1000:
        raise RiposteError("CATEGORY_OPTIONS_INVALID")
    filler_tokens: set[str] = set()
    ignored: set[str] = set()
    for collection, destination, maximum in ((fillers, filler_tokens, 1), (ignore, ignored, 3)):
        for value in collection:
            if not isinstance(value, str) or len(value) > 255:
                raise RiposteError("CATEGORY_OPTIONS_INVALID")
            tokens = title_tokens(value)
            if not 1 <= len(tokens) <= maximum:
                raise RiposteError("CATEGORY_OPTIONS_INVALID")
            destination.add(" ".join(tokens))
    drafts = category_drafts(categories)
    root = check_root(root)
    counts: Counter[str] = Counter()
    frequencies: Counter[str] = Counter()
    examples: dict[str, list[str]] = {}
    reviewed: list[dict[str, Any]] = [{"label": draft.label, "terms": list(draft.terms), "count": 0, "examples": []} for draft in drafts]
    overlaps: Counter[tuple[int, int]] = Counter()
    ambiguous_examples: list[dict[str, Any]] = []
    unmatched_examples: list[str] = []
    for path in _media_titles(root, counts, progress):
        relative = path.relative_to(root).as_posix()
        tokens = title_tokens(path.stem)
        terms = title_terms(tokens, max_words, frozenset(filler_tokens)) - ignored
        counts["analyzed_files"] += 1
        for term in terms:
            if term not in frequencies and len(frequencies) >= MAX_TERMS:
                raise RiposteError("CATEGORY_VOCABULARY_LIMIT")
            frequencies[term] += 1
            samples = examples.setdefault(term, [])
            if len(samples) < sample_limit:
                samples.append(relative)
        # Explicit matchers are independent of discovery thresholds and filler choices.
        matches: list[int] = []
        all_terms = {" ".join(tokens[start:start + length])
                     for start in range(len(tokens)) for length in range(1, 4)
                     if start + length <= len(tokens)} if drafts else set()
        for index, draft in enumerate(drafts):
            matched = sorted(all_terms.intersection(draft.terms))
            if not matched:
                continue
            matches.append(index)
            reviewed[index]["count"] += 1
            if len(reviewed[index]["examples"]) < sample_limit:
                reviewed[index]["examples"].append({"filename": relative, "matched_terms": matched})
        if drafts:
            counts["matched_files" if matches else "unmatched_files"] += 1
            if not matches and len(unmatched_examples) < sample_limit:
                unmatched_examples.append(relative)
            if len(matches) > 1:
                counts["ambiguous_files"] += 1
                if len(ambiguous_examples) < sample_limit:
                    ambiguous_examples.append({"filename": relative, "categories": [drafts[i].label for i in matches]})
                for left, a in enumerate(matches):
                    for b in matches[left + 1:]:
                        overlaps[(a, b)] += 1
    if progress:
        progress({"phase": "Ranking filename categories", "processed": counts["analyzed_files"]})
    ranked = sorted((term for term, count in frequencies.items() if count >= min_count),
                    key=lambda term: (-frequencies[term], term))
    total = counts["analyzed_files"]
    incomplete = bool(counts["unreadable_directories"] or counts["unreadable_files"])
    return {"mode": "TITLE_CATEGORY_DISCOVERY", "writes": False, "rules_saved": False,
            "checkpoint": "INCOMPLETE" if incomplete else "COMPLETE", "counts": dict(counts),
            "basis": "FILENAME_STEMS_BY_MEDIA_EXTENSION", "media_validated": False,
            "settings": {"min_count": min_count, "max_words": max_words, "limit": limit,
                         "sample_limit": sample_limit, "fillers": sorted(filler_tokens), "ignore": sorted(ignored)},
            "candidate_count": len(ranked), "omitted_candidates": max(0, len(ranked) - limit),
            "candidates": [{"term": term, "count": frequencies[term], "coverage": frequencies[term] / total,
                            "examples": examples[term]} for term in ranked[:limit]],
            "review": {"status": "SESSION_DRAFT", "categories": reviewed,
                       "overlaps": [{"categories": [drafts[a].label, drafts[b].label], "count": count}
                                    for (a, b), count in sorted(overlaps.items())],
                       "ambiguous_examples": ambiguous_examples, "unmatched_examples": unmatched_examples,
                       "unmatched_proposal": "Standard date/media/size; no category required"},
            "next": "Edit category groups and rerun to review. Use category-rules with the same groups to preview and explicitly save reusable rules. Then preview sort --categories before applying its exact plan.",
            "title_policy": "Generated SML/MED/LRG/XTL names are excluded from keyword discovery. They can still be sorted without a category; manual assignment is optional."}
