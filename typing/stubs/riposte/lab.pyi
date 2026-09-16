# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from PIL.Image import Image as _Image
from _riposte_types import Report, CatalogRow
from _riposte_types import Progress as _Progress
from .errors import RiposteError as RiposteError
from .metrics import difference_image as difference_image, fidelity as fidelity, transport_report as transport_report
from .policy import Policy as Policy
from .sanitize import decode_clean as decode_clean, encode_clean as encode_clean, png_audit as png_audit, social_render as social_render
from .store import atomic_clean_write as atomic_clean_write, check_root as check_root, find_image as find_image, safe_child as safe_child, state_relative as state_relative, workspace_lock as workspace_lock
from PIL import Image
METHODS: set[str]

def _master(root: Path, identifier: str) -> tuple[CatalogRow, _Image]: ...

def _store_trial(root: Path, row: CatalogRow, clean: Image.Image, candidate: Image.Image, report: Report) -> Report: ...

def compare_external(root: Path, identifier: str, candidate_path: Path, max_edge: int=1536, method: str='external') -> dict[str, Any]: ...

def create_candidate(root: Path, identifier: str, vae_dirs: list[Path], max_edge: int=1536, epsilon: int=4, steps: int=48, seed: int=7, progress: _Progress | None=None, engine: str='encoder', pipeline_dir: Path | None=None, device: str='auto', preserve_white: bool=True) -> dict[str, Any]: ...

def trial_report(root: Path, identifier: str) -> dict[str, Any]: ...

def trials(root: Path) -> list[dict[str, Any]]: ...

def export_candidate(root: Path, identifier: str, acknowledge_unverified: bool=False) -> dict[str, Any]: ...

def trial_pixels(root: Path, identifier: str, kind: str, view: str='identity') -> bytes: ...
