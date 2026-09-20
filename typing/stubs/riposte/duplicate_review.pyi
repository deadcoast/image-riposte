"""Source-derived duplicate analysis contract; scores are evidence, not probabilities."""
from __future__ import annotations
import csv
import io
import json
import math
from pathlib import Path
from typing import cast
from .duplicate_media import thumbnail
from .duplicates import LABELS, Source, content_hash, verify_source, scan_root
from .errors import RiposteError
from .policy import is_link

class DuplicateReview:
    report: dict[str, object]
    sources: dict[str, dict[str, object]]
    groups: dict[str, dict[str, object]]
    findings: dict[str, dict[str, object]]
    rows: list[dict[str, object]]

    def __init__(self, report: dict[str, object]) -> None:
        ...

    def summary(self) -> dict[str, object]:
        ...

    def page(self, *, label: str=..., search: str=..., media: str=..., min_confidence: float=..., order: str=..., offset: int=..., limit: int=...) -> dict[str, object]:
        ...

    def select(self, *, label: str=..., search: str=..., media: str=..., min_confidence: float=..., order: str=...) -> list[dict[str, object]]:
        ...

    def group(self, identifier: str, *, offset: int=..., limit: int=...) -> dict[str, object]:
        ...

    def detail(self, identifier: str) -> dict[str, object]:
        ...

    def preview(self, identifier: str, *, timestamp: float | None=...) -> bytes:
        ...

    def export_bytes(self, kind: str=...) -> bytes:
        ...

    def export(self, target: Path) -> dict[str, object]:
        ...
