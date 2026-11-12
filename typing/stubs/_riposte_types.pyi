from riposte.spatial import ArtistMaskRecord, BudgetSummary
"""Type-only records derived from source; never import this module at runtime.

Report and ModelTensor mark unresolved dynamic JSON and optional ML boundaries.
They do not certify report validation, tensor shapes, or model execution.
"""
from riposte.records import (ProgressEvent as ProgressEvent, PngAudit as PngAudit,
                             CatalogRow as CatalogRow, ImageInfo as ImageInfo, RequestValues as RequestValues)
from collections.abc import Callable, Sequence
from pathlib import Path
import os
from typing import Any, Literal, NotRequired, Protocol, TypeAlias, TypedDict, TypeVar

JSONValue: TypeAlias = None | bool | int | float | str | list[JSONValue] | dict[str, JSONValue]
Report: TypeAlias = dict[str, Any]
ModelTensor: TypeAlias = Any
SizeBin: TypeAlias = Literal["SML", "MED", "LRG", "XTL"]
DateSource: TypeAlias = Literal["embedded", "filesystem_creation", "filesystem_modified"]
# The existing "words" parser preserves sequence elements without coercion.
FormValue: TypeAlias = str | bool | int | float | tuple[object, ...]


Progress: TypeAlias = Callable[[ProgressEvent], None]



class OrganizationPlan(TypedDict):
    category_sorting: NotRequired[bool]
    plan_id: str
    rules_revision: NotRequired[str]
    files: list[dict[str, Any]]
    mode: Literal["READ_ONLY"]
    counts: dict[str, int]
    destinations: dict[str, int]
    blockers: dict[str, int]
    ready: bool
    source_policy: str
    video_policy: Literal["SORT_ONLY_BYTES_UNCHANGED"]

class OrganizationReport(TypedDict):
    mode: Literal["APPLY"]
    counts: dict[str, int]
    blockers: dict[str, int]
    unmanaged_or_changed_remaining: int
    checkpoint: Literal["COMPLETE", "INCOMPLETE"]
    metadata_policy: Literal["DATE_ONLY_IMAGES"]
    source_backups: Literal["PRIVATE_UNDO_HISTORY"]
    video_policy: Literal["SORT_ONLY_BYTES_UNCHANGED"]
    sort_id: str | None

class WorkspaceAudit(TypedDict):
    checkpoint: Literal["COMPLETE", "INCOMPLETE"]
    verified_images: int
    verified_videos: int
    verified_artifacts: int
    blockers: dict[str, int]
    metadata_policy: Literal["DATE_ONLY_IMAGES"]
    video_policy: Literal["SORT_ONLY_BYTES_UNCHANGED"]
    ai_protection: Literal["NOT_ESTABLISHED_BY_METADATA_AUDIT"]

class VideoInfo(TypedDict):
    day: str
    date_source: str
    width: int
    height: int
    sha256: str
    bytes: int
    source_stat: os.stat_result

class UndoSortReport(TypedDict):
    mode: Literal["UNDO_SORT_PREVIEW", "UNDO_SORT"]
    ready: bool
    blockers: dict[str, int]
    sort_id: NotRequired[str]
    checkpoint: NotRequired[Literal["COMPLETE", "INCOMPLETE"]]
    files_to_restore: NotRequired[int]
    outputs_to_remove: NotRequired[int]
    recovery_metadata: NotRequired[Literal["ORIGINAL_NAMES_AND_METADATA"]]
    scope: NotRequired[str]

class UpgradeReport(TypedDict):
    mode: Literal["STATE_UPGRADE"]
    status: Literal["ALREADY_CURRENT", "UPGRADED"]
    artwork_rewritten: Literal[0]
    catalog_ids_preserved: NotRequired[Literal[True]]
    state_directory: NotRequired[Literal[".riposte"]]

class FidelityReport(TypedDict):
    psnr_db: float | None
    identical_pixels: bool
    rmse_255: float
    max_channel_delta_255: int
    mean_channel_delta_255: float
    edge_error_255: float

class TransportRow(FidelityReport):
    transform: str

class TransportReport(TypedDict):
    evidence_level: Literal["PIXEL_TRANSPORT_ONLY"]
    ai_protection: Literal["UNVERIFIED"]
    profiles: str
    rows: list[TransportRow]

class QualityPolicy(TypedDict):
    epsilon_255: int
    preserve_white: bool
    rms_fraction: float
    delta_e76_p95: float
    tile_size: int

class QualityReport(FidelityReport):
    spatial_budget: NotRequired[BudgetSummary]
    status: Literal["PASS", "BLOCKED"]
    policy: QualityPolicy
    blockers: list[str]
    worst_tile_rmse_255: float
    delta_e76_p95: float
    budget_violating_pixels: int
    protected_pixels_changed: int
    visual_approval: Literal["REQUIRED"]
    ai_protection: Literal["UNVERIFIED"]
    scope: str

class ReleaseSettings(TypedDict):
    steps: int
    restarts: int
    seed: int
    step_255: float
    checkpoint_every: int
    frequency_weight: float

class RecipeRecord(TypedDict):
    masks: NotRequired[list[ArtistMaskRecord]]
    edges: tuple[int, ...]
    guard: ReleaseSettings
    quality: QualityPolicy

class PublicationTask(TypedDict):
    artist_mask_sha256: NotRequired[str]
    image_id: str
    date: str
    max_edge: int
    source_clean_sha256: str
    index: int

class PublicationPlan(TypedDict):
    budget_previews: NotRequired[list[Report]]
    budget_revision: NotRequired[str]
    budget_preview_total: NotRequired[int]
    budget_preview_offset: NotRequired[int]
    mode: Literal["PUBLICATION_PLAN"]
    images: int
    outputs: int
    duplicate_renders_avoided: int
    tasks: list[PublicationTask]
    recipe: RecipeRecord
    master_changes: Literal[0]
    ai_protection: Literal["UNVERIFIED"]
    writes: Literal[False]
    source_mode: NotRequired[Literal["snapshot"]]
    ignored_files: NotRequired[int]
    originals_preserved: NotRequired[Literal[True]]

class PublicationItem(TypedDict):
    id: str
    image_id: str
    max_edge: int
    date: str
    status: Literal["PENDING", "READY_FOR_REVIEW", "BLOCKED"]
    review: str
    relative: NotRequired[str]
    width: NotRequired[int]
    height: NotRequired[int]
    quality: NotRequired[QualityReport]
    artifact_sha256: NotRequired[dict[str, str]]
    transport: NotRequired[TransportReport]
    code: NotRequired[str]

class PublicationSummary(TypedDict):
    id: str
    sequence: int
    status: str
    counts: dict[str, int]
    ai_protection: Literal["UNVERIFIED"]

class PublicationBatch(PublicationSummary):
    mode: Literal["PUBLICATION_BATCH"]
    items: list[PublicationItem]
    recipe: Report
    master_changes: Literal[0]
    duplicate_renders_avoided: int
    source_mode: Literal["catalog", "snapshot"]
    ignored_files: int
    workflow: NotRequired[Literal["SORT_RIPOSTE"]]
    sorting: NotRequired[OrganizationReport]

class PublicationExport(TypedDict):
    relative: str
    bytes: int
    sha256: str
    contents: Literal["APPROVED_DATE_ONLY_PNGS"]
    ai_protection: Literal["UNVERIFIED"]



class Encoder(Protocol):
    def __call__(self, x: ModelTensor, /) -> ModelTensor: ...

EncoderT = TypeVar("EncoderT", bound=Encoder)

class InpaintProbe(Protocol):
    def __call__(self, x: ModelTensor, keep: ModelTensor, seed: int,
                 early_fraction: float, prompt_key: str, /) -> ModelTensor: ...

class TemporalProbe(Protocol):
    def __call__(self, x: ModelTensor, seed: int, /) -> ModelTensor: ...

class ContentFilterFlags(TypedDict):
    content_filter_reported: bool
    content_filter_flags: list[bool] | None

class JobStarted(TypedDict):
    job_id: str

class JobCancelled(TypedDict):
    status: Literal["CANCEL_REQUESTED"]
    boundary: Literal["NEXT_MODEL_OR_ITERATION_CHECKPOINT"]

class VaeInspection(TypedDict):
    kind: str
    weights_format: Literal["safetensors"]
    weight_files: int
    weight_bytes: int
    scope: Literal["DISTILLED_ENCODER_PROXY", "ENCODER_PROXY"]
    preflight: Literal["FILES_PRESENT_NOT_EXECUTED"]
    ai_protection: Literal["UNVERIFIED"]
    weights_sha256: NotRequired[str]
    configuration_sha256: NotRequired[str]

class RuntimeCapabilities(TypedDict):
    versions: dict[str, str]
    missing: list[str]
    cpu: Literal[True]
    cuda: bool
    mps: bool
    recommended_device: str
    model_loading: Literal["EXPLICIT_LOCAL_ONLY"]
    privacy: Literal["NO_IMAGE_UPLOADS"]
    pretrained_qualification: Literal["NOT_IMPLIED_BY_PREFLIGHT"]
    cuda_memory_mib: NotRequired[dict[str, int]]
    runtime_code: NotRequired[str]
