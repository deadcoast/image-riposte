"""Read-only ordinary receipt contracts; dynamic file records remain explicit."""
from pathlib import Path
from typing import Any, Callable
from .category_sort import source_state as source_state, verify_source as verify_source
from .errors import RiposteError as RiposteError
from .policy import Policy as Policy, path_category as path_category, sort_folder_for as sort_folder_for
from .sanitize import decode_clean as decode_clean, encode_clean as encode_clean, png_audit as png_audit
from .sort_history import latest_sort as latest_sort
from .sort_titles import title_records as title_records
from .store import check_root as check_root
from .title_categories import GENERATED_TITLE as GENERATED_TITLE
from .video import file_hash as file_hash, inspect_video as inspect_video

def receipt(basis: dict[str, Any]) -> str: ...
def verify_sort_source(root: Path, item: dict[str, Any]) -> None: ...
def ordinary_plan(root: Path, policy: Policy, progress: Callable[[dict[str, Any]], None] | None = ...) -> dict[str, Any]: ...
