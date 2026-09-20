"""Source-derived fixed local Kontext editing and named-asset identity."""
from collections.abc import Mapping
from fractions import Fraction
from pathlib import Path
from typing import Protocol
from PIL import Image
from .errors import RiposteError as RiposteError
from .models import offline as offline, read_config as read_config
from .policy import is_link as is_link

KIND: str
RESOLUTIONS: tuple[tuple[int, int], ...]
COMPONENTS: dict[str, tuple[str, tuple[str, ...]]]

def target_size(width: int, height: int) -> tuple[int, int]: ...
def prepare(image: Image.Image) -> Image.Image: ...
def conditioning() -> dict[str, object]: ...
def bundle_identity(folder: Path) -> dict[str, object]: ...

class _Pipeline(Protocol):
    def to(self, device: str) -> _Pipeline: ...
    def set_progress_bar_config(self, *, disable: bool) -> None: ...
    def __call__(self, **kwargs: object) -> object: ...

class KontextGenerator:
    pipeline: _Pipeline
    identity: dict[str, object]
    last_flags: dict[str, object]
    def __init__(self, folder: Path) -> None: ...
    def __call__(self, image: Image.Image, seed: int, steps: int) -> list[Image.Image]: ...
