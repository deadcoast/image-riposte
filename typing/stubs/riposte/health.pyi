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

class _DirectoryEntries(Protocol):

    def __next__(self) -> os.DirEntry[str]:
        ...

    def close(self) -> None:
        ...

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
    ...

def operation_observation(root: Path) -> dict[str, str]:
    ...

def _journal(root: Path, path: Path) -> str:
    ...

def inspect_health(root: Path, *, max_entries: int=MAX_ENTRIES, progress: Progress | None=None) -> HealthReport:
    ...
MAX_ENTRIES: int
MAX_JOURNAL_BYTES: int
HISTORY_ID: re.Pattern[str]
