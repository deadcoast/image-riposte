from collections.abc import Iterator
from contextlib import AbstractContextManager
from pathlib import Path
import sqlite3
from .errors import RiposteError as RiposteError
from .store import connect as connect, safe_child as safe_child, state_relative as state_relative

class CatalogGuard:
    root: Path
    changed_code: str
    path: Path
    db: sqlite3.Connection | None
    identity: tuple[int, int] | None
    version: int | None
    def __init__(self, root: Path, changed_code: str, *, read_only: bool = ...) -> None: ...
    def check(self) -> None: ...
    def write(self, expected_changes: int = ...) -> AbstractContextManager[sqlite3.Connection]: ...
    def close(self) -> None: ...
