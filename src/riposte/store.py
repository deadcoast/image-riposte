from __future__ import annotations
import contextlib
import json
import os
import sqlite3
import stat
import tomllib
import uuid
from collections.abc import Iterator
from functools import lru_cache
from typing import cast
from pathlib import Path
from .errors import RiposteError
from .locking import LEASE_NAME, file_identity, file_lease
from .policy import canonical_path, is_link
from .sanitize import png_audit, timestamp_day
from .records import CatalogRow, PngAudit

SIGNATURE = 'RIPOSTE_WORKSPACE_1\n'
LEGACY_SIGNATURE = 'SHROUD_WORKSPACE_1\n'


@lru_cache(maxsize=16)
def _application_directory(module_file: str) -> Path:
    """Identify the loaded installation, independently of cwd and sys.prefix.

    A RIPOSTE src checkout protects its entire project. A wheel protects its
    package directory, not an arbitrary number of Python environment parents.
    Cache the loaded layout so repeated catalog/path checks do not parse TOML.
    """
    package = Path(module_file).resolve().parent
    if package.parent.name == "src":
        project_file = package.parent.parent / "pyproject.toml"
        if project_file.is_file():
            try:
                project = tomllib.loads(project_file.read_text(encoding="utf-8")).get("project", {})
            except (OSError, ValueError):
                raise RiposteError("APPLICATION_LAYOUT_INVALID") from None
            if isinstance(project, dict) and project.get("name") == "riposte-studio":
                return package.parent.parent
    return package


def application_directory() -> Path:
    return _application_directory(__file__)


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
    # Reject links before canonicalizing: resolution must not make a linked
    # selection acceptable. Canonical comparison also handles '..' and aliases.
    resolved = root.resolve()
    app = application_directory()
    if resolved == app or resolved.is_relative_to(app) or app.is_relative_to(resolved):
        raise RiposteError("IMAGE_FOLDER_OVERLAPS_APPLICATION")
    lease = root / LEASE_NAME
    if lease.exists() or lease.is_symlink():
        file_identity(lease)
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
    with workspace_lock(root):
        # Resolve again under the lease: another upgrade may have just finished.
        source, target = root / state_name(root), root / ".riposte"
        current = source
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

def _read_lock_marker(path: Path) -> tuple[bytes, tuple[int, int]] | None:
    try:
        before = path.lstat()
    except FileNotFoundError:
        return None
    if is_link(path) or not stat.S_ISREG(before.st_mode) or before.st_size > 512:
        raise RiposteError("STATE_PATH_INVALID")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        opened = os.fstat(stream.fileno())
        data = stream.read(513)
    identity = before.st_dev, before.st_ino
    after = path.lstat()
    if (not stat.S_ISREG(opened.st_mode) or len(data) > 512
            or (opened.st_dev, opened.st_ino) != identity
            or (after.st_dev, after.st_ino) != identity
            or (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns)):
        raise RiposteError("STATE_PATH_INVALID")
    return data, identity


def _publish_lock_marker(path: Path, data: bytes, token: str) -> tuple[int, int]:
    # Fully initialize before publishing. Even a hard exit cannot expose an
    # ambiguous empty marker; a legacy O_EXCL writer can still win this claim.
    temporary = path.with_name(".operation-" + token + ".tmp")
    try:
        with temporary.open("xb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise RiposteError("WORKSPACE_LOCKED") from None
        info = temporary.stat()
        return info.st_dev, info.st_ino
    finally:
        temporary.unlink(missing_ok=True)


@contextlib.contextmanager
def workspace_lock(root: Path) -> Iterator[None]:
    root = check_root(root)
    with file_lease(root / LEASE_NAME) as lease_identity:
        state = state_dir(root)
        if file_identity(root / LEASE_NAME) != lease_identity:
            raise RiposteError("STATE_PATH_INVALID")
        path = state / "operation.lock"
        root_info = root.stat()
        prefix = (f"RIPOSTE_OS_LEASE_1\n{root_info.st_dev}:{root_info.st_ino}\n"
                  f"{lease_identity[0]}:{lease_identity[1]}\n").encode("ascii")
        previous = _read_lock_marker(path)
        if previous is not None:
            data, _ = previous
            token_bytes = data[len(prefix):-1]
            if (not data.startswith(prefix) or not data.endswith(b"\n") or len(token_bytes) != 32
                    or any(c not in b"0123456789abcdef" for c in token_bytes)):
                # Empty/unrecognized old locks have no provable owner. Preserve
                # them; neither PID guesses nor elapsed time justify removal.
                raise RiposteError("WORKSPACE_LOCKED")
            if _read_lock_marker(path) != previous:
                raise RiposteError("WORKSPACE_LOCKED")
            path.unlink()
        token = uuid.uuid4().hex
        data = prefix + token.encode("ascii") + b"\n"
        marker_identity = _publish_lock_marker(path, data, token)
        try:
            yield
        finally:
            # Namespace upgrade renames the state directory while retaining the
            # same lease. Never unlink a marker substituted by another writer.
            current = root / state_name(root) / "operation.lock"
            if _read_lock_marker(current) == (data, marker_identity):
                current.unlink()

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

def catalog(root: Path) -> list[CatalogRow]:
    check_root(root)
    if not (root / state_relative(root, "catalog.sqlite3")).exists():
        return []
    with contextlib.closing(sqlite3.connect(safe_child(root, state_relative(root, "catalog.sqlite3")).as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        result = [cast(CatalogRow, dict(row)) for row in db.execute("SELECT * FROM images ORDER BY day DESC, relative")]
    for row in result:
        canonical_path(row["relative"])
    return result

def record_image(root: Path, relative: str, audit: PngAudit, size: int, date_source: str, *, db: sqlite3.Connection | None = None) -> CatalogRow:
    canonical_path(relative)
    row: CatalogRow = {"id": uuid.uuid4().hex, "relative": relative, "day": audit["date"],
           "date_source": date_source, "width": audit["width"], "height": audit["height"],
           "sha256": audit["sha256"], "bytes": size}
    with (contextlib.closing(connect(root)) if db is None else contextlib.nullcontext(db)) as db:
        db.execute("INSERT INTO images VALUES (:id,:relative,:day,:date_source,:width,:height,:sha256,:bytes)", row)
        db.commit()
    return row

def find_image(root: Path, identifier: str) -> CatalogRow:
    if len(identifier) != 32 or any(c not in "0123456789abcdef" for c in identifier):
        raise RiposteError("IMAGE_NOT_FOUND")
    root = check_root(root)
    database = safe_child(root, state_relative(root, "catalog.sqlite3"))
    if not database.exists():
        raise RiposteError("IMAGE_NOT_FOUND")
    with contextlib.closing(sqlite3.connect(database.as_uri() + "?mode=ro", uri=True)) as db:
        db.row_factory = sqlite3.Row
        found = db.execute("SELECT * FROM images WHERE id=?", (identifier,)).fetchone()
    if found is None:
        raise RiposteError("IMAGE_NOT_FOUND")
    row = cast(CatalogRow, dict(found))
    path = safe_child(root, canonical_path(row["relative"]))
    try:
        result = png_audit(path.read_bytes())
    except OSError:
        raise RiposteError("CATALOG_FILE_MISSING") from None
    if result["sha256"] != row["sha256"]:
        raise RiposteError("CATALOG_FILE_CHANGED")
    return row

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
