from __future__ import annotations
import collections
import contextlib
import os
from pathlib import Path
from typing import Callable
from PIL import Image, UnidentifiedImageError
from .errors import RiposteError
from .policy import Policy, IMAGE_SUFFIXES, SIDECAR_SUFFIXES, CACHE_NAMES, folder_for, sort_folder_for, is_link, same_file_state
from .sanitize import decode_clean, encode_clean, png_audit
from .store import check_root, workspace_lock, catalog, record_image, atomic_clean_write, write_report, safe_child, state_name, connect
from .video import VIDEO_SUFFIXES, inspect_video, video_catalog, record_video, file_hash
from .sort_history import SortHistory, copy_exclusive, pending_sort, undo_sort

Progress = Callable[[dict], None]

def walk_inputs(root: Path):
    """No generated previews, linked directories, junctions, or raw-path logging."""
    root = check_root(root)
    for directory, dirs, names in os.walk(root, followlinks=False):
        current = Path(directory)
        for name in sorted(dirs.copy()):
            path = current / name
            if current == root and name == state_name(root):
                dirs.remove(name)
            elif is_link(path):
                dirs.remove(name)
                yield path, "LINK_REQUIRES_REVIEW"
        dirs.sort()
        for name in sorted(names):
            path = current / name
            if is_link(path):
                yield path, "LINK_REQUIRES_REVIEW"
            elif path.suffix.lower() in SIDECAR_SUFFIXES or name.lower() in CACHE_NAMES:
                yield path, "SIDECAR_REQUIRES_DISCARD"
            elif path.suffix.lower() in VIDEO_SUFFIXES:
                yield path, "VIDEO"
            else:
                try:
                    with Image.open(path):
                        pass
                    yield path, "IMAGE"
                except (UnidentifiedImageError, OSError, ValueError):
                    yield path, "DECODE_FAILED" if path.suffix.lower() in IMAGE_SUFFIXES else "NONIMAGE_REQUIRES_REVIEW"
                except Exception:
                    yield path, "DECODE_FAILED"

def known_good(root: Path) -> dict[str, dict]:
    return {row["relative"]: row for row in catalog(root) + video_catalog(root)}

def _validate_managed(path: Path, row: dict) -> bool:
    try:
        if "/vid/" in row["relative"]:
            return file_hash(path) == row["sha256"]
        audit = png_audit(path.read_bytes())
        return audit["sha256"] == row["sha256"]
    except (OSError, RiposteError):
        return False

def plan(root: Path, policy: Policy = Policy(), progress: Progress | None = None) -> dict:
    """Read-only including an uninitialized workspace: no directories created."""
    root = check_root(root)
    managed = known_good(root)
    counts, folders, errors = collections.Counter(), collections.Counter(), collections.Counter()
    seen = set()
    for index, (path, kind) in enumerate(walk_inputs(root), 1):
        if progress:
            progress({"phase": "Inspecting", "processed": index})
        seen.add(path.relative_to(root).as_posix())
        if kind not in {"IMAGE", "VIDEO"}:
            if kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars:
                counts["sidecars_to_discard"] += 1
            else:
                errors[kind] += 1
            continue
        rel = path.relative_to(root).as_posix()
        if rel in managed:
            if _validate_managed(path, managed[rel]):
                row = managed[rel]
                target = sort_folder_for(row["day"], row["width"], row["height"], "vid" if kind == "VIDEO" else "img")
                if path.parent.relative_to(root) != target:
                    counts["images_to_relocate"] += 1
                    folders[target.as_posix()] += 1
                else:
                    counts["already_sorted_videos" if kind == "VIDEO" else "already_clean"] += 1
            else:
                errors["CATALOG_FILE_CHANGED"] += 1
            continue
        try:
            if kind == "VIDEO":
                info = inspect_video(path, policy)
                folder = sort_folder_for(info["day"], info["width"], info["height"], "vid").as_posix()
            else:
                clean = decode_clean(path, policy)
                folder = sort_folder_for(clean.day, *clean.pixels.size).as_posix()
            folders[folder] += 1
            counts["videos_to_sort" if kind == "VIDEO" else "images_to_migrate"] += 1
            counts["input_bytes"] += path.stat().st_size
        except RiposteError as exc:
            errors[exc.code] += 1
    for missing in set(managed) - seen:
        errors["CATALOG_FILE_MISSING"] += 1
    if pending_sort(root):
        errors["SORT_RECOVERY_REQUIRED"] += 1
    return {"mode": "READ_ONLY", "counts": dict(counts), "destinations": dict(sorted(folders.items())),
            "blockers": dict(errors), "ready": not bool(errors),
            "source_policy": "Original bytes and names are kept privately for Undo last sort. Images become date-only PNGs; videos retain all bytes and metadata.",
            "video_policy": "SORT_ONLY_BYTES_UNCHANGED"}

def _next_relative(root: Path, folder: Path, suffix: str = ".png", *, next_numbers: dict[Path, int] | None = None) -> str:
    """Reserve each attempted sequence number for this sort, even after failure."""
    dest = safe_child(root, folder.as_posix())
    code = folder.name
    if next_numbers is None:
        next_numbers = {}
    if folder not in next_numbers:
        highest = 0
        if dest.exists():
            for entry in dest.iterdir():
                stem = entry.stem
                digits = stem[len(code):]
                if stem.startswith(code) and digits.isascii() and digits.isdigit():
                    highest = max(highest, int(digits))
        next_numbers[folder] = highest + 1
    number = next_numbers[folder]
    # External additions can occupy a name after the initial directory scan.
    while True:
        name = f"{code}{number:02d}{suffix}"
        candidate = dest / name
        if not candidate.exists() and not candidate.is_symlink():
            break
        number += 1
    next_numbers[folder] = number + 1
    return (folder / name).as_posix()

def organize(root: Path, policy: Policy = Policy(), progress: Progress | None = None) -> dict:
    """Verified commit before source unlink. No silent deletion of undecodable data."""
    root = check_root(root)
    counts, errors = collections.Counter(), collections.Counter()
    with workspace_lock(root):
        history = SortHistory(root)
        managed = known_good(root)
        next_numbers: dict[Path, int] = {}
        # Snapshot paths; originals are copied privately before any source unlink.
        inputs = list(walk_inputs(root))
        for index, (path, kind) in enumerate(inputs, 1):
            if progress:
                progress({"phase": "Cleansing / organizing", "processed": index, "total": len(inputs)})
            try:
                if kind not in {"IMAGE", "VIDEO"}:
                    if kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars:
                        if path.stat().st_nlink > 1:
                            raise RiposteError("HARDLINK_REQUIRES_REVIEW")
                        entry = history.prepare(path, None, None, "sidecar")
                        history.remove_source(entry)
                        counts["sidecars_discarded"] += 1
                    else:
                        errors[kind] += 1
                    continue
                rel = path.relative_to(root).as_posix()
                previous = managed.get(rel)
                if previous is not None:
                    if not _validate_managed(path, previous):
                        errors["CATALOG_FILE_CHANGED"] += 1
                        continue
                    target = sort_folder_for(previous["day"], previous["width"], previous["height"], "vid" if kind == "VIDEO" else "img")
                    if path.parent.relative_to(root) == target:
                        counts["already_sorted_videos" if kind == "VIDEO" else "already_clean"] += 1
                        continue
                if kind == "VIDEO":
                    info = inspect_video(path, policy)
                    source_stat = info.pop("source_stat")
                    folder = sort_folder_for(info["day"], info["width"], info["height"], "vid")
                    relative = _next_relative(root, folder, path.suffix.lower(), next_numbers=next_numbers)
                    entry = history.prepare(path, relative, {**info, "relative": relative}, "vid")
                    try:
                        copy_exclusive(root, path, relative, info["sha256"])
                    except RiposteError as exc:
                        if exc.code == "DESTINATION_EXISTS":
                            history.reject_output(entry)
                        raise
                    row = record_video(root, relative, info)
                else:
                    clean = decode_clean(path, policy)
                    source_stat = clean.source_stat
                    data = path.read_bytes() if previous else encode_clean(clean.pixels, clean.day)
                    result = png_audit(data)
                    date_source = previous["date_source"] if previous else clean.date_source
                    folder = sort_folder_for(result["date"], result["width"], result["height"])
                    relative = _next_relative(root, folder, next_numbers=next_numbers)
                    expected = {"relative": relative, "day": result["date"], "width": result["width"], "height": result["height"],
                                "sha256": result["sha256"], "bytes": len(data), "date_source": date_source}
                    if previous:
                        expected["id"] = previous["id"]
                    entry = history.prepare(path, relative, expected, "img", previous)
                    try:
                        atomic_clean_write(root, relative, data)
                    except RiposteError as exc:
                        if exc.code == "DESTINATION_EXISTS":
                            history.reject_output(entry)
                        raise
                    if previous:
                        with contextlib.closing(connect(root)) as db:
                            db.execute("UPDATE images SET relative=? WHERE id=?", (relative, previous["id"]))
                            db.commit()
                        row = expected
                        del managed[rel]
                    else:
                        row = record_image(root, relative, result, len(data), date_source)
                managed[relative] = row
                # Use fstat on both sides: Windows Path.stat and fstat do not
                # consistently expose the same ctime. Keep ctime change checks,
                # including edits that restore mtime, and bind the path to the
                # reopened descriptor before removing the verified source.
                with path.open("rb") as source:
                    current = os.fstat(source.fileno())
                    unchanged = same_file_state(source_stat, current)
                    path_state = path.stat()
                    unchanged = unchanged and os.path.samestat(current, path_state)
                if (is_link(path) or not unchanged
                    or not same_file_state(path_state, path.stat())):
                    raise RiposteError("SOURCE_CHANGED_OUTPUT_RETAINED")
                history.remove_source(entry)
                counts["videos_sorted" if kind == "VIDEO" else "relocated" if previous else "migrated"] += 1
            except RiposteError as exc:
                errors[exc.code] += 1
            except Exception:
                errors["IO_OPERATION_FAILED"] += 1
        # Only truly empty old folders; files of unknown purpose are never discarded.
        for source, _ in inputs:
            for path in source.parents:
                if path == root or is_link(path):
                    break
                try:
                    path.rmdir()
                except OSError:
                    break
        # Rescan so concurrent additions / residual originals cannot be called clean.
        remaining = 0
        seen = set()
        for path, kind in walk_inputs(root):
            relative = path.relative_to(root).as_posix()
            seen.add(relative)
            if kind not in {"IMAGE", "VIDEO"} or relative not in managed or not _validate_managed(path, managed[relative]):
                remaining += 1
        for missing in set(managed) - seen:
            errors["CATALOG_FILE_MISSING"] += 1
        report = {"mode": "APPLY", "counts": dict(counts), "blockers": dict(errors),
                  "unmanaged_or_changed_remaining": remaining,
                  "checkpoint": "COMPLETE" if not errors and not remaining else "INCOMPLETE",
                  "metadata_policy": "DATE_ONLY_IMAGES", "video_policy": "SORT_ONLY_BYTES_UNCHANGED",
                  "source_backups": "PRIVATE_UNDO_HISTORY", "sort_id": history.finish()}
        write_report(root, "last-run.json", report)
        return report

def audit_workspace(root: Path) -> dict:
    root = check_root(root)
    managed = known_good(root)
    errors = collections.Counter()
    count = videos = 0
    seen = set()
    for path, kind in walk_inputs(root):
        relative = path.relative_to(root).as_posix()
        if relative not in managed or kind not in {"IMAGE", "VIDEO"}:
            errors["UNMANAGED_INPUT"] += 1
        elif not _validate_managed(path, managed[relative]):
            errors["CATALOG_FILE_CHANGED"] += 1
        else:
            row = managed[relative]
            actual_folder = sort_folder_for(row["day"], row["width"], row["height"], "vid" if kind == "VIDEO" else "img")
            allowed = {actual_folder}
            if kind == "IMAGE":
                allowed.add(folder_for(row["day"], row["width"], row["height"]))
            if path.parent.relative_to(root) not in allowed:
                errors["CLASSIFICATION_MISMATCH"] += 1
            if kind == "VIDEO": videos += 1
            else: count += 1
        seen.add(relative)
    for rel in managed:
        if rel not in seen:
            errors["CATALOG_FILE_MISSING"] += 1
    # All app-generated image artifacts must pass the same parser, not just masters.
    state = root / state_name(root)
    artifacts = 0
    if state.exists():
        for path in state.rglob("*"):
            if is_link(path):
                errors["STATE_LINKED"] += 1
            elif path.is_file() and path.suffix.lower() == ".png":
                try:
                    png_audit(path.read_bytes())
                    artifacts += 1
                except (RiposteError, OSError):
                    errors["ARTIFACT_AUDIT_FAILED"] += 1
    return {"checkpoint": "COMPLETE" if not errors else "INCOMPLETE", "verified_images": count,
            "verified_videos": videos, "video_policy": "SORT_ONLY_BYTES_UNCHANGED",
            "verified_artifacts": artifacts, "blockers": dict(errors), "metadata_policy": "DATE_ONLY_IMAGES",
            "ai_protection": "NOT_ESTABLISHED_BY_METADATA_AUDIT"}
