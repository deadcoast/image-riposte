"""Sort-only video inspection and catalog. No transcoding or protection."""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import uuid
from pathlib import Path
from typing import Any, cast

from .errors import RiposteError
from .policy import Policy, extract_day, is_link, same_file_state, sort_folder_for, valid_day
from .store import check_root, connect, safe_child, state_relative
from .records import CatalogRow

VIDEO_SUFFIXES = frozenset({".mp4", ".m4v", ".mov", ".mkv", ".webm", ".avi", ".wmv", ".mpg", ".mpeg", ".mts", ".m2ts", ".3gp", ".ogv"})


def file_hash(path: Path) -> str:
    if is_link(path) or not path.is_file() or path.stat().st_nlink != 1:
        raise RiposteError("FILE_REQUIRES_REVIEW")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
        if not same_file_state(before, os.fstat(stream.fileno())) or not os.path.samestat(before, path.stat()):
            raise RiposteError("SOURCE_CHANGED")
    return digest


def inspect_video(path: Path, policy: Policy = Policy()) -> dict[str, Any]:
    if is_link(path) or path.stat().st_nlink != 1:
        raise RiposteError("VIDEO_LINK_REQUIRES_REVIEW")
    executable = shutil.which("ffprobe")
    if executable is None:
        raise RiposteError("VIDEO_PROBE_UNAVAILABLE")
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
    try:
        result = subprocess.run(
            [executable, "-v", "error", "-protocol_whitelist", "file", "-select_streams", "v:0",
             "-show_entries", "stream=width,height:stream_disposition=attached_pic:stream_tags=creation_time:format_tags=creation_time",
             "-of", "json", str(path.absolute())], capture_output=True, timeout=30,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        if result.returncode or len(result.stdout) > 65536:
            raise ValueError("invalid probe")
        data = json.loads(result.stdout)
        video = data["streams"][0]
        width, height = int(video["width"]), int(video["height"])
        if min(width, height) < 1 or video.get("disposition", {}).get("attached_pic"):
            raise ValueError("not a video")
    except (OSError, subprocess.SubprocessError, ValueError, KeyError, IndexError, TypeError):
        raise RiposteError("VIDEO_PROBE_FAILED") from None
    day, source = extract_day(None, before, "modified" if policy.date_mode == "embedded" else policy.date_mode)
    if policy.date_mode == "embedded":
        for tags in (video.get("tags", {}), data.get("format", {}).get("tags", {})):
            try:
                day, source = valid_day(str(tags.get("creation_time", ""))[:10]), "embedded"
                break
            except RiposteError:
                pass
    digest = file_hash(path)
    with path.open("rb") as stream:
        if not same_file_state(before, os.fstat(stream.fileno())):
            raise RiposteError("SOURCE_CHANGED")
    return {"day": day, "date_source": source, "width": width, "height": height,
            "sha256": digest, "bytes": before.st_size, "source_stat": before}


def video_catalog(root: Path) -> list[CatalogRow]:
    root = check_root(root)
    path = safe_child(root, state_relative(root, "catalog.sqlite3"))
    if not path.exists():
        return []
    with contextlib.closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='videos'").fetchone():
            return []
        rows = [cast(CatalogRow, dict(row)) for row in db.execute("SELECT * FROM videos ORDER BY day DESC, relative")]
    for row in rows:
        relative = Path(row["relative"])
        from .policy import path_category
        folder = sort_folder_for(row["day"], row["width"], row["height"], "vid", path_category(row["relative"]))
        stem = relative.stem
        if (relative.parent != folder or relative.suffix not in VIDEO_SUFFIXES
                or not stem.startswith(folder.name) or not stem[len(folder.name):].isascii()
                or not stem[len(folder.name):].isdigit() or len(stem[len(folder.name):]) < 2):
            raise RiposteError("VIDEO_CATALOG_PATH_INVALID")
        safe_child(root, row["relative"])
    return rows


def record_video(root: Path, relative: str, info: dict[str, Any], *, db: sqlite3.Connection | None = None) -> CatalogRow:
    row = {k: info[k] for k in ("day", "date_source", "width", "height", "sha256", "bytes")}
    row.update(id=uuid.uuid4().hex, relative=relative)
    with (contextlib.closing(connect(root)) if db is None else contextlib.nullcontext(db)) as db:
        db.execute("CREATE TABLE IF NOT EXISTS videos (id TEXT PRIMARY KEY, relative TEXT UNIQUE NOT NULL, day TEXT NOT NULL, date_source TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL)")
        db.execute("INSERT INTO videos VALUES (:id,:relative,:day,:date_source,:width,:height,:sha256,:bytes)", row)
        db.commit()
    return cast(CatalogRow, row)
