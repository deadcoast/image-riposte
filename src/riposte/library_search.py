"""Opt-in private image-library search. Never enrich the ordinary catalog.

One read transaction joins provenance to catalog identity. This is a metadata
lookup, not a fresh audit of every image's bytes. Opening an image still audits it.
"""
from __future__ import annotations

import contextlib
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import unicodedata
from typing import Literal, TypedDict, cast

from .errors import RiposteError
from .policy import BINS, MONTHS, canonical_path
from .records import CatalogRow, Progress
from .sort_titles import validate_title
from .store import check_root, safe_child, state_relative


class SearchRow(CatalogRow):
    original_filename: str | None
    category: str | None
    provenance: Literal["MATCHED", "MISSING", "MISMATCHED", "INVALID"]
    title_state: Literal["KNOWN", "UNKNOWN"]


class SearchReport(TypedDict):
    mode: Literal["PRIVATE_LIBRARY_SEARCH"]
    rows: list[SearchRow]
    total: int
    limit: int
    offset: int
    next_offset: int | None
    revision: str
    basis: str


def normalized(value: str) -> str:
    return unicodedata.normalize("NFKC", value).casefold()


def search_library(root: Path, *, search: str = "", category: str = "",
                   title_state: str = "all", year: str | None = None,
                   month: str | int | None = None, size: str | None = None,
                   limit: int = 50, offset: int = 0,
                   expected_revision: str | None = None,
                   progress: Progress | None = None) -> SearchReport:
    """Literal Unicode search; exact category slug; AND-combined filters.

    Return at most 500 rows, ordered by day descending then path and ID. A
    revision binds the catalog, bounded provenance read and filter settings;
    callers paging that revision must restart if it changes. No query is saved.
    """
    root = check_root(root)
    if (type(limit) is not int or not 1 <= limit <= 500 or
            type(offset) is not int or not 0 <= offset <= 1_000_000_000):
        raise RiposteError("PAGINATION_INVALID")
    if (not isinstance(search, str) or len(search) > 200 or
            not isinstance(category, str) or len(category) > 96 or
            title_state not in {"all", "known", "unknown"}):
        raise RiposteError("LIBRARY_SEARCH_INVALID")
    if expected_revision is not None and not re.fullmatch(r"[0-9a-f]{64}", expected_revision):
        raise RiposteError("LIBRARY_SEARCH_INVALID")
    if year not in (None, "", "all", "EVERYTHING_ELSE") and (not isinstance(year, str) or not re.fullmatch(r"[0-9]{4}", year) or year == "0000"):
        raise RiposteError("YEAR_FILTER_INVALID")
    if size not in (None, "", "all", *BINS):
        raise RiposteError("SIZE_FILTER_INVALID")
    if month not in (None, "", "all", "ALL"):
        word = str(month)
        months = [m for i, m in enumerate(MONTHS, 1) if word.lower() in {m.lower(), m[:3].lower(), str(i)}]
        if len(months) != 1:
            raise RiposteError("MONTH_FILTER_INVALID")
        month = months[0]
    else:
        month = None
    query, category = normalized(search.strip()), normalized(category.strip())
    revision = hashlib.sha256(json.dumps([query, category, title_state, year, month, size, limit]).encode())
    rows: list[SearchRow] = []
    total = 0
    path = safe_child(root, state_relative(root, "catalog.sqlite3"))
    if progress:
        progress({"phase": "Searching private library", "processed": 0})
    if path.exists():
        try:
            with contextlib.closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=2)) as db:
                db.row_factory = sqlite3.Row
                db.execute("BEGIN")
                titles = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='sort_titles'").fetchone()
                # Bound individual untrusted JSON before decoding; do not load the
                # full title table or perform one catalog lookup per result.
                sql = ("SELECT i.*, substr(t.data,1,16385) AS private_title FROM images i LEFT JOIN sort_titles t ON t.id=i.id "
                       if titles else "SELECT i.*, NULL AS private_title FROM images i ")
                for index, record in enumerate(db.execute(sql + "ORDER BY i.day DESC, i.relative, i.id")):
                    row = dict(record)
                    raw = row.pop("private_title")
                    canonical_path(row["relative"])
                    revision.update(json.dumps([row, raw], sort_keys=True, ensure_ascii=True).encode())
                    if progress and index % 128 == 0:
                        progress({"phase": "Searching private library", "processed": index})
                    parts = row["relative"].split("/")
                    if year not in (None, "", "all") and parts[0] != year:
                        continue
                    if month is not None and parts[1] != month:
                        continue
                    if size not in (None, "", "all") and parts[-2] != size:
                        continue
                    item = cast(SearchRow, {**row, "original_filename": None, "category": None,
                                           "provenance": "MISSING", "title_state": "UNKNOWN"})
                    if raw is not None:
                        try:
                            if not isinstance(raw, str) or len(raw) > 16384:
                                raise ValueError("bounded title")
                            title = json.loads(raw)
                            validate_title(title)
                            if title["id"] != row["id"] or title["media"] != "img" or title["sha256"] != row["sha256"]:
                                item["provenance"] = "MISMATCHED"
                            else:
                                item["original_filename"] = title["original_filename"]
                                item["category"] = title["category"]
                                item["provenance"] = "MATCHED"
                                item["title_state"] = "KNOWN" if item["original_filename"] else "UNKNOWN"
                        except (RiposteError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
                            item["provenance"] = "INVALID"
                    if title_state != "all" and item["title_state"].lower() != title_state:
                        continue
                    if category and normalized(item["category"] or "") != category:
                        continue
                    searchable = " ".join(str(item[k] or "") for k in ("relative", "id", "day", "original_filename", "category"))
                    if query and query not in normalized(searchable):
                        continue
                    if offset <= total < offset + limit:
                        rows.append(item)
                    total += 1
        except sqlite3.Error:
            raise RiposteError("LIBRARY_SEARCH_UNAVAILABLE") from None
    current = revision.hexdigest()
    if expected_revision is not None and expected_revision != current:
        raise RiposteError("LIBRARY_SEARCH_STALE")
    if progress:
        progress({"phase": "Private library search complete", "processed": total})
    return {"mode": "PRIVATE_LIBRARY_SEARCH", "rows": rows, "total": total, "limit": limit, "offset": offset,
            "next_offset": offset + limit if offset + limit < total else None, "revision": current,
            "basis": "Private metadata matched to catalog ID, image type and stored hash. Image bytes are audited when opened; this search does not audit them."}
