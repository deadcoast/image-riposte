"""Cross-platform key input with bounded escape/paste decoding and cleanup.

Windows uses msvcrt; POSIX uses cbreak + select. No eval, readline history, global
hotkey hook or keyboard capture outside this process's foreground terminal.
"""
from __future__ import annotations
from dataclasses import dataclass
import codecs
import contextlib
import os
import sys
import time

@dataclass(frozen=True)
class Key:
    name: str
    text: str = ""

SEQUENCES = {
    "\x1b[A": "up", "\x1b[B": "down", "\x1b[C": "right", "\x1b[D": "left",
    "\x1b[H": "home", "\x1b[F": "end", "\x1bOH": "home", "\x1bOF": "end",
    "\x1b[5~": "pageup", "\x1b[6~": "pagedown", "\x1b[3~": "delete",
    "\x1bOP": "f1", "\x1bOQ": "f2", "\x1bOR": "f3", "\x1bOS": "f4",
    "\x1b[11~": "f1", "\x1b[12~": "f2", "\x1b[13~": "f3", "\x1b[14~": "f4",
    "\x1b[Z": "backtab", "\x1b[1~": "home", "\x1b[4~": "end",
}
SINGLE = {"\r": "enter", "\n": "enter", "\t": "tab", "\x7f": "backspace", "\x08": "backspace", "\x03": "interrupt", "\x04": "eof", "\x15": "clear"}


class KeyDecoder:
    def __init__(self):
        self.buffer = ""
        self.pasting = False
        self.paste = ""
        self._paste_tail = ""

    def feed(self, value: str):
        self.buffer += value
        # A malicious/unrecognized sequence cannot allocate an unbounded buffer.
        if len(self.buffer) > 32768: self.buffer = self.buffer[:32768]

    def next(self, flush_escape=False) -> Key | None:
        if self.pasting:
            end = self.buffer.find("\x1b[201~")
            if end >= 0:
                value = (self.paste + self.buffer[:end])[:4096]
                self.buffer = self.buffer[end + 6:]
                self.paste = ""; self.pasting = False
                # Newlines are data, never queued Enter events.
                return Key("paste", "".join(c for c in value.replace("\r", " ").replace("\n", " ") if ord(c) >= 32 and ord(c) != 127))
            take = max(0, len(self.buffer) - 6)
            self.paste = (self.paste + self.buffer[:take])[:4096]
            self.buffer = self.buffer[take:]
            return None
        if not self.buffer: return None
        if self.buffer.startswith("\x1b[200~"):
            self.buffer = self.buffer[6:]; self.pasting = True
            return self.next(flush_escape)
        for sequence, name in SEQUENCES.items():
            if self.buffer.startswith(sequence):
                self.buffer = self.buffer[len(sequence):]
                return Key(name)
        if self.buffer[0] == "\x1b":
            known = list(SEQUENCES) + ["\x1b[200~"]
            if any(seq.startswith(self.buffer) for seq in known) and not flush_escape:
                return None
            if self.buffer == "\x1b":
                if not flush_escape: return None
                self.buffer = ""; return Key("escape")
            # Consume an unknown CSI sequence as a unit, never turn its suffix
            # into a menu shortcut (including mouse and modified-key sequences).
            if self.buffer.startswith(("\x1b[", "\x1bO")):
                end = next((i for i in range(2, len(self.buffer)) if "@" <= self.buffer[i] <= "~"), None)
                if end is None:
                    if flush_escape: self.buffer = ""
                    return None
                self.buffer = self.buffer[end + 1:]; return Key("ignored")
            self.buffer = self.buffer[2:]; return Key("ignored")
        char, self.buffer = self.buffer[0], self.buffer[1:]
        if char in SINGLE: return Key(SINGLE[char])
        if ord(char) < 32: return Key("ignored")
        return Key("char", char)


class TerminalKeys:
    def __init__(self, stream=None, output=None):
        self.stream = stream or sys.stdin
        self.output = output or sys.stdout
        self.decoder = KeyDecoder()
        self._unicode = codecs.getincrementaldecoder("utf-8")("replace")
        self._saved = None
        self._windows_prefix = None
        self.active = False

    def __enter__(self):
        if not self.stream.isatty(): raise OSError("Interactive input needs a terminal")
        if os.name != "nt":
            import termios, tty
            fd = self.stream.fileno()
            self._saved = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        try:
            self.output.write("\x1b[?2004h"); self.output.flush()
            self.active = True
        except BaseException:
            self.__exit__(None, None, None)
            raise
        return self

    def __exit__(self, *exc):
        try:
            if self._saved is not None:
                import termios
                termios.tcsetattr(self.stream.fileno(), termios.TCSADRAIN, self._saved)
        finally:
            self._saved = None
            with contextlib.suppress(Exception):
                self.output.write("\x1b[?2004l\x1b[?25h"); self.output.flush()
            self.active = False

    def read(self, timeout=.08) -> Key | None:
        value = self.decoder.next()
        if value is not None: return value
        if os.name == "nt":
            import msvcrt
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if msvcrt.kbhit():
                    char = msvcrt.getwch()
                    if self._windows_prefix is not None:
                        self._windows_prefix = None
                        return Key({"H":"up","P":"down","K":"left","M":"right","G":"home","O":"end","I":"pageup","Q":"pagedown","S":"delete",";":"f1","<":"f2","=":"f3",">":"f4"}.get(char,"ignored"))
                    if char in ("\x00", "\xe0"):
                        self._windows_prefix = char; continue
                    self.decoder.feed(char)
                    value = self.decoder.next()
                    if value: return value
                time.sleep(.006)
        else:
            import select
            readable, _, _ = select.select([self.stream.fileno()], [], [], timeout)
            if readable:
                raw = os.read(self.stream.fileno(), 8192)
                if not raw: return Key("eof")
                self.decoder.feed(self._unicode.decode(raw))
                return self.decoder.next()
        return self.decoder.next(flush_escape=True)
