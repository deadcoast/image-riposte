# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from _riposte_types import VaeInspection, RuntimeCapabilities
from _riposte_types import Report, ModelTensor
from .errors import RiposteError as RiposteError
from .policy import is_link as is_link
VAE_CLASSES: set[str]
DEPENDENCIES: tuple[str, ...]

def offline() -> None: ...

def read_config(path: Path) -> dict[str, Any]: ...

def _weights(folder: Path) -> list[Path]: ...

def model_fingerprint(folder: Path) -> str: ...

def inspect_vae(folder: Path, fingerprint: bool=False) -> VaeInspection: ...

def runtime_capabilities() -> RuntimeCapabilities: ...

def select_device(requested: str='auto') -> str: ...

class LocalEncoder:
    identity: Report
    device: str
    kind: str
    model: Any
    factor: int

    def __init__(self, folder: Path, device: str='auto') -> None: ...

    def __call__(self, x: ModelTensor) -> ModelTensor: ...
PROMPTS: dict[str, str]

class LocalInpaintProbe:
    device: str
    vae: Any
    unet: Any
    scheduler: Any
    embeddings: Any
    factor: int
    scaling: float
    timesteps: Any
    identity: Report

    def __init__(self, folder: Path, device: str='auto') -> None: ...

    def __call__(self, x: ModelTensor, keep: ModelTensor, seed: int, early_fraction: float, prompt_key: str) -> ModelTensor: ...
