from __future__ import annotations
import collections
import os
from pathlib import Path
from typing import Callable
from PIL import Image, UnidentifiedImageError
from .errors import RiposteError
from .policy import Policy, IMAGE_SUFFIXES, SIDECAR_SUFFIXES, CACHE_NAMES, folder_for, is_link, same_file_state
from .sanitize import decode_clean, encode_clean, png_audit
from .store import check_root, workspace_lock, catalog, record_image, atomic_clean_write, write_report, safe_child, state_name

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
    return {row["relative"]: row for row in catalog(root)}

def _validate_managed(path: Path, row: dict) -> bool:
    try:
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
        if kind != "IMAGE":
            if kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars:
                counts["sidecars_to_discard"] += 1
            else:
                errors[kind] += 1
            continue
        rel = path.relative_to(root).as_posix()
        if rel in managed:
            if _validate_managed(path, managed[rel]):
                counts["already_clean"] += 1
            else:
                errors["CATALOG_FILE_CHANGED"] += 1
            continue
        try:
            clean = decode_clean(path, policy)
            folder = folder_for(clean.day, *clean.pixels.size).as_posix()
            folders[folder] += 1
            counts["images_to_migrate"] += 1
            counts["input_bytes"] += path.stat().st_size
        except RiposteError as exc:
            errors[exc.code] += 1
    for missing in set(managed) - seen:
        errors["CATALOG_FILE_MISSING"] += 1
    return {"mode": "READ_ONLY", "counts": dict(counts), "destinations": dict(sorted(folders.items())),
            "blockers": dict(errors), "ready": not bool(errors),
            "source_policy": "Verified image sources are unlinked on apply; no raw backups."}

def _next_relative(root: Path, folder: Path) -> str:
    dest = safe_child(root, folder.as_posix())
    code = folder.name
    used = []
    if dest.exists():
        for entry in dest.iterdir():
            stem = entry.stem
            if stem.startswith(code) and stem[len(code):].isdigit():
                used.append(int(stem[len(code):]))
    number = max(used, default=0) + 1
    return (folder / f"{code}{number:02d}.png").as_posix()

def organize(root: Path, policy: Policy = Policy(), progress: Progress | None = None) -> dict:
    """Verified commit before source unlink. No silent deletion of undecodable data."""
    root = check_root(root)
    counts, errors = collections.Counter(), collections.Counter()
    with workspace_lock(root):
        managed = known_good(root)
        # Snapshot only path references in RAM, not raw file bytes or raw metadata.
        inputs = list(walk_inputs(root))
        for index, (path, kind) in enumerate(inputs, 1):
            if progress:
                progress({"phase": "Cleansing / organizing", "processed": index, "total": len(inputs)})
            try:
                if kind != "IMAGE":
                    if kind == "SIDECAR_REQUIRES_DISCARD" and policy.discard_sidecars:
                        if path.stat().st_nlink > 1:
                            raise RiposteError("HARDLINK_REQUIRES_REVIEW")
                        path.unlink()
                        counts["sidecars_discarded"] += 1
                    else:
                        errors[kind] += 1
                    continue
                rel = path.relative_to(root).as_posix()
                if rel in managed:
                    if _validate_managed(path, managed[rel]):
                        counts["already_clean"] += 1
                    else:
                        errors["CATALOG_FILE_CHANGED"] += 1
                    continue
                clean = decode_clean(path, policy)
                data = encode_clean(clean.pixels, clean.day)
                result = png_audit(data)
                folder = folder_for(clean.day, clean.pixels.width, clean.pixels.height)
                relative = _next_relative(root, folder)
                atomic_clean_write(root, relative, data)
                # No metadata-bearing source path or source hash goes into this row.
                row = record_image(root, relative, result, len(data), clean.date_source)
                managed[relative] = row
                if is_link(path) or not same_file_state(clean.source_stat, path.stat()):
                    raise RiposteError("SOURCE_CHANGED_OUTPUT_RETAINED")
                path.unlink()  # Deliberately does not send contaminated originals to Trash.
                counts["migrated"] += 1
            except RiposteError as exc:
                errors[exc.code] += 1
            except Exception:
                errors["IO_OPERATION_FAILED"] += 1
        # Only truly empty old folders; files of unknown purpose are never discarded.
        for directory, _, _ in os.walk(root, topdown=False, followlinks=False):
            path = Path(directory)
            if path != root and state_name(root) not in path.relative_to(root).parts and not is_link(path):
                try:
                    path.rmdir()
                except OSError:
                    pass
        # Rescan so concurrent additions / residual originals cannot be called clean.
        remaining = 0
        seen = set()
        for path, kind in walk_inputs(root):
            relative = path.relative_to(root).as_posix()
            seen.add(relative)
            if kind != "IMAGE" or relative not in managed or not _validate_managed(path, managed[relative]):
                remaining += 1
        for missing in set(managed) - seen:
            errors["CATALOG_FILE_MISSING"] += 1
        report = {"mode": "APPLY", "counts": dict(counts), "blockers": dict(errors),
                  "unmanaged_or_changed_remaining": remaining,
                  "checkpoint": "COMPLETE" if not errors and not remaining else "INCOMPLETE",
                  "metadata_policy": "DATE_ONLY", "source_backups": "NONE"}
        write_report(root, "last-run.json", report)
        return report

def audit_workspace(root: Path) -> dict:
    root = check_root(root)
    managed = known_good(root)
    errors = collections.Counter()
    count = 0
    seen = set()
    for path, kind in walk_inputs(root):
        relative = path.relative_to(root).as_posix()
        if relative not in managed or kind != "IMAGE":
            errors["UNMANAGED_INPUT"] += 1
        elif not _validate_managed(path, managed[relative]):
            errors["CATALOG_FILE_CHANGED"] += 1
        else:
            row = managed[relative]
            actual_folder = folder_for(row["day"], row["width"], row["height"]).as_posix()
            if path.parent.relative_to(root).as_posix() != actual_folder:
                errors["CLASSIFICATION_MISMATCH"] += 1
            count += 1
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
            "verified_artifacts": artifacts, "blockers": dict(errors), "metadata_policy": "DATE_ONLY",
            "ai_protection": "NOT_ESTABLISHED_BY_METADATA_AUDIT"}
