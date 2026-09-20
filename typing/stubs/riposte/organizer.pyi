# Source-derived external stub; see typing/README.md for scope.
from typing import Iterator, Sequence
from pathlib import Path
from .catalog_guard import CatalogGuard as CatalogGuard
from _riposte_types import CatalogRow, OrganizationPlan, OrganizationReport, WorkspaceAudit
from _riposte_types import Progress as _Progress
from .errors import RiposteError as RiposteError
from .locking import LEASE_NAME as LEASE_NAME
from .policy import CACHE_NAMES as CACHE_NAMES, IMAGE_SUFFIXES as IMAGE_SUFFIXES, Policy as Policy, SIDECAR_SUFFIXES as SIDECAR_SUFFIXES, folder_for as folder_for, is_link as is_link, same_file_state as same_file_state
from .sanitize import decode_clean as decode_clean, encode_clean as encode_clean, png_audit as png_audit
from .store import atomic_clean_write as atomic_clean_write, catalog as catalog, check_root as check_root, record_image as record_image, safe_child as safe_child, state_name as state_name, workspace_lock as workspace_lock, write_report as write_report
from .policy import sort_folder_for as sort_folder_for
from .store import connect as connect
from .video import VIDEO_SUFFIXES as VIDEO_SUFFIXES, inspect_video as inspect_video, video_catalog as video_catalog, record_video as record_video, file_hash as file_hash
from .sort_history import SortHistory as SortHistory, copy_exclusive as copy_exclusive, pending_sort as pending_sort, undo_sort as undo_sort
Progress = _Progress

def walk_inputs(root: Path) -> Iterator[tuple[Path, str]]: ...

def known_good(root: Path) -> dict[str, CatalogRow]: ...

def _validate_managed(path: Path, row: CatalogRow) -> bool: ...

def plan(root: Path, policy: Policy=..., progress: Progress | None=None, *, categories: bool=..., assignments: Sequence[str]=...) -> OrganizationPlan: ...

def _next_relative(root: Path, folder: Path, suffix: str=..., *, next_numbers: dict[Path, int] | None=...) -> str: ...

def organize(root: Path, policy: Policy=..., progress: Progress | None=None, *, categories: bool=..., assignments: Sequence[str]=..., plan_id: str | None=...) -> OrganizationReport: ...

def audit_workspace(root: Path) -> WorkspaceAudit: ...

from .sort_titles import title_records as title_records
from .title_categories import GENERATED_TITLE as GENERATED_TITLE
from .policy import path_category as path_category
