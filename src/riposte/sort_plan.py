"""Read-only ordinary sort receipts; execution remains in the shared organizer."""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import cast
from .records import MediaInfo
from typing import Any, Callable
import unicodedata

from .category_sort import source_state, verify_source
from .errors import RiposteError
from .policy import Policy, path_category, sort_folder_for
from .sanitize import decode_clean, encode_clean, png_audit
from .sort_history import latest_sort
from .sort_titles import title_records
from .store import check_root
from .title_categories import GENERATED_TITLE
from .video import file_hash, inspect_video


def receipt(basis: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(basis, sort_keys=True, ensure_ascii=True, allow_nan=False).encode()).hexdigest()


def verify_sort_source(root: Path, item: dict[str, Any]) -> None:
    try:
        verify_source(root, item)
    except (OSError, RiposteError):
        raise RiposteError("SORT_PREVIEW_CHANGED") from None


def ordinary_plan(root: Path, policy: Policy, progress: Callable[[dict[str, Any]], None] | None = None) -> dict[str, Any]:
    from .organizer import walk_inputs, known_good, _next_relative, _validate_managed

    root = check_root(root)
    managed, titles = known_good(root), title_records(root)
    provenance = {row["id"]: row for row in titles}
    history = latest_sort(root)
    counts: Counter[str] = Counter()
    folders: Counter[str] = Counter()
    blockers: Counter[str] = Counter()
    files: list[dict[str, Any]] = []
    numbers: dict[Path, int] = {}
    seen: set[str] = set()
    for index, (path, kind) in enumerate(walk_inputs(root), 1):
        if progress:
            progress({"phase": "Inspecting", "processed": index})
        relative = path.relative_to(root).as_posix()
        seen.add(relative)
        item: dict[str, Any] = {"source": relative, "kind": kind, "action": "BLOCKED", "destination": None}
        files.append(item)
        try:
            # Even untouched blockers bind their observed identity, without
            # following links or reading arbitrary unsupported file contents.
            state = path.lstat()
            item["observed_state"] = [state.st_dev, state.st_ino, state.st_mode, state.st_size, state.st_mtime_ns, state.st_ctime_ns]
            if kind not in {"IMAGE", "VIDEO"} and not (kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars):
                raise RiposteError(kind)
            if state.st_nlink != 1:
                raise RiposteError("HARDLINK_REQUIRES_REVIEW")
            if kind in {"IMAGE", "VIDEO"} and state.st_size > policy.max_file_bytes:
                raise RiposteError("FILE_LIMIT")
            item["source_state"] = source_state(path)
            item["source_sha256"] = file_hash(path)
            if kind == "SIDECAR_REQUIRES_DISCARD":
                verify_sort_source(root, item)
                item["action"] = "DISCARD"
                counts["sidecars_to_discard"] += 1
                continue
            previous = managed.get(relative)
            media = "vid" if kind == "VIDEO" else "img"
            if previous:
                if not _validate_managed(path, previous):
                    raise RiposteError("CATALOG_FILE_CHANGED")
                info = cast(MediaInfo, dict(previous))
            elif kind == "VIDEO":
                info = cast(MediaInfo, inspect_video(path, policy))
                info.pop("source_stat")
            else:
                clean = decode_clean(path, policy)
                data = encode_clean(clean.pixels, clean.day)
                audit = png_audit(data)
                info = {"day": audit["date"], "date_source": clean.date_source, "width": audit["width"],
                        "height": audit["height"], "sha256": audit["sha256"], "bytes": len(data)}
            category = path_category(relative) if previous else None
            folder = sort_folder_for(info["day"], info["width"], info["height"], media, category)
            staying = previous is not None and path.parent.relative_to(root) == folder
            destination = relative if staying else _next_relative(root, folder, path.suffix.lower() if kind == "VIDEO" else ".png", next_numbers=numbers)
            title = provenance.get(previous["id"]) if previous else {
                "id": None, "media": media,
                "original_filename": None if GENERATED_TITLE.fullmatch(unicodedata.normalize("NFKC", path.stem)) else path.name,
                "category": None, "manual": False, "matched_terms": [], "rule_revision": None, "sha256": info["sha256"],
            }
            item.update(destination=destination, expected=info, title=title)
            verify_sort_source(root, item)
            item["action"] = "KEEP" if staying else "SORT"
            if staying:
                counts["already_sorted_videos" if kind == "VIDEO" else "already_clean"] += 1
            else:
                folders[folder.as_posix()] += 1
                counts["images_to_relocate" if previous else "videos_to_sort" if kind == "VIDEO" else "images_to_migrate"] += 1
                if not previous:
                    counts["input_bytes"] += state.st_size
        except RiposteError as exc:
            item["error"] = exc.code
            blockers[exc.code] += 1
        except OSError:
            item["error"] = "IO_OPERATION_FAILED"
            blockers["IO_OPERATION_FAILED"] += 1
    for _ in set(managed) - seen:
        blockers["CATALOG_FILE_MISSING"] += 1
    if history and history["status"] in {"APPLYING", "UNDOING"}:
        blockers["SORT_RECOVERY_REQUIRED"] += 1
    root_stat = root.stat()
    basis = {"version": "riposte-ordinary-sort-1", "root": str(root.resolve()), "identity": [root_stat.st_dev, root_stat.st_ino],
             "policy": asdict(policy), "catalog": managed, "titles": titles,
             "history": {key: history[key] for key in ("id", "status")} if history else None,
             "files": files, "blockers": dict(blockers)}
    return {"mode": "READ_ONLY", "category_sorting": False, "plan_id": receipt(basis), "files": files,
            "counts": dict(counts), "destinations": dict(sorted(folders.items())), "blockers": dict(blockers), "ready": not blockers,
            "source_policy": "Original bytes and names are kept privately for Undo last sort. Images become date-only PNGs; videos retain all bytes and metadata.",
            "video_policy": "SORT_ONLY_BYTES_UNCHANGED"}
