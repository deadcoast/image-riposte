"""Production terminal cells rendered on a simulated host, not a screenshot."""
from pathlib import Path
import tempfile

from PIL import Image, ImageDraw, ImageFont
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render

HERE = Path(__file__).parent
font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 16)
bold = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 16)
with tempfile.TemporaryDirectory(prefix="riposte-sorter-capture-") as folder:
    root = Path(folder)
    for n in range(30): (root / f"image-folder-{n:02d}").mkdir()
    controller = Controller(root, Presentation(no_animation=True))
    try:
        for name, width, height in [("home-small", 72, 24), ("sorter-small", 72, 24),
                                    ("sorter-wide", 100, 34), ("picker-small", 72, 24)]:
            if name == "sorter-small": controller.sorter()
            if name == "picker-small":
                controller.key(Key("char", "b"))
                controller.state.height = height
                controller.key(Key("pagedown"))
            surface = render(controller.state, width, height)
            image = Image.new("RGB", (width*10, height*21), "#20242a")
            draw = ImageDraw.Draw(image)
            for y, row in enumerate(surface.cells):
                for x, cell in enumerate(row):
                    color = surface.palette.get(cell.fg, cell.fg)
                    if color == "default": color = "#D8DEE9"
                    draw.text((x*10, y*21), cell.char, font=bold if cell.bold else font, fill=color)
            image.save(HERE / (name + ".png"))
            (HERE / (name + ".txt")).write_text(surface.plain(), encoding="utf-8")
    finally:
        controller.shutdown()
