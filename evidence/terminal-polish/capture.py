"""Production cell renders on a simulated terminal host; no screenshot claim."""
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


def finish(controller):
    assert controller.state.operation.done.wait(10)
    controller.pump()


with tempfile.TemporaryDirectory(prefix="riposte-polish-capture-") as folder:
    root = Path(folder)
    controller = Controller(root, Presentation(no_animation=True))
    try:
        controller.sorter(); capture(controller, "sorter")
        controller.key(Key("char", "1")); finish(controller); capture(controller, "empty")
        controller.key(Key("enter")); controller.key(Key("char", "g"))
        controller.key(Key("paste", str(root / "missing-folder"))); controller.key(Key("enter"))
        capture(controller, "path-error"); controller.key(Key("escape"))
        source = root / "painting.png"
        Image.new("RGB", (80, 60), (65, 125, 165)).save(source)
        sidecar = root / "painting.xmp"; sidecar.write_text("synthetic retained metadata")
        controller.key(Key("char", "1")); finish(controller); capture(controller, "blocked")
        controller.key(Key("enter")); sidecar.unlink()
        controller.key(Key("char", "1")); finish(controller); capture(controller, "preview")
        controller.key(Key("enter")); capture(controller, "confirmation")
        source.write_bytes(b"changed after preview")
        controller.key(Key("char", "REPLACE")); controller.key(Key("enter")); finish(controller)
        capture(controller, "stale-preview")
        assert source.read_bytes() == b"changed after preview"
        controller.key(Key("char", "g"))
        held = root / "__float__"; held.mkdir()
        controller.key(Key("paste", str(held))); controller.key(Key("enter"))
        controller.key(Key("char", "1")); finish(controller)
        capture(controller, "float-root")
        assert list(held.iterdir()) == []
    finally:
        controller.shutdown()
