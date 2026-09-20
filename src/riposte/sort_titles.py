"""Private title provenance, deliberately separate from the public media catalog."""
from __future__ import annotations

import contextlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any

from .errors import RiposteError
from .policy import category_slug
from .store import check_root, connect, safe_child, state_relative


def validate_title(row: dict[str, Any]) -> None:
    try:
        if (set(row) != {"id", "media", "original_filename", "category", "manual", "rule_revision", "matched_terms", "sha256"}
                or not re.fullmatch(r"[0-9a-f]{32}", row["id"])
                or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                or row["media"] not in {"img", "vid"} or type(row["manual"]) is not bool
                or row["original_filename"] is not None and (not isinstance(row["original_filename"], str)
                    or not row["original_filename"] or any(c in row["original_filename"] for c in "/\\\0"))
                or not isinstance(row["matched_terms"], list) or any(not isinstance(t, str) for t in row["matched_terms"])
                or row["rule_revision"] is not None and row["rule_revision"] != "missing"
                    and not re.fullmatch(r"[0-9a-f]{64}", row["rule_revision"])):
            raise ValueError()
        if row["category"] is not None:
            category_slug(row["category"])
    except (KeyError, TypeError, ValueError):
        raise RiposteError("TITLE_PROVENANCE_INVALID") from None


def title_records(root: Path) -> list[dict[str, Any]]:
    root = check_root(root)
    path = safe_child(root, state_relative(root, "catalog.sqlite3"))
    if not path.exists():
        return []
    try:
        with contextlib.closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sort_titles'").fetchone():
                return []
            rows = []
            for identifier, data in db.execute("SELECT id,data FROM sort_titles ORDER BY id"):
                row = json.loads(data)
                validate_title(row)
                if identifier != row["id"]:
                    raise ValueError()
                rows.append(row)
            return rows
    except (sqlite3.Error, ValueError, TypeError):
        raise RiposteError("TITLE_PROVENANCE_INVALID") from None


def put_title(db: sqlite3.Connection, row: dict[str, Any]) -> None:
    validate_title(row)
    db.execute("CREATE TABLE IF NOT EXISTS sort_titles (id TEXT PRIMARY KEY, data TEXT NOT NULL)")
    db.execute("INSERT OR REPLACE INTO sort_titles VALUES (?,?)", (row["id"], json.dumps(row, sort_keys=True, ensure_ascii=True)))


def restore_titles(db: sqlite3.Connection, rows: list[dict[str, Any]]) -> None:
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sort_titles'").fetchone():
        db.execute("DELETE FROM sort_titles")
    for row in rows:
        put_title(db, row)


def save_title(root: Path, row: dict[str, Any], *, db: sqlite3.Connection | None = None) -> None:
    """Caller holds the workspace lock and has persisted the recovery intent."""
    with (contextlib.closing(connect(root)) if db is None else contextlib.nullcontext(db)) as db:
        put_title(db, row)
        db.commit()
