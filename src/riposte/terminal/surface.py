"""A deterministic ASCII cell surface rendered by Rich, not a bitmap terminal.

The same cells drive live rendering, plain transcripts and developer evidence.
No private font files, terminal image protocol, HTML or external UI runtime.
"""
from __future__ import annotations
from dataclasses import dataclass
from functools import lru_cache
import textwrap
from rich.segment import Segment
from rich.style import Style

from .palette import PALETTES



def ascii_text(value: object) -> str:
    """Display-only escaping. Untrusted strings cannot emit terminal controls."""
    return "".join(c if 32 <= ord(c) < 127 or c == "\n" else "?" for c in str(value))


@dataclass(frozen=True)
class Cell:
    char: str = " "
    fg: str = "text"
    bg: str = "bg"
    bold: bool = False


@lru_cache(maxsize=4096)
def _style(fg, bg, bold):
    return Style(color=fg, bgcolor="default", bold=bold)


class Surface:
    def __init__(self, width: int, height: int, theme="goks"):
        self.width, self.height = max(1, min(width, 240)), max(1, min(height, 100))
        self.theme = theme if theme in PALETTES else "goks"
        self.palette = PALETTES[self.theme]
        self.cells = [[Cell() for _ in range(self.width)] for _ in range(self.height)]

    def put(self, x, y, char, fg="text", bg=None, bold=False):
        if 0 <= x < self.width and 0 <= y < self.height:
            char = ascii_text(char)[:1]
            if char == "\n" or not char: char = " "
            self.cells[y][x] = Cell(char, fg, "bg", bold)

    def fill(self, x, y, width, height, bg="panel", char=" ", fg="line"):
        for row in range(max(y, 0), min(y + height, self.height)):
            for col in range(max(x, 0), min(x + width, self.width)):
                self.cells[row][col] = Cell(char, fg, "bg")

    def text(self, x, y, text, fg="text", bg=None, bold=False, width=None):
        for dy, line in enumerate(ascii_text(text).splitlines() or [""]):
            for dx, c in enumerate(line[:width] if width is not None else line):
                self.put(x + dx, y + dy, c, fg, bg, bold)

    def wrap(self, x, y, text, width, height=100, fg="muted", bg=None, bold=False):
        if width < 1: return 0
        lines = []
        for paragraph in ascii_text(text).splitlines():
            lines.extend(textwrap.wrap(paragraph, width=width, break_long_words=True, break_on_hyphens=False) or [""])
        for dy, line in enumerate(lines[:height]): self.text(x, y + dy, line, fg, bg, bold)
        return min(len(lines), height)

    def rule(self, y, x=2, width=None, label="", fg="line"):
        width = width if width is not None else self.width - x * 2
        self.text(x, y, "-" * max(0, width), fg)
        if label: self.text(x + 2, y, f" {label} ", "muted")

    def frame(self, x, y, width, height, title="", bg="panel", fg="line"):
        if width < 2 or height < 2: return
        self.fill(x, y, width, height, bg)
        for row in (y, y + height - 1): self.text(x, row, "+" + "-" * (width - 2) + "+", fg, bg)
        for row in range(y + 1, y + height - 1):
            self.put(x, row, "|", fg, bg); self.put(x + width - 1, row, "|", fg, bg)
        if title: self.text(x + 2, y, f" {title} ", "muted", bg, width=width - 4)

    def plain(self): return "\n".join("".join(c.char for c in row) for row in self.cells)

    def __rich_console__(self, console, options):
        palette = self.palette
        width = min(self.width, options.max_width)
        for n, row in enumerate(self.cells):
            run, last = "", None
            for cell in row[:width]:
                key = (palette.get(cell.fg, cell.fg), palette.get(cell.bg, cell.bg), cell.bold)
                if last is not None and key != last:
                    yield Segment(run, _style(*last)); run = ""
                run += cell.char; last = key
            if run: yield Segment(run, _style(*last))
            if n < self.height - 1: yield Segment.line()
