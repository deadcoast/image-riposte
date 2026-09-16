"""Bounded SIGTERM handling: restore terminal state and join owned operations.

SIGKILL and power loss cannot run Python cleanup. No stronger claim is made.
"""
from __future__ import annotations
from contextlib import contextmanager
import signal
import threading


class TerminationRequested(BaseException):
    pass


@contextmanager
def termination_guard():
    if threading.current_thread() is not threading.main_thread():
        yield
        return
    previous = signal.getsignal(signal.SIGTERM)
    requested = False

    def terminate(_signum, _frame):
        nonlocal requested
        if not requested:
            requested = True
            raise TerminationRequested()

    signal.signal(signal.SIGTERM, terminate)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)
