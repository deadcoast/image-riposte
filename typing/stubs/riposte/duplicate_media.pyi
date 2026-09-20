"""Source-derived duplicate analysis contract; scores are evidence, not probabilities."""
from __future__ import annotations
from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import time
from PIL import Image
from .duplicate_features import Visual, describe
from .errors import RiposteError
from .policy import Policy
from .records import Progress
from .sanitize import decode_clean

@dataclass(frozen=True)
class Signature:
    width: int
    height: int
    pixel_sha256: str | None
    frames: tuple[Visual, ...]
    duration: float | None = ...

def normalized_image(path: Path, max_pixels: int=...) -> Image.Image:
    ...

def image_signature(path: Path, *, max_pixels: int=...) -> Signature:
    ...

def equal_pixels(left: Path, right: Path, *, max_pixels: int=...) -> bool:
    ...

def local_process(args: list[str], *, limit: int, progress: Progress | None=...) -> bytes:
    ...

def video_probe(path: Path, progress: Progress | None=...) -> tuple[int, int, float]:
    ...

def video_frame(path: Path, timestamp: float, *, edge: int=..., progress: Progress | None=...) -> Image.Image:
    ...

def video_signature(path: Path, *, progress: Progress | None=...) -> Signature:
    ...

def sampled_frame(path: Path, timestamp: float, *, edge: int=..., progress: Progress | None=...) -> tuple[Image.Image, float]:
    ...

def thumbnail(path: Path, *, media: str, timestamp: float | None=...) -> bytes:
    ...
