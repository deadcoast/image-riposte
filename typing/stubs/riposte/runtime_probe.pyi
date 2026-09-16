# Source-derived external stub; see typing/README.md for scope.
from typing import Any
from pathlib import Path
from _riposte_types import Report, Encoder
from _riposte_types import Progress as _Progress
from .errors import RiposteError as RiposteError

def probe_encoder(encoder: Encoder) -> Report: ...

def execute_local_probe(vae_dirs: list[Path], device: str='auto', progress: _Progress | None=None) -> dict[str, Any]: ...
