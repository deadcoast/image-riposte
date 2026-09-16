# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from .errors import RiposteError as RiposteError
from .lab import trial_report as trial_report
from .metrics import fidelity as fidelity, transform as transform
from .sanitize import encode_clean as encode_clean, png_audit as png_audit, social_render as social_render
from .store import atomic_clean_write as atomic_clean_write, safe_child as safe_child, state_relative as state_relative, workspace_lock as workspace_lock
PROMPTS: tuple[str, ...]

def run_benchmark(root: Path, trial_id: str, model_dir: Path, task: str='edit', seeds: tuple[int, ...]=(7, 19), transforms: tuple[str, ...]=('identity', 'jpeg85', 'resize75'), steps: int=25) -> dict[str, Any]: ...
