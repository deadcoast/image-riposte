"""Read-only exact category plans. Application stays in the existing sorter."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import json
import os
import unicodedata
from pathlib import Path
from typing import cast
from .records import MediaInfo
from typing import Any, Callable, Sequence

from .category_rules import load_rules, match_title
from .errors import RiposteError
from .policy import Policy, sort_folder_for, sort_excluded, path_category
from .sanitize import decode_clean, encode_clean, png_audit
from .sort_history import latest_sort
from .sort_titles import title_records
from .store import check_root, safe_child
from .video import file_hash, inspect_video
from .title_categories import GENERATED_TITLE


def source_state(path: Path) -> list[int]:
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
    if not os.path.samestat(before, path.stat()) or before.st_nlink != 1:
        raise RiposteError("SOURCE_CHANGED")
    return [before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns]


def verify_source(root: Path, item: dict[str, Any]) -> None:
    path = safe_child(root, item["source"])
    try:
        if (source_state(path) != item["source_state"] or file_hash(path) != item["source_sha256"]
                or source_state(path) != item["source_state"]):
            raise RiposteError("CATEGORY_PREVIEW_CHANGED")
    except OSError:
        raise RiposteError("CATEGORY_PREVIEW_CHANGED") from None


def category_plan(root: Path, policy: Policy, *, assignments: Sequence[str] = (),
                  progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    from .organizer import walk_inputs, known_good, _next_relative, _validate_managed
    root = check_root(root)
    if sort_excluded(root.resolve()):
        raise RiposteError("SORT_FLOAT_ROOT")
    rules = load_rules(root)
    labels = {r.slug: r.label for r in rules.rules} | {"uncategorized": "Uncategorized"}
    overrides: dict[str, str] = {}
    for spec in assignments:
        if not isinstance(spec, str):
            raise RiposteError("CATEGORY_ASSIGNMENT_INVALID")
        relative, sep, slug = spec.rpartition("=")
        if (not sep or not relative or slug not in labels and slug != "auto" or relative in overrides
                or Path(relative).as_posix() != relative or relative.split("/")[0] in {".riposte", ".shroud"}):
            raise RiposteError("CATEGORY_ASSIGNMENT_INVALID")
        safe_child(root, relative)
        overrides[relative] = slug
    managed = known_good(root)
    titles = title_records(root)
    provenance = {r["id"]: r for r in titles}
    counts: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    folders: Counter[str] = Counter()
    files: list[dict[str, Any]] = []
    seen: set[str] = set()
    numbers: dict[Path, int] = {}
    history = latest_sort(root)
    if history and history["status"] in {"APPLYING", "UNDOING"}:
        blockers["SORT_RECOVERY_REQUIRED"] += 1
    for index, (path, kind) in enumerate(walk_inputs(root), 1):
        if progress:
            progress({"phase": "Planning categories", "processed": index})
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        item: dict[str, Any] = {"source": relative, "original_filename": None, "kind": kind,
                               "matched_terms": [], "category": None, "destination": None}
        files.append(item)
        try:
            if kind not in {"IMAGE", "VIDEO"} and not (kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars):
                raise RiposteError(kind)
            item["source_state"] = source_state(path)
            item["source_sha256"] = file_hash(path)
            if kind == "SIDECAR_REQUIRES_DISCARD":
                item["action"] = "DISCARD"
                counts["sidecars_to_discard"] += 1
                continue
            media = "vid" if kind == "VIDEO" else "img"
            previous = managed.get(relative)
            old = provenance.get(previous["id"]) if previous else None
            if old and previous is not None and (old["sha256"] != previous["sha256"] or old["media"] != media):
                raise RiposteError("TITLE_PROVENANCE_CHANGED")
            original = old["original_filename"] if old else None if previous else path.name
            if original and GENERATED_TITLE.fullmatch(unicodedata.normalize("NFKC", Path(original).stem)):
                original = None
            item["original_filename"] = original
            manual = overrides.get(relative)
            if manual is None and old and old["manual"]:
                manual = old["category"]
            match: dict[str, Any]
            if manual and manual != "auto":
                # Explicit new assignments were validated above. A saved manual
                # choice remains meaningful even after its matching rule goes away.
                match = {"status": "MANUAL", "category": {"slug": manual, "label": labels.get(manual, manual)}, "matches": []}
            else:
                match = match_title(Path(original).stem, rules.rules) if original else {"status": "ORIGINAL_TITLE_UNAVAILABLE", "category": None, "matches": []}
            item["match_status"] = match["status"]
            item["matches"] = match["matches"]
            counts[match["status"].lower() + "_files"] += 1
            category = match["category"]
            category_source = match["status"] if category else "NONE"
            if category is None and previous and manual != "auto":
                # No new match is not consent to remove an existing category.
                # The catalog's canonical path is usable even for legacy rows
                # whose original-title record is absent.
                retained = path_category(relative)
                if retained:
                    category = {"slug": retained, "label": labels.get(retained, retained)}
                    category_source = "PRESERVED"
            category_slug = category["slug"] if category else None
            terms: list[str] = next((r["matched_terms"] for r in match["matches"] if r["slug"] == category_slug), [])
            item.update(category=category, category_source=category_source, matched_terms=terms)
            counts["category_files" if category else "without_category_files"] += 1
            if previous:
                if not _validate_managed(path, previous):
                    raise RiposteError("CATALOG_FILE_CHANGED")
                info = cast(MediaInfo, dict(previous))
            elif media == "vid":
                info = cast(MediaInfo, inspect_video(path, policy))
                info.pop("source_stat")
            else:
                clean = decode_clean(path, policy)
                data = encode_clean(clean.pixels, clean.day)
                audit = png_audit(data)
                info = {"day": audit["date"], "date_source": clean.date_source, "width": audit["width"],
                        "height": audit["height"], "sha256": audit["sha256"], "bytes": len(data)}
            folder = sort_folder_for(info["day"], info["width"], info["height"], media, category_slug)
            staying = previous is not None and path.parent.relative_to(root) == folder
            destination = relative if staying else _next_relative(root, folder, path.suffix.lower() if media == "vid" else ".png", next_numbers=numbers)
            item.update(destination=destination, action="KEEP" if staying else "SORT", expected=info,
                        title={"id": previous["id"] if previous else None, "media": media, "original_filename": original,
                               "category": category_slug, "manual": match["status"] == "MANUAL", "matched_terms": terms,
                               "sha256": info["sha256"], "rule_revision": rules.revision})
            folders[folder.as_posix()] += 1
            counts["already_sorted" if staying else "files_to_sort"] += 1
            verify_source(root, item)
        except RiposteError as exc:
            blockers[exc.code] += 1
            item["error"] = exc.code
        except OSError:
            blockers["IO_OPERATION_FAILED"] += 1
            item["error"] = "IO_OPERATION_FAILED"
    for _ in set(managed) - seen:
        blockers["CATALOG_FILE_MISSING"] += 1
    if set(overrides) - seen or any(r["source"] in overrides and r["kind"] not in {"IMAGE", "VIDEO"} for r in files):
        blockers["CATEGORY_ASSIGNMENT_INVALID"] += 1
    root_stat = root.stat()
    basis = {"version": 2, "root": str(root), "identity": [root_stat.st_dev, root_stat.st_ino],
             "policy": asdict(policy), "rules": rules.revision, "titles": titles, "catalog": managed,
             "history": {k: history[k] for k in ("id", "status")} if history else None,
             "assignments": overrides, "files": files, "blockers": dict(blockers)}
    token = hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=True).encode()).hexdigest()
    return {"mode": "READ_ONLY", "category_sorting": True, "plan_id": token, "rules_revision": rules.revision,
            "ready": not blockers, "counts": dict(counts), "destinations": dict(sorted(folders.items())),
            "blockers": dict(blockers), "files": files,
            "source_policy": "Original names, bytes and category assignments are kept privately for Undo last sort.",
            "video_policy": "SORT_ONLY_BYTES_UNCHANGED"}
