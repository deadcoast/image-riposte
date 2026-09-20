"""Capture production cells on a simulated terminal host, not native screenshots."""
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


def capture(controller, name):
    for width, height in [(72, 24), (100, 34)]:
        surface = render(controller.state, width, height)
        image = Image.new("RGB", (width*10, height*21), "#20242a")
        draw = ImageDraw.Draw(image)
        for y, row in enumerate(surface.cells):
            for x, cell in enumerate(row):
                color = surface.palette.get(cell.fg, cell.fg)
                if color == "default": color = "#D8DEE9"
                draw.text((x*10, y*21), cell.char, font=bold if cell.bold else font, fill=color)
        stem = f"{name}-{width}x{height}"
        image.save(HERE / (stem + ".png"))
        (HERE / (stem + ".txt")).write_text(surface.plain(), encoding="utf-8")


with tempfile.TemporaryDirectory(prefix="riposte-sorting-research-") as folder:
    root = Path(folder)
    for name in ("SML01.png", "holiday.png", "forestOak.png", "forestPine.png", "forestMoss.png", "factoryWall.png", "factoryPipe.png", "factoryFloor.png"):
        Image.new("RGB", (80, 60), (65, 125, 165)).save(root / name)
    controller = Controller(root, Presentation(no_animation=True))
    try:
        controller.sorter(); capture(controller, "sorter")
        controller.key(Key("char", "1"))
        assert controller.state.operation.done.wait(10)
        controller.pump()
        assert controller.state.page.result["ready"]
        capture(controller, "preview")
        controller.state.page.scroll = 30
        capture(controller, "patterns")
        controller.state.page.scroll = 0
        controller.key(Key("enter")); capture(controller, "confirmation")
    finally:
        controller.shutdown()
