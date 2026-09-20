"""Error codes, never decoder messages, source paths, or source metadata."""
import re


def safe_code(value: object) -> str:
    return value if isinstance(value, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", value) else "OPERATION_FAILED"


class RiposteError(Exception):
    def __init__(self, code: str):
        self.code = safe_code(code)
        super().__init__(self.code)
