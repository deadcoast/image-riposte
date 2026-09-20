from dataclasses import dataclass
from typing import TypedDict

class Entry(TypedDict, total=False):
    title: str
    action: str
    level: str
    operations: dict[str, str]

class Catalog(TypedDict):
    version: int
    aliases: dict[str, str]
    entries: dict[str, Entry]

@dataclass(frozen=True)
class Guidance:
    code: str
    title: str
    action: str
    level: str = ...

def _catalog() -> Catalog: ...
CATALOG: Catalog
def guidance(code: object, operation: str = '') -> Guidance: ...
def recovery_text(code: object, operation: str = '') -> str: ...
