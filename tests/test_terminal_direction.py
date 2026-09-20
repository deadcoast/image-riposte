"""An extended Windows key's cached scan code is not another keyboard event."""
from collections import deque
from types import SimpleNamespace
import sys

import pytest

from riposte.terminal.keyboard import Key, TerminalKeys


@pytest.mark.parametrize("prefix", ["\x00", "\xe0"])
@pytest.mark.parametrize("code,expected", [("H", "up"), ("P", "down"), ("K", "left"),
    ("M", "right"), ("G", "home"), ("O", "end"), ("I", "pageup"),
    ("Q", "pagedown"), (";", "f1"), ("<", "f2"), ("=", "f3"), (">", "f4")])
def test_extended_key_consumes_cached_scan_code_without_another_kbhit(prefix, code, expected, monkeypatch):
    # Physical input and the CRT's cached wide scan-code buffer are separate.
    # kbhit becomes false once getwch consumes the physical key's prefix.
    physical = deque([(prefix, code)])
    cached = []

    def read():
        if cached:
            return cached.pop()
        lead, scan = physical.popleft()
        cached.append(scan)
        return lead

    monkeypatch.setitem(sys.modules, "msvcrt", SimpleNamespace(
        kbhit=lambda: bool(physical), getwch=read))
    monkeypatch.setattr("riposte.terminal.keyboard.os", SimpleNamespace(name="nt"))
    keyboard = TerminalKeys()
    assert keyboard.read(0) == Key(expected)
    assert not cached
    assert keyboard.read(0) is None
