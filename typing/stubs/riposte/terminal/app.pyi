# Source-derived external stub; see typing/README.md for scope.
from .interaction import fields_for as fields_for
from typing import TextIO
from pathlib import Path
from ..errors import RiposteError as RiposteError
from .controller import Controller as Controller
from .keyboard import Key as Key, TerminalKeys as TerminalKeys
from .output import Presentation as Presentation, error as error
from .render import render as render, view_rows as view_rows
from .signals import TerminationRequested as TerminationRequested, termination_guard as termination_guard

def _line_command(controller: Controller, line: str) -> None: ...

def linear_session(controller: Controller, input_stream: TextIO | None=None, output_stream: TextIO | None=None) -> None: ...

def _read_keys(controller: Controller, keyboard: TerminalKeys, timeout: float) -> bool: ...

def launch(root: Path | None, presentation: Presentation, *, linear: bool=False, initial: str='home') -> int: ...

def _launch(root: Path | None, presentation: Presentation, *, linear: bool=False, initial: str='home') -> int: ...
