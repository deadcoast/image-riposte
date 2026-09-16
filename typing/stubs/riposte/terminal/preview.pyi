# Source-derived external stub; see typing/README.md for scope.
from .surface import Surface as Surface
from PIL import Image
from dataclasses import dataclass, field

@dataclass
class Preview:
    image: Image.Image
    cache: dict[tuple[int, int], list[list[tuple[str, str]]]] = field(default_factory=dict)

def make_preview(raw: bytes) -> Preview: ...

def paint_preview(surface: Surface, raw: Preview, x: int, y: int, width: int, height: int) -> None: ...
