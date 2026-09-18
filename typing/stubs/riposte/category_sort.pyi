"""Exact-plan records contain dynamic per-file media/matching evidence."""
from pathlib import Path
from typing import Any, Callable, Sequence
from .category_rules import load_rules as load_rules, match_title as match_title
from .errors import RiposteError as RiposteError
from .policy import Policy as Policy, sort_folder_for as sort_folder_for
from .sanitize import decode_clean as decode_clean, encode_clean as encode_clean, png_audit as png_audit
from .sort_history import latest_sort as latest_sort
from .sort_titles import title_records as title_records
from .store import check_root as check_root, safe_child as safe_child
from .video import file_hash as file_hash, inspect_video as inspect_video
from .title_categories import GENERATED_TITLE as GENERATED_TITLE

def source_state(path: Path) -> list[int]: ...
def verify_source(root: Path, item: dict[str, Any]) -> None: ...
def category_plan(root: Path, policy: Policy, *, assignments: Sequence[str] = ..., progress: Callable[[dict[str, Any]], None] | None = ...) -> dict[str, Any]: ...
