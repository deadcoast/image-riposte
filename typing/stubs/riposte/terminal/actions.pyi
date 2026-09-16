# Source-derived external stub; see typing/README.md for scope.
from typing import Any, Iterable, Mapping
from pathlib import Path
from _riposte_types import FormValue
from ..errors import RiposteError as RiposteError
from .service import EFFECTS as EFFECTS, Request as Request
from dataclasses import dataclass

@dataclass(frozen=True)
class Field:
    key: str
    label: str
    kind: str = ...
    default: Any = ...
    help: str = ...
    choices: tuple[str, ...] = ...
    minimum: float | None = ...
    maximum: float | None = ...
    optional: bool = ...

@dataclass(frozen=True)
class Action:
    key: str
    title: str
    section: str
    summary: str
    fields: tuple[Field, ...] = ...

    @property
    def effect(self) -> str: ...
DEVICE: Field
VAE_FIELDS: tuple[Field, ...]
INPAINT: Field
VIDEO: Field
IMAGE: Field
TRIAL: Field
BATCH: Field
ITEM: Field
MODEL: Field
STEPS: Field
SEED: Field
EPSILON: Field
WHITE: Field
EDGES: Field
PUB_FIELDS: tuple[Field, ...]
MAX_EDGE: Field
ACTIONS: tuple[Action, ...]
BY_KEY: dict[str, Action]

def defaults(action: Action, models: dict[str, Any] | None=None) -> dict[str, Any]: ...

def parse_value(field: Field, raw: Any) -> FormValue: ...

def make_request(key: str, root: Path | None, values: Mapping[str, Any], selected: Iterable[str]=()) -> Request: ...

def request_argv(request: Request) -> list[str]: ...

def command_line(request: Request, shell: str='powershell') -> str: ...
