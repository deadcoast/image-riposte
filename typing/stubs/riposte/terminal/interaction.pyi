# Source-derived external stub for the reviewed 0.5 terminal revision.
from dataclasses import dataclass
from typing import TypedDict
from .actions import BY_KEY as BY_KEY, Field as _Field
from .state import Page as _Page, Session as _Session

@dataclass(frozen=True)
class Hint:
    key: str
    label: str
    explanation: str

class _HintRecord(TypedDict):
    key: str
    label: str
    explanation: str

class _ContextRecord(TypedDict):
    screen: str
    context: str
    controls: list[_HintRecord]

GLOBAL: tuple[Hint, ...]
def fields_for(page: _Page) -> tuple[_Field, ...]: ...
def hints(state: _Session) -> list[Hint]: ...
def context(state: _Session) -> str: ...
def contextual_help(state: _Session) -> _ContextRecord: ...
