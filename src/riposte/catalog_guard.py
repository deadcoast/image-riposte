"""Operation-local SQLite revision guard; never cache consent across operations."""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import sqlite3
from pathlib import Path

from .errors import RiposteError
from .store import connect, safe_child, state_relative


class CatalogGuard:
    def __init__(self, root: Path, changed_code: str, *, read_only: bool = False):
        self.root, self.changed_code = root, changed_code
        self.path = safe_child(root, state_relative(root, "catalog.sqlite3"))
        self.db: sqlite3.Connection | None = None
        self.identity: tuple[int, int] | None = None
        self.version: int | None = None
        try:
            before = self.path.stat() if self.path.exists() else None
            if not read_only:
                self.db = connect(root)
            elif before is not None:
                self.db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
            if self.db is not None:
                after = self.path.stat()
                self.identity = after.st_dev, after.st_ino
                if before is not None and (before.st_dev, before.st_ino) != self.identity:
                    raise RiposteError(changed_code)
                self.version = self.db.execute("PRAGMA data_version").fetchone()[0]
            self.check()
        except BaseException:
            self.close()
            raise

    def check(self) -> None:
        try:
            path = safe_child(self.root, state_relative(self.root, "catalog.sqlite3"))
            current = path.stat() if path.exists() else None
            identity = (current.st_dev, current.st_ino) if current is not None else None
            if path != self.path or identity != self.identity:
                raise RiposteError(self.changed_code)
            # Compare only on this live connection. Its own commits do not
            # advance data_version; any other connection's commit does.
            if self.db is not None and self.db.execute("PRAGMA data_version").fetchone()[0] != self.version:
                raise RiposteError(self.changed_code)
        except (OSError, sqlite3.Error):
            raise RiposteError(self.changed_code) from None

    @contextmanager
    def write(self, expected_changes: int = 1) -> Iterator[sqlite3.Connection]:
        self.check()
        if self.db is None:
            raise RiposteError(self.changed_code)
        db = self.db
        db.execute("BEGIN IMMEDIATE")
        try:
            self.check()  # Includes commits between the first check and BEGIN.
            before = db.total_changes
            yield db
            if db.total_changes - before != expected_changes:
                # Includes unexpected trigger effects on this connection.
                raise RiposteError(self.changed_code)
            db.commit()
            self.check()
        except BaseException:
            db.rollback()
            raise

    def close(self) -> None:
        if self.db is not None:
            self.db.close()

