# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from _riposte_types import Report, ModelTensor
from .errors import RiposteError as RiposteError
from .models import model_fingerprint as model_fingerprint, offline as offline, read_config as read_config, select_device as select_device
from .models import configuration_fingerprint as configuration_fingerprint
from .policy import is_link as is_link
from dataclasses import dataclass

@dataclass(frozen=True)
class TemporalConfig:
    width: int = ...
    height: int = ...
    frames: int = ...
    generation_steps: int = ...
    fps: int = ...
    motion_bucket: int = ...
    noise_augmentation: float = ...
    guidance_max: float = ...

    def __post_init__(self) -> None: ...

def letterbox_tensor(x: ModelTensor, width: int, height: int) -> ModelTensor: ...

def v_prediction_original(sample: ModelTensor, velocity: ModelTensor, sigma: ModelTensor) -> ModelTensor: ...

class LocalTemporalProbe:
    sigma: float
    initial_sigma: float
    device: str
    config: TemporalConfig
    dtype: Any
    vae: Any
    unet: Any
    image_encoder: Any
    timestep: ModelTensor
    factor: int
    clip_size: int
    mean: ModelTensor
    std: ModelTensor
    identity: Report

    def __init__(self, folder: Path, device: str='auto', config: TemporalConfig=...) -> None: ...

    def __call__(self, x: ModelTensor, seed: int) -> ModelTensor: ...
