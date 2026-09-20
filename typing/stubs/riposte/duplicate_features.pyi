"""Source-derived duplicate analysis contract; scores are evidence, not probabilities."""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Literal
import numpy as np
from numpy.typing import NDArray
from PIL import Image

@dataclass(frozen=True)
class View:
    name: str
    rotation: int
    mirror: bool
    box: tuple[int, int, int, int]
    phash: int
    coverage: float
    aspect: float

@dataclass(frozen=True)
class Visual:
    pixels: NDArray[np.uint8]
    width: int
    height: int
    views: tuple[View, ...]
    timestamp: float | None = ...

def luminance(pixels: NDArray[np.uint8]) -> NDArray[np.float64]:
    ...

def informative(pixels: NDArray[np.uint8]) -> bool:
    ...

def phash(pixels: NDArray[np.uint8]) -> int:
    ...

def view_pixels(visual: Visual, view: View) -> NDArray[np.uint8]:
    ...

def describe(image: Image.Image, *, crops: bool=..., timestamp: float | None=...) -> Visual:
    ...

def structural(left: NDArray[np.float64], right: NDArray[np.float64]) -> float:
    ...

def compare_views(left: Visual, lv: View, right: Visual, rv: View) -> dict[str, object] | None:
    ...
