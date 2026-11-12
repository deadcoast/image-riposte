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

MAX_PIXELS = 1_048_576
MAX_TOTAL_PIXELS = 4_194_304
MAX_PNG_BYTES = 2_097_152
RESAMPLING = "overlap-min-v1"


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
        if (not isinstance(self.source_sha256, str)
                or re.fullmatch(r"[0-9a-f]{64}", self.source_sha256) is None
                or type(self.width) is not int or type(self.height) is not int
                or not 1 <= self.width <= 4096 or not 1 <= self.height <= 4096
                or self.width * self.height > MAX_PIXELS
                or type(self.pixels) is not bytes or len(self.pixels) != self.width * self.height):
            raise RiposteError("ARTIST_MASK_INVALID")

    @property
    def identity(self) -> str:
        header = f"riposte-artist-mask-1:{RESAMPLING}:{self.source_sha256}:{self.width}:{self.height}:".encode("ascii")
        return hashlib.sha256(header + self.pixels).hexdigest()

    def public(self) -> ArtistMaskRecord:
        return {"source_sha256": self.source_sha256, "width": self.width, "height": self.height,
                "pixels": base64.b64encode(self.pixels).decode("ascii"), "sha256": self.identity}

    @classmethod
    def from_dict(cls, value: object) -> ArtistMask:
        try:
            if not isinstance(value, dict) or set(value) != {"source_sha256", "width", "height", "pixels", "sha256"}:
                raise ValueError
            if not isinstance(value["pixels"], str) or len(value["pixels"]) > (MAX_PIXELS + 2) // 3 * 4:
                raise ValueError
            mask = cls(value["source_sha256"], value["width"], value["height"], base64.b64decode(value["pixels"], validate=True))
            if value["sha256"] != mask.identity or mask.public() != value:
                raise ValueError
            return mask
        except (ValueError, TypeError, binascii.Error):
            raise RiposteError("ARTIST_MASK_INVALID") from None

    @classmethod
    def from_png(cls, raw: bytes, source_sha256: str) -> ArtistMask:
        try:
            if len(raw) > MAX_PNG_BYTES:
                raise ValueError
            with Image.open(io.BytesIO(raw)) as image:
                if (image.format != "PNG" or image.mode != "L" or getattr(image, "n_frames", 1) != 1
                        or image.width * image.height > MAX_PIXELS or max(image.size) > 4096
                        or "transparency" in image.info or image.getexif().get(274, 1) != 1):
                    raise ValueError
                return cls(source_sha256, image.width, image.height, image.tobytes())
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            raise RiposteError("ARTIST_MASK_PNG_INVALID") from None

    def validate_aspect(self, size: tuple[int, int]) -> None:
        # Permit the one-cell rounding needed when an artist reduces a large
        # canvas to a bounded mask. No crop, rotate or orientation guessing.
        if abs(self.width * size[1] - self.height * size[0]) > max(size):
            raise RiposteError("ARTIST_MASK_ASPECT_MISMATCH")

    @lru_cache(maxsize=4)
    def raster(self, size: tuple[int, int]) -> NDArray[np.uint8]:
        width, height = size
        if min(size) < 1 or max(size) > 4096:
            raise RiposteError("GUARD_DIMENSIONS_INVALID")
        source = np.frombuffer(self.pixels, dtype=np.uint8).reshape(self.height, self.width)
        horizontal = np.empty((self.height, width), dtype=np.uint8)
        for x in range(width):
            lo, hi = x * self.width // width, ((x + 1) * self.width + width - 1) // width
            horizontal[:, x] = source[:, lo:hi].min(axis=1)
        output = np.empty((height, width), dtype=np.uint8)
        for y in range(height):
            lo, hi = y * self.height // height, ((y + 1) * self.height + height - 1) // height
            output[y] = horizontal[lo:hi].min(axis=0)
        output.setflags(write=False)
        return output


def checked_masks(masks: tuple[ArtistMask, ...]) -> tuple[ArtistMask, ...]:
    if (not isinstance(masks, tuple) or len(masks) > 200
            or any(not isinstance(mask, ArtistMask) for mask in masks)
            or sum(len(mask.pixels) for mask in masks) > MAX_TOTAL_PIXELS
            or len({mask.source_sha256 for mask in masks}) != len(masks)):
        raise RiposteError("ARTIST_MASK_SELECTION_INVALID")
    return masks


def read_mask(path: Path, source_sha256: str) -> ArtistMask:
    from .intake import _safe_input
    try:
        with _safe_input(path).open("rb") as stream:
            return ArtistMask.from_png(stream.read(MAX_PNG_BYTES + 1), source_sha256)
    except OSError:
        raise RiposteError("ARTIST_MASK_UNREADABLE") from None


def read_map(path: Path) -> tuple[ArtistMask, ...]:
    from .intake import _safe_input
    try:
        with _safe_input(path).open("rb") as stream:
            raw = stream.read(6_000_001)
        if len(raw) > 6_000_000:
            raise ValueError
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) != {"schema", "masks"} or type(value["schema"]) is not int or value["schema"] != 1 or not isinstance(value["masks"], list):
            raise ValueError
        return checked_masks(tuple(ArtistMask.from_dict(item) for item in value["masks"]))
    except (OSError, ValueError, TypeError):
        raise RiposteError("ARTIST_MASK_INVALID") from None


def mask_for(masks: tuple[ArtistMask, ...], row: Mapping[str, object]) -> ArtistMask | None:
    mask = next((item for item in masks if item.source_sha256 == row["sha256"]), None)
    if mask is not None:
        mask.validate_aspect((int(str(row["width"])), int(str(row["height"]))))
    return mask


def budget_identity(caps: NDArray[np.uint8], mask: ArtistMask | None) -> BudgetSummary:
    return {"artist_mask_sha256": mask.identity if mask else None,
            "resampling": RESAMPLING if mask else None,
            "effective_budget_sha256": hashlib.sha256(f"{caps.shape[1]}:{caps.shape[0]}:".encode() + caps.tobytes()).hexdigest(),
            "width": caps.shape[1], "height": caps.shape[0],
            "unchanged_pixels": int((caps == 0).sum()), "editable_pixels": int((caps > 0).sum()),
            "maximum_channel_change_255": int(caps.max())}


def preview(image: Image.Image, caps: NDArray[np.uint8], mask: ArtistMask) -> BudgetPreview:
    """Exact-size cap raster plus a bounded artwork overlay; private, no writes."""
    stream = io.BytesIO()
    Image.fromarray(caps).save(stream, format="PNG")
    actual = np.asarray(image.convert("RGB"), dtype=np.float32)
    weights = mask.raster(image.size)
    # Stronger cyan overlay denotes more restraint; original remains visible.
    alpha = (1 - weights.astype(np.float32) / 255)[..., None] * .65
    overlay = Image.fromarray(np.rint(actual * (1 - alpha) + np.array([0, 220, 210]) * alpha).astype(np.uint8))
    overlay.thumbnail((768, 768), Image.Resampling.LANCZOS)
    rendered = io.BytesIO(); overlay.save(rendered, format="PNG")
    return {**budget_identity(caps, mask), "caps_png": base64.b64encode(stream.getvalue()).decode("ascii"),
            "overlay_png": base64.b64encode(rendered.getvalue()).decode("ascii")}
