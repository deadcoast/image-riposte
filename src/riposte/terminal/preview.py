"""Optional ASCII thumbnails of verified images, never substitutes for pixel review."""
from __future__ import annotations
import io
from dataclasses import dataclass, field
from PIL import Image
from .surface import Surface


@dataclass
class Preview:
    image: Image.Image
    cache: dict = field(default_factory=dict)


def make_preview(raw: bytes) -> Preview:
    with Image.open(io.BytesIO(raw)) as source:
        rgba = source.convert("RGBA")
        image = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
        image.alpha_composite(rgba)
        image = image.convert("RGB")
        image.thumbnail((256, 128), Image.Resampling.LANCZOS)
    return Preview(image)


def paint_preview(surface: Surface, raw: Preview, x: int, y: int, width: int, height: int):
    if width < 2 or height < 2: return
    image = raw.image
    aspect = image.width / image.height
    cols = min(width, max(1, round(height * 2 * aspect)))
    rows = min(height, max(1, round(cols / (2 * aspect))))
    key = (cols, rows)
    if key not in raw.cache:
        if len(raw.cache) > 4: raw.cache.clear()
        sampled = image.resize((cols, rows), Image.Resampling.LANCZOS)
        glyphs = "@%#ox+=:,. "
        cells = []
        for py in range(rows):
            row = []
            for px in range(cols):
                r, g, b = sampled.getpixel((px, py))
                lum = .2126*r + .7152*g + .0722*b
                row.append((glyphs[min(10, int(lum / 256 * 11))], f"#{r:02x}{g:02x}{b:02x}"))
            cells.append(row)
        raw.cache[key] = cells
    ox, oy = x + (width - cols) // 2, y + (height - rows) // 2
    for py, row in enumerate(raw.cache[key]):
        for px, (char, colour) in enumerate(row):
            if surface.theme == "mono":
                colour = "default"
            elif surface.theme in {"goks", "dark"}:
                # A dark ink outline cannot be printed as black on a host-owned
                # dark terminal. Lift glyph tones; actual PNG viewing is unchanged.
                values = [int(colour[i:i+2],16) for i in (1,3,5)]
                colour = "#" + "".join(f"{round(112 + value * 143/255):02x}" for value in values)
            surface.put(ox + px, oy + py, char, colour)
