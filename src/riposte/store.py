from __future__ import annotations
import contextlib
import json
import os
import sqlite3
import uuid
from pathlib import Path
from .errors import RiposteError
from .policy import canonical_path, is_link
from .sanitize import png_audit, timestamp_day

SIGNATURE = 'RIPOSTE_WORKSPACE_1\n'
LEGACY_SIGNATURE = 'SHROUD_WORKSPACE_1\n'


def state_name(root: Path) -> str:
    """Pure lookup. Legacy files remain in place until explicit upgrade."""
    return ".shroud" if (root / ".shroud").exists() else ".riposte"


def state_relative(root: Path, suffix: str = "") -> str:
    return state_name(root) + ("/" + suffix if suffix else "")


def check_root(root: Path) -> Path:
    root = root.absolute()
    if not root.is_dir() or is_link(root):
        raise RiposteError("ROOT_INVALID")
    if any(is_link(p) for p in root.parents):
        raise RiposteError("ROOT_LINKED")
    present = [root / name for name in (".riposte", ".shroud")
               if (root / name).exists() or (root / name).is_symlink()]
    if len(present) > 1:
        raise RiposteError("WORKSPACE_NAMESPACE_CONFLICT")
    for state in present:
        if is_link(state) or not state.is_dir():
            raise RiposteError("STATE_PATH_INVALID")
        marker = state / "WORKSPACE"
        try:
            allowed = {LEGACY_SIGNATURE} if state.name == ".shroud" else {SIGNATURE, LEGACY_SIGNATURE}
            if is_link(marker) or marker.read_text() not in allowed:
                raise RiposteError("STATE_DIRECTORY_CONFLICT")
        except OSError:
            raise RiposteError("STATE_DIRECTORY_CONFLICT") from None
    return root


def state_dir(root: Path) -> Path:
    root = check_root(root)
    state = root / state_name(root)
    if not state.exists():
        state.mkdir(mode=0o700)
        (state / "WORKSPACE").write_text(SIGNATURE)
    return state


def legacy_workspace(root: Path) -> bool:
    root = check_root(root)
    state = root / state_name(root)
    return state.exists() and (state.name == ".shroud" or (state / "WORKSPACE").read_text() == LEGACY_SIGNATURE)


def upgrade_workspace(root: Path) -> dict:
    """Rename only application state; never decode, rewrite or renumber art.

    A crash after the directory rename leaves a recognized legacy marker at the
    new name. Re-running finishes the marker replacement without duplicating art.
    """
    root = check_root(root)
    if not legacy_workspace(root):
        return {"mode": "STATE_UPGRADE", "status": "ALREADY_CURRENT", "artwork_rewritten": 0}
    source, target = root / state_name(root), root / ".riposte"
    lock = source / "operation.lock"
    try:
        fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RiposteError("WORKSPACE_LOCKED") from None
    os.close(fd)
    current = source
    try:
        if source != target:
            if target.exists():
                raise RiposteError("WORKSPACE_NAMESPACE_CONFLICT")
            os.rename(source, target)
            current = target
        marker_temp = current / (".marker-" + uuid.uuid4().hex)
        try:
            with marker_temp.open("x", encoding="utf-8") as stream:
                stream.write(SIGNATURE)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(marker_temp, current / "WORKSPACE")
        finally:
            marker_temp.unlink(missing_ok=True)
    finally:
        (current / "operation.lock").unlink(missing_ok=True)
    return {"mode": "STATE_UPGRADE", "status": "UPGRADED", "artwork_rewritten": 0,
            "catalog_ids_preserved": True, "state_directory": ".riposte"}

def safe_child(root: Path, relative: str) -> Path:
    root = check_root(root)
    path = Path(relative)
    if path.is_absolute() or any(p in {"..", "."} for p in path.parts) or "\\" in relative:
        raise RiposteError("PATH_REJECTED")
    dest = root / path
    if not dest.is_relative_to(root):
        raise RiposteError("PATH_REJECTED")
    cur = root
    for part in path.parts:
        cur = cur / part
        if (cur.exists() or cur.is_symlink()) and is_link(cur):
            raise RiposteError("PATH_LINKED")
    return dest

@contextlib.contextmanager
def workspace_lock(root: Path):
    path = state_dir(root) / "operation.lock"
    if path.exists() and is_link(path):
        raise RiposteError("STATE_PATH_INVALID")
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        raise RiposteError("WORKSPACE_LOCKED") from None
    try:
        os.close(fd)
        yield
    finally:
        path.unlink(missing_ok=True)

def connect(root: Path) -> sqlite3.Connection:
    path = state_dir(root) / "catalog.sqlite3"
    if path.exists() and is_link(path):
        raise RiposteError("STATE_PATH_INVALID")
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=DELETE")
    db.execute("PRAGMA secure_delete=ON")
    db.execute("CREATE TABLE IF NOT EXISTS images (id TEXT PRIMARY KEY, relative TEXT UNIQUE NOT NULL, day TEXT NOT NULL, date_source TEXT NOT NULL, width INTEGER NOT NULL, height INTEGER NOT NULL, sha256 TEXT NOT NULL, bytes INTEGER NOT NULL)")
    db.commit()
    return db

def catalog(root: Path) -> list[dict]:
    check_root(root)
    if not (root / state_relative(root, "catalog.sqlite3")).exists():
        return []
    with contextlib.closing(sqlite3.connect(safe_child(root, state_relative(root, "catalog.sqlite3")).as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        result = [dict(row) for row in db.execute("SELECT * FROM images ORDER BY day DESC, relative")]
    for row in result:
        canonical_path(row["relative"])
    return result

def record_image(root: Path, relative: str, audit: dict, size: int, date_source: str) -> dict:
    canonical_path(relative)
    row = {"id": uuid.uuid4().hex, "relative": relative, "day": audit["date"],
           "date_source": date_source, "width": audit["width"], "height": audit["height"],
           "sha256": audit["sha256"], "bytes": size}
    with contextlib.closing(connect(root)) as db:
        db.execute("INSERT INTO images VALUES (:id,:relative,:day,:date_source,:width,:height,:sha256,:bytes)", row)
        db.commit()
    return row

def find_image(root: Path, identifier: str) -> dict:
    if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise RiposteError("IMAGE_NOT_FOUND")
    for row in catalog(root):
        if row["id"] == identifier:
            path = safe_child(root, canonical_path(row["relative"]))
            try:
                result = png_audit(path.read_bytes())
            except OSError:
                raise RiposteError("CATALOG_FILE_MISSING") from None
            if result["sha256"] != row["sha256"]:
                raise RiposteError("CATALOG_FILE_CHANGED")
            return row
    raise RiposteError("IMAGE_NOT_FOUND")

def atomic_clean_write(root: Path, relative: str, data: bytes, replace: bool = False) -> Path:
    audit = png_audit(data)
    dest = safe_child(root, relative)
    if dest.exists() and not replace:
        raise RiposteError("DESTINATION_EXISTS")
    dest.parent.mkdir(parents=True, exist_ok=True)
    # All temporary bytes are already canonical and contain only the retained date.
    temp = dest.parent / (".clean-" + uuid.uuid4().hex + ".tmp")
    try:
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        timestamp_day(temp, audit["date"])
        safe_child(root, relative)
        if replace:
            os.replace(temp, dest)
        else:
            # Link publication is exclusive: a late destination wins without
            # being overwritten or receiving our output's timestamp.
            try:
                os.link(temp, dest)
            except FileExistsError:
                raise RiposteError("DESTINATION_EXISTS") from None
        if png_audit(dest.read_bytes())["sha256"] != audit["sha256"]:
            raise RiposteError("WRITE_VERIFY_FAILED")
        return dest
    finally:
        temp.unlink(missing_ok=True)

def write_report(root: Path, name: str, report: dict) -> None:
    # Only callers with explicit, code-defined schemas call this function.
    if name not in {"last-run.json", "last-audit.json"}:
        raise RiposteError("REPORT_NAME_INVALID")
    path = state_dir(root) / name
    if path.exists() and is_link(path):
        raise RiposteError("STATE_PATH_INVALID")
    temp = path.with_suffix(".tmp")
    if temp.exists() and is_link(temp):
        raise RiposteError("STATE_PATH_INVALID")
    temp.write_text(json.dumps(report, indent=2, allow_nan=False))
    os.replace(temp, path)


def atomic_json_write(root: Path, relative: str, report: dict) -> Path:
    """Commit a code-defined report without leaving partial JSON on interruption."""
    data = json.dumps(report, indent=2, allow_nan=False).encode("utf-8")
    dest = safe_child(root, relative)
    if dest.exists():
        raise RiposteError("DESTINATION_EXISTS")
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp = dest.parent / (".report-" + uuid.uuid4().hex + ".tmp")
    try:
        with temp.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        if dest.exists():
            raise RiposteError("DESTINATION_EXISTS")
        os.replace(temp, dest)
        return dest
    finally:
        temp.unlink(missing_ok=True)
