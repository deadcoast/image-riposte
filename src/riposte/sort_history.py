"""Private, byte-exact recovery records for explicit sort operations.

Recovery copies deliberately retain original metadata and names. They are never
publishing inputs or public exports. The journal is flushed before every unlink.
"""
from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from .errors import RiposteError
from .policy import is_link, same_file_state
from .store import catalog, check_root, connect, safe_child, state_dir, state_name, state_relative, workspace_lock
from .video import file_hash, video_catalog
from .sort_titles import title_records, validate_title, save_title, restore_titles


def _save(root: Path, journal: dict[str, Any]) -> None:
    relative = state_relative(root, f"sort-history/{journal['id']}/journal.json")
    dest = safe_child(root, relative)
    dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = dest.parent / (uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as stream:
            json.dump(journal, stream, ensure_ascii=True, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        safe_child(root, relative)
        os.replace(temp, dest)
    finally:
        temp.unlink(missing_ok=True)


def _media_path(root: Path, relative: str) -> Path:
    if not relative or Path(relative).parts[0] in {".riposte", ".shroud"}:
        raise RiposteError("SORT_HISTORY_INVALID")
    return safe_child(root, relative)


def latest_sort(root: Path) -> dict[str, Any] | None:
    root = check_root(root)
    folder = safe_child(root, state_relative(root, "sort-history"))
    if not folder.exists():
        return None
    try:
        for entry in sorted(folder.iterdir(), reverse=True):
            if not re.fullmatch(r"[0-9]{20}-[0-9a-f]{32}", entry.name) or is_link(entry):
                raise RiposteError("SORT_HISTORY_INVALID")
            path = safe_child(root, state_relative(root, f"sort-history/{entry.name}/journal.json"))
            journal = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(journal, dict) or journal["version"] not in {1, 2} or journal["id"] != entry.name or journal["status"] not in {"APPLYING", "APPLIED", "UNDOING", "UNDONE"}:
                raise RiposteError("SORT_HISTORY_INVALID")
            if any(not isinstance(journal[k], list) or any(not isinstance(row, dict) for row in journal[k])
                   for k in ("entries", "images", "videos")):
                raise RiposteError("SORT_HISTORY_INVALID")
            for item in journal["entries"]:
                if (not isinstance(item["source"], str) or not isinstance(item["backup"], str)
                        or not re.fullmatch(r"[0-9a-f]{64}", item["sha256"])
                        or any(type(item[k]) is not bool for k in ("removing", "removed", "restoring"))
                        or any(type(item[k]) is not int for k in ("atime_ns", "mtime_ns"))
                        or item["media"] not in {"img", "vid", "sidecar"}
                        or item["output"] is not None and (not isinstance(item["output"], str) or not isinstance(item["expected"], dict))):
                    raise RiposteError("SORT_HISTORY_INVALID")
            if journal["version"] == 2:
                for key in ("titles", "title_updates"):
                    if not isinstance(journal[key], list):
                        raise RiposteError("SORT_HISTORY_INVALID")
                    for row in journal[key]:
                        validate_title(row)
                    if len({r["id"] for r in journal[key]}) != len(journal[key]):
                        raise RiposteError("SORT_HISTORY_INVALID")
            if journal["status"] != "UNDONE" and (journal["entries"] or journal.get("title_updates")):
                return journal
    except (OSError, ValueError, KeyError, TypeError):
        raise RiposteError("SORT_HISTORY_INVALID") from None
    return None


def pending_sort(root: Path) -> bool:
    journal = latest_sort(root)
    return journal is not None and journal["status"] in {"APPLYING", "UNDOING"}


def copy_exclusive(root: Path, source: Path, relative: str, digest: str) -> Path:
    """Stream to a private temporary, then publish without overwriting any path."""
    dest = safe_child(root, relative)
    if dest.exists():
        raise RiposteError("DESTINATION_EXISTS")
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.parent / (".restore-" + uuid.uuid4().hex + ".tmp")
    try:
        with source.open("rb") as src, temp.open("xb") as target:
            shutil.copyfileobj(src, target, 1024 * 1024)
            target.flush()
            os.fsync(target.fileno())
        if file_hash(temp) != digest:
            raise RiposteError("WRITE_VERIFY_FAILED")
        safe_child(root, relative)
        # An exclusive hard-link commit is atomic and never replaces a late file.
        try:
            os.link(temp, dest)
        except FileExistsError:
            raise RiposteError("DESTINATION_EXISTS") from None
    finally:
        temp.unlink(missing_ok=True)
    return dest


class SortHistory:
    def __init__(self, root: Path):
        if pending_sort(root):
            raise RiposteError("SORT_RECOVERY_REQUIRED")
        self.root = root
        self.journal: dict[str, Any] = {"version": 2, "id": f"{time.time_ns():020d}-{uuid.uuid4().hex}",
                        "status": "APPLYING", "entries": [], "images": catalog(root), "videos": video_catalog(root),
                        "titles": title_records(root), "title_updates": []}

    def record_title(self, row: dict[str, Any]) -> None:
        validate_title(row)
        if row in self.journal["titles"]:
            return
        if any(r["id"] == row["id"] for r in self.journal["title_updates"]):
            raise RiposteError("SORT_HISTORY_INVALID")
        self.journal["title_updates"].append(row)
        _save(self.root, self.journal)
        save_title(self.root, row)

    def prepare(self, source: Path, output: str | None, expected: dict[str, Any] | None, media: str, before_row: dict[str, Any] | None = None) -> dict[str, Any]:
        if is_link(source) or source.stat().st_nlink != 1:
            raise RiposteError("HARDLINK_REQUIRES_REVIEW")
        relative = source.relative_to(self.root).as_posix()
        _media_path(self.root, relative)
        with source.open("rb") as stream:
            stat = os.fstat(stream.fileno())
        digest = file_hash(source)
        index = len(self.journal["entries"])
        backup = state_relative(self.root, f"sort-history/{self.journal['id']}/{index:08d}.bin")
        state_dir(self.root)
        # An empty journal makes interrupted backup creation recognizable.
        _save(self.root, self.journal)
        copy_exclusive(self.root, source, backup, digest)
        entry = {"source": relative, "backup": f"{index:08d}.bin", "sha256": digest,
                 "atime_ns": stat.st_atime_ns, "mtime_ns": stat.st_mtime_ns,
                 "output": output, "expected": expected, "media": media,
                 "before_row": before_row, "removing": False, "removed": False, "restoring": False}
        self.journal["entries"].append(entry)
        _save(self.root, self.journal)
        # The verified backup owns this slot even if the original has changed.
        # Keep it addressable for undo and let the next input use a fresh slot.
        try:
            with source.open("rb") as stream:
                unchanged = same_file_state(stat, os.fstat(stream.fileno()))
        except OSError:
            unchanged = False
        if not unchanged:
            raise RiposteError("SOURCE_CHANGED")
        return entry

    def reject_output(self, entry: dict[str, Any]) -> None:
        """A confirmed destination conflict grants no ownership of that path."""
        entry["output"] = None
        entry["expected"] = None
        _save(self.root, self.journal)

    def remove_source(self, entry: dict[str, Any]) -> None:
        source = _media_path(self.root, entry["source"])
        before = source.stat()
        if file_hash(source) != entry["sha256"]:
            raise RiposteError("SOURCE_CHANGED_OUTPUT_RETAINED")
        entry["removing"] = True
        _save(self.root, self.journal)
        # Journal persistence can yield to another writer. Recheck both the
        # pathname identity and bytes after that write, before removing it.
        # Hashing also detects same-size edits that restore the original mtime.
        try:
            unchanged = (same_file_state(before, source.stat())
                         and file_hash(source) == entry["sha256"]
                         and same_file_state(before, source.stat()))
        except (OSError, RiposteError):
            unchanged = False
        if not unchanged:
            # No unlink was attempted. Undo must leave this later source alone,
            # while still being able to remove our generated output.
            entry["removing"] = False
            _save(self.root, self.journal)
            raise RiposteError("SOURCE_CHANGED_OUTPUT_RETAINED")
        source.unlink()
        entry["removed"] = True
        _save(self.root, self.journal)

    def finish(self) -> str | None:
        if not self.journal["entries"] and not self.journal["title_updates"]:
            return None
        self.journal["status"] = "APPLIED"
        _save(self.root, self.journal)
        return str(self.journal["id"])


def _check(root: Path, journal: dict[str, Any]) -> dict[str, Any]:
    """Validate the entire undo before its first write; rechecked during commit."""
    blockers: dict[str, int] = {}
    def blocked(code: str) -> None:
        blockers[code] = blockers.get(code, 0) + 1
    try:
        current = {"img": catalog(root), "vid": video_catalog(root)}
        before = {"img": journal["images"], "vid": journal["videos"]}
        for index, entry in enumerate(journal["entries"]):
            source = _media_path(root, entry["source"])
            if entry["source"] == entry["output"]:
                raise RiposteError("SORT_HISTORY_INVALID")
            if entry["backup"] != f"{index:08d}.bin":
                raise RiposteError("SORT_HISTORY_INVALID")
            expected_backup = state_relative(root, f"sort-history/{journal['id']}/{index:08d}.bin")
            backup = safe_child(root, expected_backup)
            if not backup.is_file() or file_hash(backup) != entry["sha256"]:
                blocked("UNDO_BACKUP_CHANGED")
            if source.exists():
                if entry["removed"] and not entry["restoring"]:
                    blocked("UNDO_SOURCE_OCCUPIED")
                elif (entry["removing"] or entry["restoring"]) and file_hash(source) != entry["sha256"]:
                    blocked("UNDO_SOURCE_CHANGED")
            if entry["output"]:
                output = _media_path(root, entry["output"])
                if output.exists() and file_hash(output) != entry["expected"]["sha256"]:
                    blocked("UNDO_OUTPUT_CHANGED")
                media = entry["media"]
                if media not in current:
                    raise RiposteError("SORT_HISTORY_INVALID")
                rows = [r for r in current[media] if r["relative"] == entry["output"]]
                for row in rows:
                    if any(row[k] != v for k, v in entry["expected"].items()):
                        blocked("UNDO_CATALOG_CHANGED")
                    current[media].remove(row)
                previous = entry["before_row"]
                if previous:
                    if previous in current[media]:
                        current[media].remove(previous)
                    before[media] = [r for r in before[media] if r != previous]
        for media in current:
            if sorted(current[media], key=lambda r: r["id"]) != sorted(before[media], key=lambda r: r["id"]):
                blocked("UNDO_CATALOG_CHANGED")
        if journal["version"] == 2:
            titles = {r["id"]: r for r in title_records(root)}
            old_titles = {r["id"]: r for r in journal["titles"]}
            for row in journal["title_updates"]:
                previous = old_titles.pop(row["id"], None)
                if titles.pop(row["id"], None) not in (previous, row):
                    blocked("UNDO_ASSIGNMENTS_CHANGED")
            if titles != old_titles:
                blocked("UNDO_ASSIGNMENTS_CHANGED")
    except (OSError, KeyError, TypeError, ValueError):
        blocked("SORT_HISTORY_INVALID")
    except RiposteError as exc:
        blocked(exc.code)
    return {"mode": "UNDO_SORT_PREVIEW", "sort_id": journal["id"], "ready": not blockers,
            "files_to_restore": sum(bool(e.get("removing")) for e in journal["entries"]),
            "outputs_to_remove": sum(bool(e.get("output")) for e in journal["entries"]),
            "blockers": blockers, "recovery_metadata": "ORIGINAL_NAMES_AND_METADATA",
            "scope": "Restore this sort only. Protection outputs and review records stay in place."}


def undo_sort(root: Path, apply: bool = False, sort_id: str | None = None) -> dict[str, Any]:
    root = check_root(root)
    journal = latest_sort(root)
    if journal is None:
        return {"mode": "UNDO_SORT_PREVIEW", "ready": False, "blockers": {"NO_SORT_TO_UNDO": 1}}
    if sort_id is not None and journal["id"] != sort_id:
        raise RiposteError("SORT_HISTORY_CHANGED_REPREVIEW")
    if not apply:
        return _check(root, journal)
    with workspace_lock(root):
        journal = latest_sort(root)
        if journal is None:
            raise RiposteError("NO_SORT_TO_UNDO")
        if sort_id is not None and journal["id"] != sort_id:
            raise RiposteError("SORT_HISTORY_CHANGED_REPREVIEW")
        preview = _check(root, journal)
        if not preview["ready"]:
            return {**preview, "mode": "UNDO_SORT", "checkpoint": "INCOMPLETE"}
        journal["status"] = "UNDOING"
        _save(root, journal)
        for entry in reversed(journal["entries"]):
            source = _media_path(root, entry["source"])
            if source.exists() and entry["removed"] and not entry["restoring"]:
                raise RiposteError("UNDO_SOURCE_OCCUPIED")
            if source.exists() and (entry["removing"] or entry["restoring"]) and file_hash(source) != entry["sha256"]:
                raise RiposteError("UNDO_SOURCE_CHANGED")
            entry["restoring"] = entry["removing"] or not source.exists()
            _save(root, journal)
            if not source.exists():
                backup = safe_child(root, state_relative(root, f"sort-history/{journal['id']}/{entry['backup']}"))
                copy_exclusive(root, backup, entry["source"], entry["sha256"])
            if entry["restoring"]:
                os.utime(source, ns=(entry["atime_ns"], entry["mtime_ns"]))
            if entry["output"]:
                output = _media_path(root, entry["output"])
                if output.exists():
                    if file_hash(output) != entry["expected"]["sha256"]:
                        raise RiposteError("UNDO_OUTPUT_CHANGED")
                    output.unlink()
                for folder in output.parents:
                    if folder == root:
                        break
                    try:
                        folder.rmdir()
                    except OSError:
                        break
        if not _check(root, journal)["ready"]:
            raise RiposteError("UNDO_CATALOG_CHANGED")
        with contextlib.closing(connect(root)) as db:
            for table, rows in (("images", journal["images"]), ("videos", journal["videos"])):
                if table == "videos" and not db.execute("SELECT 1 FROM sqlite_master WHERE name='videos'").fetchone():
                    continue
                db.execute(f"DELETE FROM {table}")
                db.executemany(f"INSERT INTO {table} VALUES (:id,:relative,:day,:date_source,:width,:height,:sha256,:bytes)", rows)
            if journal["version"] == 2:
                restore_titles(db, journal["titles"])
            db.commit()
        journal["status"] = "UNDONE"
        _save(root, journal)
        return {**preview, "mode": "UNDO_SORT", "checkpoint": "COMPLETE"}
