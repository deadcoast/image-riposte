"""Reviewed standalone input inspection and clean snapshot contracts."""
from dataclasses import dataclass
from pathlib import Path as Path
import os
from PIL import Image as Image, UnidentifiedImageError as UnidentifiedImageError
from _riposte_types import Report, Progress
from .errors import RiposteError as RiposteError
from .policy import Policy as Policy, IMAGE_SUFFIXES as IMAGE_SUFFIXES, SIDECAR_SUFFIXES as SIDECAR_SUFFIXES, CACHE_NAMES as CACHE_NAMES, is_link as is_link, same_file_state as same_file_state
from .sanitize import decode_clean as decode_clean, encode_clean as encode_clean, png_audit as png_audit

def _safe_input(path: Path) -> Path: ...
def input_files(paths: list[Path]) -> tuple[list[Path], int]: ...

@dataclass
class InputSource:
    path: Path
    row: Report
    source_stat: os.stat_result
    def snapshot(self, policy: Policy) -> bytes: ...

def inspect_inputs(paths: list[Path], policy: Policy = ..., progress: Progress | None = None) -> tuple[list[InputSource], int]: ...
