"""Private artist masks: immutable content, conservative coverage, tighter caps.

Black preserves pixels; white permits the automatic budget; gray scales it down.
All mask cells whose normalized area overlaps an output pixel participate in
the minimum. Thin protected regions therefore survive downsampling.
"""
from __future__ import annotations
import base64
import binascii
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
from functools import lru_cache
from typing import Mapping, TypedDict
import numpy as np
from numpy.typing import NDArray
from PIL import Image, UnidentifiedImageError
from .errors import RiposteError
MAX_PIXELS = 1048576
MAX_TOTAL_PIXELS = 4194304
MAX_PNG_BYTES = 2097152
RESAMPLING = 'overlap-min-v1'

class ArtistMaskRecord(TypedDict):
    source_sha256: str
    width: int
    height: int
    pixels: str
    sha256: str

class BudgetSummary(TypedDict):
    artist_mask_sha256: str | None
    resampling: str | None
    effective_budget_sha256: str
    width: int
    height: int
    unchanged_pixels: int
    editable_pixels: int
    maximum_channel_change_255: int

class BudgetPreview(BudgetSummary):
    caps_png: str
    overlay_png: str

@dataclass(frozen=True)
class ArtistMask:
    source_sha256: str
    width: int
    height: int
    pixels: bytes

    def __post_init__(self) -> None:
        ...

    @property
    def identity(self) -> str:
        ...

    def public(self) -> ArtistMaskRecord:
        ...

    @classmethod
    def from_dict(cls, value: object) -> ArtistMask:
        ...

    @classmethod
    def from_png(cls, raw: bytes, source_sha256: str) -> ArtistMask:
        ...

    def validate_aspect(self, size: tuple[int, int]) -> None:
        ...

    def raster(self, size: tuple[int, int]) -> NDArray[np.uint8]:
        ...

def checked_masks(masks: tuple[ArtistMask, ...]) -> tuple[ArtistMask, ...]:
    ...

def read_mask(path: Path, source_sha256: str) -> ArtistMask:
    ...

def read_map(path: Path) -> tuple[ArtistMask, ...]:
    ...

def mask_for(masks: tuple[ArtistMask, ...], row: Mapping[str, object]) -> ArtistMask | None:
    ...

def budget_identity(caps: NDArray[np.uint8], mask: ArtistMask | None) -> BudgetSummary:
    ...

def preview(image: Image.Image, caps: NDArray[np.uint8], mask: ArtistMask) -> BudgetPreview:
    ...
