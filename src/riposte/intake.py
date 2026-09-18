"""Source-preserving file/folder intake for standalone protection.

Paths and source stat identities are transient. Only reconstructed date-only PNGs
and clean image identities may enter a saved publication request.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import os
import uuid

from PIL import Image, UnidentifiedImageError

from .errors import RiposteError
from .policy import Policy, IMAGE_SUFFIXES, SIDECAR_SUFFIXES, CACHE_NAMES, is_link, same_file_state
from .sanitize import decode_clean, encode_clean, png_audit


def _safe_input(path: Path) -> Path:
    path = path.expanduser().absolute()
    try:
        path.lstat()
    except FileNotFoundError:
        raise RiposteError("INPUT_NOT_FOUND") from None
    except OSError:
        raise RiposteError("INPUT_UNREADABLE") from None
    if any(is_link(part) for part in (path, *path.parents)):
        raise RiposteError("INPUT_LINK_REQUIRES_REVIEW")
    if any(part.name in {".riposte", ".shroud"} for part in (path, *path.parents)):
        raise RiposteError("INPUT_APPLICATION_STATE_REJECTED")
    if not path.is_file() and not path.is_dir():
        raise RiposteError("INPUT_NOT_FOUND")
    return Path(os.path.abspath(path))


def input_files(paths: list[Path]) -> tuple[list[Path], int]:
    """Expand folders deterministically, deduplicate overlaps, never follow links."""
    files: list[Path] = []
    seen: set[Path] = set()
    visited: set[Path] = set()
    ignored = 0

    def add(path: Path, explicit: bool = False) -> None:
        nonlocal ignored
        path = _safe_input(path)
        if path in seen:
            return
        seen.add(path)
        if not explicit and (path.suffix.lower() in SIDECAR_SUFFIXES or path.name.lower() in CACHE_NAMES):
            ignored += 1
            return
        try:
            with Image.open(path):
                pass
        except (UnidentifiedImageError, OSError, ValueError):
            if explicit or path.suffix.lower() in IMAGE_SUFFIXES:
                raise RiposteError("INPUT_DECODE_FAILED") from None
            ignored += 1
            return
        files.append(path)
        if len(files) > 200:
            raise RiposteError("PUBLICATION_SELECTION_INVALID")

    def walk_error(error: OSError) -> None:
        raise RiposteError("INPUT_UNREADABLE") from None

    for supplied in paths:
        path = _safe_input(Path(supplied))
        if path.is_file():
            add(path, explicit=True)
            continue
        for directory, dirs, names in os.walk(path, followlinks=False, onerror=walk_error):
            current = _safe_input(Path(directory))
            if current in visited:
                dirs.clear()
                continue
            visited.add(current)
            dirs[:] = sorted(name for name in dirs if name not in {".riposte", ".shroud"})
            for name in dirs:
                _safe_input(current / name)
            for name in sorted(names):
                add(current / name)
    if not files:
        raise RiposteError("NO_INPUT_IMAGES")
    return files, ignored


@dataclass
class InputSource:
    path: Path
    row: dict
    source_stat: os.stat_result

    def snapshot(self, policy: Policy) -> bytes:
        clean = decode_clean(_safe_input(self.path), policy)
        try:
            data = encode_clean(clean.pixels, clean.day)
            if (not same_file_state(self.source_stat, clean.source_stat)
                    or png_audit(data)["sha256"] != self.row["sha256"]):
                raise RiposteError("INPUT_CHANGED_REPLAN")
            return data
        finally:
            clean.pixels.close()


def inspect_inputs(paths: list[Path], policy: Policy = Policy(), progress=None) -> tuple[list[InputSource], int]:
    files, ignored = input_files(paths)
    sources = []
    for index, path in enumerate(files):
        if progress:
            progress({"phase": "Inspecting selected images", "processed": index, "total": len(files)})
        clean = decode_clean(path, policy)
        try:
            data = encode_clean(clean.pixels, clean.day)
            audit = png_audit(data)
            row = {"id": uuid.uuid4().hex, "day": clean.day, "width": audit["width"],
                   "height": audit["height"], "sha256": audit["sha256"]}
            sources.append(InputSource(path, row, clean.source_stat))
        finally:
            clean.pixels.close()
    return sources, ignored
