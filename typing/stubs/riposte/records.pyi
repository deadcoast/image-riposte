"""Source-owned records for shared operation and media boundaries.

These annotations describe existing values. Runtime validation, consent and
filesystem checks remain with the producing/consuming operations.
"""
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from os import stat_result
from typing import Literal, NotRequired, TypeAlias, TypedDict

class ProgressEvent(TypedDict, total=False):
    phase: str
    processed: int
    total: int
    item: int
    items: int
    branch: int
    branches: int
    batch_id: str
    state: str

class PngAudit(TypedDict):
    date: str
    width: int
    height: int
    chunks: list[str]
    metadata: Literal["DATE_ONLY"]
    sha256: str

class ImageSource(TypedDict):
    id: str
    relative: str
    day: str
    width: int
    height: int
    sha256: str

class CatalogRow(ImageSource):
    date_source: str
    bytes: int

class MediaInfo(TypedDict):
    day: str
    date_source: str
    width: int
    height: int
    sha256: str
    bytes: int
    source_stat: NotRequired[stat_result]
    id: NotRequired[str]
    relative: NotRequired[str]

class ImageInfo(PngAudit):
    mode: Literal["VERIFIED_IMAGE"]
    viewer: Literal["NOT_OPENED", "HANDOFF_REQUESTED"]
    relative: NotRequired[str]

class RequestValues(TypedDict, total=False):
    visual: bool
    videos: bool
    include_float: bool
    max_files: int
    max_visual: int
    max_pairs: int
    max_findings: int
    max_file_bytes: int
    duplicate_report: Path | str | None
    plan_id: str | None
    input_paths: Sequence[Path | str]
    image_id: str
    image_ids: list[str] | tuple[str, ...]
    all_images: bool
    batch_id: str | None
    item_id: str
    item_ids: list[str] | tuple[str, ...]
    trial_id: str | None
    run_id: str
    ratings: Path | str
    trial_ids: Sequence[str]
    cohort_id: str
    panel_id: str
    reviewer_id: str
    run_ids: Sequence[str]
    reviewers: int
    rubric: Path | str
    sample_size: int
    relative: str
    vae_dirs: Sequence[Path | str]
    model: Path | str
    candidate: Path | str
    inpaint: Path | str | None
    video: Path | str | None
    edges: list[int] | tuple[int, ...]
    epsilon: int
    steps: int
    restarts: int
    seed: int
    seeds: list[int] | tuple[int, ...]
    views: list[str] | tuple[str, ...]
    max_edge: int
    device: str
    engine: str
    task: str
    method: str
    date_mode: str
    discard_sidecars: bool
    preserve_white: bool
    delta_e76_p95: float
    rms_fraction: float
    decision: str
    visual_accepted: bool
    acknowledge_unverified: bool
    execute: bool
    kind: str
    view: str
    open_viewer: bool
    year: str | None
    month: str | int | None
    size: str | None
    search: str
    limit: int | None
    offset: int
    categories: bool
    assignments: Sequence[str]
    sort_id: str | None
    category_specs: Sequence[str]
    exclusions: Sequence[str]
    priorities: Sequence[str]
    slugs: Sequence[str]
    clear: bool
    review: bool
    expected_revision: str | None
    min_count: int
    max_words: int
    fillers: str | Sequence[str]
    ignore: Sequence[str]

# Consumers inspect callbacks without mutating a producer's event record.
Progress: TypeAlias = Callable[[Mapping[str, object]], None]


class PreviewSortOptions(TypedDict, total=False):
    categories: bool
    assignments: Sequence[str]

class SortOptions(PreviewSortOptions, total=False):
    plan_id: str | None


class SelectionFilters(TypedDict, total=False):
    year: str | None
    month: str | int | None
    size: str | None


class ListOptions(SelectionFilters, total=False):
    search: str
    limit: int | None
    offset: int

