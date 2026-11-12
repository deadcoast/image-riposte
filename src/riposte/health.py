"""Bounded, non-mutating storage observations, never a permission to prune.

Logical sizes count directory entries, not allocated clusters or unique content.
No images are decoded and no recovery backup is hashed by this inspection.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import shutil
import stat
import sys
import time
from typing import Any, Protocol, TypedDict

from .errors import RiposteError
from .locking import LEASE_NAME, file_identity
from .policy import CACHE_NAMES, IMAGE_SUFFIXES, SIDECAR_SUFFIXES, is_link, same_file_state, sort_excluded
from .records import Progress
from .store import _read_lock_marker, check_root, safe_child, state_name
from .video import VIDEO_SUFFIXES

MAX_ENTRIES = 100_000
MAX_JOURNAL_BYTES = 4 * 1024 * 1024
HISTORY_ID = re.compile(r"[0-9]{20}-[0-9a-f]{32}")


class _DirectoryEntries(Protocol):
    def __next__(self) -> os.DirEntry[str]: ...
    def close(self) -> None: ...


class CapabilityReport(TypedDict):
    filesystem: str | None
    hard_links: str
    read_only: bool | None
    source: str
    write_test: str
    note: str


class HealthReport(TypedDict):
    mode: str
    writes: bool
    checkpoint: str
    status: str
    usage: dict[str, int]
    capacity: dict[str, int | None]
    estimate: dict[str, Any]
    filesystem: CapabilityReport
    operation: dict[str, str]
    history: dict[str, Any]
    coverage: dict[str, Any]
    guidance: list[str]


def filesystem_capabilities(root: Path) -> CapabilityReport:
    result: CapabilityReport = {
        "filesystem": None, "hard_links": "UNKNOWN", "read_only": None,
        "source": "unavailable", "write_test": "NOT_RUN",
        "note": "Volume flags describe advertised support. Permissions, exclusive commits, locks and crash durability were not tested.",
    }
    try:
        if sys.platform == "win32":
            import ctypes
            from ctypes import wintypes
            api = ctypes.WinDLL("kernel32", use_last_error=True)
            volume = ctypes.create_unicode_buffer(32768)
            get_path = api.GetVolumePathNameW
            get_path.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD]
            get_path.restype = wintypes.BOOL
            if not get_path(str(root), volume, len(volume)):
                return result
            flags = wintypes.DWORD()
            name = ctypes.create_unicode_buffer(261)
            info = api.GetVolumeInformationW
            info.argtypes = [wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.DWORD,
                             ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(wintypes.DWORD),
                             ctypes.POINTER(wintypes.DWORD), wintypes.LPWSTR, wintypes.DWORD]
            info.restype = wintypes.BOOL
            if info(volume.value, None, 0, None, None, ctypes.byref(flags), name, len(name)):
                result["filesystem"] = name.value
                result["source"] = "GetVolumeInformationW"
                result["hard_links"] = "ADVERTISED" if flags.value & 0x00400000 else "NOT_ADVERTISED"
                result["read_only"] = bool(flags.value & 0x00080000)
        elif hasattr(os, "statvfs"):
            result["read_only"] = bool(os.statvfs(root).f_flag & os.ST_RDONLY)
            result["source"] = "statvfs"
    except (OSError, AttributeError):
        pass
    return result


def operation_observation(root: Path) -> dict[str, str]:
    """Observe marker format only; never acquire, reclaim or remove a lease."""
    try:
        marker = _read_lock_marker(root / state_name(root) / "operation.lock")
        if marker is None:
            return {"status": "NO_MARKER_OBSERVED", "ownership": "NOT_TESTED"}
        dev, ino = file_identity(root / LEASE_NAME)
        info = root.stat()
        prefix = f"RIPOSTE_OS_LEASE_1\n{info.st_dev}:{info.st_ino}\n{dev}:{ino}\n".encode("ascii")
        token = marker[0][len(prefix):-1]
        recognized = (marker[0].startswith(prefix) and marker[0].endswith(b"\n")
                      and len(token) == 32 and all(c in b"0123456789abcdef" for c in token))
        return {"status": "LEASE_MARKER_PRESENT" if recognized else "UNRECOGNIZED_MARKER", "ownership": "NOT_TESTED"}
    except (OSError, RiposteError):
        return {"status": "UNREADABLE_OR_UNRECOGNIZED_MARKER", "ownership": "NOT_TESTED"}


def _journal(root: Path, path: Path) -> str:
    """Bounded header/shape check. Does not grant undo or deletion authority."""
    safe_child(root, path.relative_to(root).as_posix())
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size > MAX_JOURNAL_BYTES:
        return "UNVERIFIED"
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        # Windows lstat/fstat ctime can differ (creation vs change time).
        # Compare stable cross-API fields, then recheck lstat against lstat.
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                != (opened.st_dev, opened.st_ino, opened.st_size, opened.st_mtime_ns)):
            return "UNVERIFIED"
        data = stream.read(MAX_JOURNAL_BYTES + 1)
    if len(data) > MAX_JOURNAL_BYTES or not same_file_state(before, path.lstat()):
        return "UNVERIFIED"
    try:
        journal = json.loads(data)
        if (not isinstance(journal, dict) or type(journal.get("version")) is not int
                or journal["version"] not in {1, 2} or journal.get("id") != path.parent.name
                or journal.get("status") not in {"APPLYING", "APPLIED", "UNDOING", "UNDONE"}
                or any(not isinstance(journal.get(k), list) or any(not isinstance(r, dict) for r in journal[k])
                       for k in ("entries", "images", "videos"))):
            return "UNVERIFIED"
        if journal["version"] == 2 and any(not isinstance(journal.get(k), list) for k in ("titles", "title_updates")):
            return "UNVERIFIED"
        for index, row in enumerate(journal["entries"]):
            if (row.get("backup") != f"{index:08d}.bin" or not isinstance(row.get("source"), str)
                    or not isinstance(row.get("sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", row["sha256"])
                    or any(type(row.get(k)) is not bool for k in ("removing", "removed", "restoring"))):
                return "UNVERIFIED"
        return str(journal["status"])
    except (ValueError, TypeError, RecursionError):
        return "UNVERIFIED"


def inspect_health(root: Path, *, max_entries: int = MAX_ENTRIES, progress: Progress | None = None) -> HealthReport:
    if type(max_entries) is not int or not 1 <= max_entries <= 200_000:
        raise RiposteError("RESOURCE_LIMIT_INVALID")
    root = check_root(root)
    namespace = state_name(root)
    operation = operation_observation(root)
    usage = {key: 0 for key in ("workspace_bytes", "private_state_bytes", "recovery_bytes", "float_bytes", "other_bytes", "files")}
    counts: dict[str, int] = {}
    history_dirs: set[str] = set()
    journals: dict[str, str] = {}
    candidate_bytes = candidate_files = visited = 0
    issues: dict[str, int] = {}
    started = time.monotonic()
    capacity: dict[str, int | None] = {"total_bytes": None, "used_bytes": None, "free_bytes": None}
    try:
        disk = shutil.disk_usage(root)
        capacity.update(total_bytes=disk.total, used_bytes=disk.used, free_bytes=disk.free)
    except OSError:
        issues["CAPACITY_UNAVAILABLE"] = 1
    capabilities = filesystem_capabilities(root)

    def issue(code: str) -> None:
        issues[code] = issues.get(code, 0) + 1

    # Iterators bound memory and entry counting; do not materialize a wide tree.
    stack: list[tuple[Path, os.stat_result, _DirectoryEntries]] = []
    try:
        stack.append((root, root.lstat(), os.scandir(root)))
        while stack:
            if progress:
                progress({"phase": "Inspecting workspace storage", "processed": visited})
            if visited >= max_entries or time.monotonic() - started > 30:
                issue("ENTRY_LIMIT" if visited >= max_entries else "TIME_LIMIT")
                break
            directory, before_dir, iterator = stack[-1]
            try:
                entry = next(iterator)
            except StopIteration:
                iterator.close()
                stack.pop()
                if not same_file_state(before_dir, directory.lstat()):
                    issue("DIRECTORY_CHANGED")
                continue
            visited += 1
            path = Path(entry.path)
            parts = path.relative_to(root).parts
            try:
                if is_link(path):
                    issue("LINK_OR_REPARSE_SKIPPED")
                    continue
                safe_child(root, path.relative_to(root).as_posix())
                info = path.lstat()
                if stat.S_ISDIR(info.st_mode):
                    if info.st_dev != root.stat().st_dev:
                        issue("OTHER_VOLUME_SKIPPED")
                    elif len(stack) >= 128:
                        issue("DEPTH_LIMIT")
                    else:
                        if len(parts) == 3 and parts[:2] == (namespace, "sort-history"):
                            history_dirs.add(parts[2])
                        stack.append((path, info, os.scandir(path)))
                    continue
                if parts == (namespace, "sort-history"):
                    issue("HISTORY_DIRECTORY_INVALID")
                if not stat.S_ISREG(info.st_mode):
                    issue("NONREGULAR_SKIPPED")
                    continue
                size = info.st_size
                usage["files"] += 1
                usage["workspace_bytes"] += size
                private = parts[0] == namespace or parts == (LEASE_NAME,)
                floating = not private and sort_excluded(path.parent)
                if private:
                    usage["private_state_bytes"] += size
                    if len(parts) >= 3 and parts[1] == "sort-history":
                        usage["recovery_bytes"] += size
                        if len(parts) == 4 and parts[3] == "journal.json":
                            journals[parts[2]] = _journal(root, path) if HISTORY_ID.fullmatch(parts[2]) else "UNVERIFIED"
                elif floating:
                    usage["float_bytes"] += size
                else:
                    usage["other_bytes"] += size
                    # Inventory envelope, not a sort plan: includes already-sorted
                    # media and sidecars; extensionless decodable inputs are unknown.
                    if path.suffix.lower() in IMAGE_SUFFIXES | VIDEO_SUFFIXES | SIDECAR_SUFFIXES or path.name.lower() in CACHE_NAMES:
                        candidate_bytes += size
                        candidate_files += 1
            except (OSError, RiposteError):
                issue("PATH_UNREADABLE_OR_CHANGED")
    except OSError:
        issue("DIRECTORY_UNREADABLE_OR_CHANGED")
    finally:
        for _, _, iterator in stack:
            iterator.close()
    for identifier in history_dirs:
        status = journals.get(identifier, "UNVERIFIED")
        counts[status] = counts.get(status, 0) + 1
    after = operation_observation(root)
    if progress:
        progress({"phase": "Storage inspection finished", "processed": visited})
    if operation != after:
        issue("OPERATION_MARKER_CHANGED")
    guidance = [
        "This is a live observation, not an atomic snapshot or permission to sort or delete.",
        "Private recovery copies retain original names, metadata and full file bytes. Keep them private.",
        "No retention or cleanup is performed. Keep recovery histories together; use Preview undo to verify the latest undo before restoring.",
    ]
    if operation["status"] != "NO_MARKER_OBSERVED" or after["status"] != "NO_MARKER_OBSERVED":
        guidance.append("An operation marker was observed. It does not prove a live or abandoned owner. Wait for other operations; never delete the marker or lease manually.")
    if counts.get("APPLYING", 0) or counts.get("UNDOING", 0):
        guidance.append("An unfinished sort or undo was recorded. Preview undo before attempting another sort; retain every recovery file.")
    if counts.get("UNVERIFIED", 0):
        guidance.append("Some history could not be summarized. Preserve it and resolve access or damaged state before relying on recovery.")
    if capabilities["source"] == "unavailable":
        guidance.append("Filesystem capabilities are unknown. Inspection did not run a write or hard-link test.")
    if capabilities["hard_links"] == "NOT_ADVERTISED" or capabilities["read_only"]:
        guidance.append("This volume does not advertise required hard links or is read-only. Use a supported writable local volume for sort commits.")
    free = capacity["free_bytes"]
    if free is not None and free < candidate_bytes:
        guidance.append("Available capacity is smaller than the inventoried backup envelope. Review a dry run and free space outside recovery history before sorting.")
    if issues:
        guidance.append("Coverage is incomplete. Totals describe only observed entries; resolve skipped paths or rerun with a larger entry limit.")
    attention = bool(counts.get("UNVERIFIED", 0) or counts.get("APPLYING", 0) or counts.get("UNDOING", 0)
                     or operation["status"] != "NO_MARKER_OBSERVED" or capabilities["read_only"]
                     or capabilities["hard_links"] == "NOT_ADVERTISED" or free is not None and free < candidate_bytes)
    return {
        "mode": "WORKSPACE_HEALTH", "writes": False, "checkpoint": "INCOMPLETE" if issues else "COMPLETE",
        "status": "INCOMPLETE" if issues else "ATTENTION" if attention else "OBSERVED",
        "usage": usage, "capacity": capacity,
        "estimate": {"backup_envelope_bytes": candidate_bytes, "candidate_files": candidate_files,
                     "required_free_bytes": None, "sufficient_space": None,
                     "basis": "Observed image/video/sidecar suffixes outside private and float storage, including already-sorted files. Actual sort selection, extensionless images, decoded output expansion, temporary files and journals are not estimated. This is not required peak space or a fit guarantee."},
        "filesystem": capabilities, "operation": after,
        "history": {"directories": len(history_dirs), "statuses": counts, "restore_verified": False,
                    "latest_observed": max(journals, default=None), "integrity": "Headers and entry shapes only; backups and undo conflicts were not verified."},
        "coverage": {"entries": visited, "limit": max_entries, "issues": issues,
                     "basis": "Logical bytes per regular directory entry; hard links can be counted twice. Not allocated disk space. Linked paths and other volumes are not followed. Reads may update filesystem access times."},
        "guidance": guidance,
    }
