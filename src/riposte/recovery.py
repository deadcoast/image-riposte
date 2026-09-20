"""Read-only presentation guidance. Never retries or mutates an operation."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import TypedDict, cast

from .errors import safe_code


class Entry(TypedDict, total=False):
    title: str
    action: str
    level: str
    operations: dict[str, str]


class Catalog(TypedDict):
    version: int
    aliases: dict[str, str]
    entries: dict[str, Entry]


@dataclass(frozen=True)
class Guidance:
    code: str
    title: str
    action: str
    level: str = "error"


def _catalog() -> Catalog:
    try:
        value = json.loads((Path(__file__).parent / "static/recovery-catalog.json").read_text(encoding="utf-8"))
        if value["version"] != 1 or "OPERATION_FAILED" not in value["entries"]:
            raise ValueError("catalog version")
        if not all(isinstance(k, str) and isinstance(v, str) for k, v in value["aliases"].items()):
            raise ValueError("catalog aliases")
        for code, entry in value["entries"].items():
            if safe_code(code) != code or not all(isinstance(entry[k], str) and entry[k] for k in ("title", "action")):
                raise ValueError("catalog entry")
            if entry.get("level", "error") not in {"error", "info"}:
                raise ValueError("catalog level")
            if not all(isinstance(k, str) and isinstance(v, str) and v for k, v in entry.get("operations", {}).items()):
                raise ValueError("catalog operations")
        return cast(Catalog, value)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        # Missing installation data must not mask the original safe code.
        return {"version": 1, "aliases": {}, "entries": {"OPERATION_FAILED": {
            "title": "Operation needs attention.",
            "action": "Guidance is unavailable. Keep files and recovery records intact. Check the operation status before trying again; changes are never retried automatically.",
        }}}


CATALOG = _catalog()


def guidance(code: object, operation: str = "") -> Guidance:
    identifier = safe_code(code)
    entry = CATALOG["entries"].get(identifier, CATALOG["entries"]["OPERATION_FAILED"])
    family = CATALOG["aliases"].get(operation.split("/", 1)[0].lower(), "general")
    action = entry.get("operations", {}).get(family, entry["action"])
    return Guidance(identifier, entry["title"], action, entry.get("level", "error"))


def recovery_text(code: object, operation: str = "") -> str:
    item = guidance(code, operation)
    return f"{item.title} Next action: {item.action} Code: {item.code}"
