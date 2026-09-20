"""Non-blocking OS leases on a persistent private file; never delete that file.

The descriptor/handle owns the lease, not a PID or an age threshold. Its root
location stays fixed across legacy state-directory upgrades.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
import errno
import os
from pathlib import Path
import stat
import sys

from .errors import RiposteError
from .policy import is_link

LEASE_NAME = ".riposte-operation.lease"


def file_identity(path: Path) -> tuple[int, int]:
    info = path.lstat()
    if is_link(path) or not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_size != 0:
        raise RiposteError("STATE_PATH_INVALID")
    return info.st_dev, info.st_ino


def _windows_open(path: Path) -> int:
    if sys.platform != "win32":
        raise RiposteError("WORKSPACE_LOCK_UNAVAILABLE")
    import ctypes
    from ctypes import wintypes
    import msvcrt

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    create = api.CreateFileW
    create.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                       wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
    create.restype = wintypes.HANDLE
    close = api.CloseHandle
    close.argtypes = [wintypes.HANDLE]
    close.restype = wintypes.BOOL
    # READ|WRITE; share READ|WRITE|DELETE; OPEN_ALWAYS; OPEN_REPARSE_POINT.
    handle = create(str(path), 0xC0000000, 7, None, 4, 0x00200000, None)
    if handle == ctypes.c_void_p(-1).value:
        raise OSError(ctypes.get_last_error(), "lease open failed")
    try:
        return msvcrt.open_osfhandle(handle, os.O_RDWR | os.O_BINARY)
    except BaseException:
        close(handle)
        raise


def _windows_lock(fd: int, *, release: bool = False) -> None:
    if sys.platform != "win32":
        raise RiposteError("WORKSPACE_LOCK_UNAVAILABLE")
    import ctypes
    from ctypes import wintypes
    import msvcrt

    class Overlapped(ctypes.Structure):
        _fields_ = [("Internal", ctypes.c_size_t), ("InternalHigh", ctypes.c_size_t),
                    ("Offset", wintypes.DWORD), ("OffsetHigh", wintypes.DWORD),
                    ("hEvent", wintypes.HANDLE)]

    api = ctypes.WinDLL("kernel32", use_last_error=True)
    overlap = Overlapped()
    handle = msvcrt.get_osfhandle(fd)
    if release:
        unlock = api.UnlockFileEx
        unlock.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                           wintypes.DWORD, ctypes.POINTER(Overlapped)]
        unlock.restype = wintypes.BOOL
        result = unlock(handle, 0, 1, 0, ctypes.byref(overlap))
    else:
        lock = api.LockFileEx
        lock.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.DWORD,
                         wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(Overlapped)]
        lock.restype = wintypes.BOOL
        result = lock(handle, 3, 0, 1, 0, ctypes.byref(overlap))
    if not result:
        code = ctypes.get_last_error()
        if not release and code in {32, 33}:
            raise RiposteError("WORKSPACE_LOCKED")
        raise OSError(code, "lease operation failed")


@contextmanager
def file_lease(path: Path) -> Iterator[tuple[int, int]]:
    """Acquire exclusive ownership, or fail closed without waiting/replacing."""
    fd = -1
    locked = False
    try:
        if path.exists() or path.is_symlink():
            file_identity(path)
        if sys.platform == "win32":
            fd = _windows_open(path)
        else:
            fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
        os.set_inheritable(fd, False)
        info = os.fstat(fd)
        identity = info.st_dev, info.st_ino
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or file_identity(path) != identity:
            raise RiposteError("STATE_PATH_INVALID")
        if sys.platform == "win32":
            _windows_lock(fd)
        else:
            import fcntl
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                if exc.errno in {errno.EACCES, errno.EAGAIN}:
                    raise RiposteError("WORKSPACE_LOCKED") from None
                raise
        locked = True
        if file_identity(path) != identity:
            raise RiposteError("STATE_PATH_INVALID")
    except OSError:
        if fd != -1:
            os.close(fd)
        raise RiposteError("WORKSPACE_LOCK_UNAVAILABLE") from None
    except BaseException:
        if fd != -1:
            os.close(fd)
        raise
    try:
        yield identity
    finally:
        if fd != -1:
            try:
                if locked:
                    if sys.platform == "win32":
                        _windows_lock(fd, release=True)
                    else:
                        import fcntl
                        fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
