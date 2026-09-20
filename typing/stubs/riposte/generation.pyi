# Source-derived external stub; see typing/README.md for scope.
from . import __version__ as __version__
from typing import Any
from collections.abc import Mapping, Sequence
from pathlib import Path
from PIL.Image import Image as _Image
from _riposte_types import Report
from _riposte_types import Progress as _Progress
from .errors import RiposteError as RiposteError
from .metrics import fidelity as fidelity
from .models import model_fingerprint as model_fingerprint, offline as offline, read_config as read_config, configuration_fingerprint as configuration_fingerprint
from .kontext import KIND as KONTEXT_KIND, KontextGenerator as KontextGenerator, prepare as prepare_kontext
from .experiment import begin_experiment as begin_experiment, finish_experiment as finish_experiment, conditioning as conditioning, _object as _object, _text as _text
from .records import Progress as Progress
from .qualification import CONTROL_SEEDS as CONTROL_SEEDS, _verified_pair as _verified_pair
from .sanitize import encode_clean as encode_clean, png_audit as png_audit, social_render as social_render
from .store import atomic_clean_write as atomic_clean_write, atomic_json_write as atomic_json_write, safe_child as safe_child, state_relative as state_relative, workspace_lock as workspace_lock
from .views import HOLDOUT_VIEWS as HOLDOUT_VIEWS, TRAIN_VIEWS as TRAIN_VIEWS, matched_control as matched_control, publication_view as publication_view
from PIL import Image
from _riposte_types import ContentFilterFlags
ALLOWED_COMPONENTS: dict[str, set[str]]

class LocalGenerator:
    pipeline: Any
    task: str
    identity: dict[str, object]

    def __init__(self, folder: Path, task: str) -> None: ...
    last_flags: ContentFilterFlags

    def __call__(self, image: Image.Image, seed: int, steps: int) -> list[Image.Image]: ...

def prepare_input(image: Image.Image, task: str, model: Mapping[str, object] | None = None) -> Image.Image: ...

def frame_motion(frames: list[Image.Image]) -> float | None: ...

def _validate(task: str, seeds: Sequence[int], views: Sequence[str], steps: int) -> None: ...

def controlled_generation(root: Path, trial_id: str, model_dir: Path, task: str='edit', seeds: tuple[int, ...]=(7, 19), views: tuple[str, ...]=('identity', 'jpeg70'), steps: int=25, progress: _Progress | None=None) -> dict[str, Any]: ...

def _execute(root: Path, trial: Mapping[str, object], pair: dict[str, _Image], generator: LocalGenerator, task: str, seeds: Sequence[int], views: Sequence[str], steps: int, progress: _Progress | None, experiment: Mapping[str, object] | None = None, *, sequence: int | None = None) -> dict[str, object]: ...

def generation_report(root: Path, identifier: str) -> dict[str, Any]: ...

def generation_runs(root: Path, trial_id: str) -> list[dict[str, Any]]: ...

def generation_frame(root: Path, identifier: str, relative: str) -> bytes: ...
