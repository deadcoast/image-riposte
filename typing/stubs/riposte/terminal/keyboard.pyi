# Source-derived external stub; see typing/README.md for scope.
from typing import Any, TextIO, Self
import codecs
from dataclasses import dataclass

@dataclass(frozen=True)
class Key:
    name: str
    text: str = ...
SEQUENCES: dict[str, str]
SINGLE: dict[str, str]

class KeyDecoder:
    buffer: str
    pasting: bool
    paste: str
    _paste_tail: str

    def __init__(self) -> None: ...

    def feed(self, value: str) -> None: ...

    def next(self, flush_escape: bool=False) -> Key | None: ...

class TerminalKeys:
    stream: TextIO
    output: TextIO
    decoder: KeyDecoder
    _unicode: codecs.IncrementalDecoder
    _saved: list[Any] | None
    _windows_prefix: str | None
    active: bool

    def __init__(self, stream: TextIO | None=None, output: TextIO | None=None) -> None: ...

    def __enter__(self) -> Self: ...

    def __exit__(self, *exc: object) -> None: ...

    def read(self, timeout: float=0.08) -> Key | None: ...
