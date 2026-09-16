"""A single foreground-owned worker. Only actual callback values are progress.

Workers are non-daemon and joined before terminal exit. Source replacement is not
interrupted by UI cancellation. Long model calls stop only at cooperative points.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from collections import deque
import threading
import time
import re
from typing import Any, Callable
from ..errors import RiposteError
from .service import Request, CANCELLABLE, execute, result_exit_code


def safe_code(value: object) -> str:
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", value) else "OPERATION_FAILED"


def safe_phase(value: object) -> str:
    # Existing callbacks are code-defined prose. Reject controls/path-like data;
    # never preserve a raw backend exception as a progress message.
    if not isinstance(value, str) or not value or len(value) > 120 or any(ord(c) < 32 or ord(c) > 126 for c in value):
        return "Working"
    if "\\" in value or ":" in value or value.startswith("/") or "../" in value:
        return "Working"
    return value


@dataclass
class Snapshot:
    state: str = "RUNNING"
    phase: str = "Starting operation"
    processed: int | None = None
    total: int | None = None
    item: int | None = None
    items: int | None = None
    elapsed: float = 0.0
    cancel_requested: bool = False
    cancellable: bool = True
    code: str | None = None
    batch_id: str | None = None
    events: tuple[str, ...] = ()


class Operation:
    def __init__(self, request: Request, function: Callable = execute):
        self.request, self.function = request, function
        self.cancellable = request.name in CANCELLABLE
        self.started = time.monotonic()
        self._lock = threading.Lock()
        self._cancel = threading.Event()
        self.done = threading.Event()
        self._snapshot = Snapshot(cancellable=self.cancellable)
        self._events: deque[str] = deque(maxlen=10)
        self.result: Any = None
        self.exit_code = 0
        self.thread = threading.Thread(target=self._run, name="riposte-foreground-operation", daemon=False)

    def start(self):
        self.thread.start()
        return self

    def progress(self, event: dict):
        if self._cancel.is_set() and self.cancellable:
            raise RiposteError("JOB_CANCELLED")
        if not isinstance(event, dict): return
        phase = safe_phase(event.get("phase"))
        with self._lock:
            if phase != self._snapshot.phase:
                self._events.append(phase)
                # Counts from a previous phase are not implied to cover the new one.
                self._snapshot.processed = self._snapshot.total = None
            self._snapshot.phase = phase
            for key in ("processed", "total", "item", "items"):
                value = event.get(key)
                if type(value) is int and 0 <= value <= 10**10:
                    setattr(self._snapshot, key, value)
            if self._snapshot.total is not None and self._snapshot.total <= 0: self._snapshot.total = None
            batch = event.get("batch_id")
            if isinstance(batch, str) and re.fullmatch(r"[0-9a-f]{32}", batch): self._snapshot.batch_id = batch

    def cancel(self) -> bool:
        if not self.cancellable: return False
        self._cancel.set()
        with self._lock: self._snapshot.cancel_requested = True
        return True

    def snapshot(self) -> Snapshot:
        with self._lock:
            return Snapshot(**{**vars(self._snapshot), "events": tuple(self._events), "elapsed": time.monotonic() - self.started})

    def _run(self):
        try:
            self.progress({"phase": "Starting operation"})
            self.result = self.function(self.request, self.progress)
            self.exit_code = result_exit_code(self.result)
            with self._lock:
                self._snapshot.state = "NEEDS_ATTENTION" if self.exit_code else "DONE"
                self._snapshot.phase = "Finished with blockers" if self.exit_code else "Operation finished"
        except RiposteError as exc:
            code = safe_code(exc.code)
            self.exit_code = 130 if code == "JOB_CANCELLED" else 2
            with self._lock:
                self._snapshot.state = "CANCELLED" if code == "JOB_CANCELLED" else "ERROR"
                self._snapshot.code = code
                self._snapshot.phase = "Stopped at a checkpoint" if code == "JOB_CANCELLED" else "Operation stopped"
        except BaseException:
            self.exit_code = 2
            with self._lock:
                self._snapshot.state, self._snapshot.code = "ERROR", "OPERATION_FAILED"
                self._snapshot.phase = "Operation stopped"
        finally:
            self.done.set()

    def join(self):
        self.thread.join()
        return self.result
