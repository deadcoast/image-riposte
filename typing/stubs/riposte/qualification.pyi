from _riposte_types import EncoderT
# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from PIL.Image import Image as _Image
from _riposte_types import Report, Encoder
from _riposte_types import Progress as _Progress
from .errors import RiposteError as RiposteError
from .metrics import fidelity as fidelity
from .sanitize import encode_clean as encode_clean, png_audit as png_audit
from .store import atomic_clean_write as atomic_clean_write, safe_child as safe_child, state_relative as state_relative, workspace_lock as workspace_lock
from .views import HOLDOUT_VIEWS as HOLDOUT_VIEWS, TRAIN_VIEWS as TRAIN_VIEWS, image_tensor as image_tensor, keep_mask as keep_mask, matched_control as matched_control, publication_view as publication_view
from PIL import Image
CONTROL_SEEDS: tuple[int, ...]
EVAL_MASKS: tuple[str, ...]

def evaluate_pair(clean: Image.Image, candidate: Image.Image, encoders: list[EncoderT], training_identities: list[Report] | None=None, control_seeds: tuple[int, ...]=..., progress: _Progress | None=None, optimization_views: list[str] | None=None, optimization_masks: list[str] | None=None) -> dict[str, Any]: ...

def _verified_pair(root: Path, trial: str) -> tuple[Report, dict[str, _Image]]: ...

def qualify_trial(root: Path, trial_id: str, vae_dirs: list[Path], device: str='auto', progress: _Progress | None=None) -> dict[str, Any]: ...

def evaluations(root: Path, trial_id: str) -> list[dict[str, Any]]: ...
