from __future__ import annotations
import datetime as dt
import os
import re
from dataclasses import dataclass
from pathlib import Path
from .errors import RiposteError

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December")
YEARS = ("2026", "2025", "2024")
BINS = ("SML", "MED", "LRG", "XTL")
FORMAT_NAMES = frozenset({"PNG", "JPEG", "WEBP", "BMP", "TIFF", "GIF"})
IMAGE_SUFFIXES = frozenset({".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".avif", ".heic", ".heif", ".psd", ".svg", ".jxl", ".exr"})
SIDECAR_SUFFIXES = frozenset({".xmp", ".exif", ".iptc", ".aae"})
CACHE_NAMES = frozenset({".ds_store", "thumbs.db", "desktop.ini"})
CANONICAL = re.compile(r"^(202[456]|EVERYTHING_ELSE)/(" + "|".join(MONTHS) + r")/(?:img/)?(SML|MED|LRG|XTL)/(SML|MED|LRG|XTL)([0-9]{2,})\.png$")

@dataclass(frozen=True)
class Policy:
    date_mode: str = "download"
    max_pixels: int = 60_000_000
    max_file_bytes: int = 512 * 1024 * 1024
    discard_sidecars: bool = False
    def __post_init__(self):
        if self.date_mode not in {"download", "modified", "embedded"}:
            raise RiposteError("DATE_POLICY_INVALID")
        if self.max_pixels < 1 or self.max_file_bytes < 1:
            raise RiposteError("RESOURCE_LIMIT_INVALID")

def size_bin(width: int, height: int) -> str:
    """Fixed, pixel-area bins; neither file size nor an aesthetic quality claim."""
    n = width * height
    if min(width, height) < 1:
        raise RiposteError("INVALID_DIMENSIONS")
    return "SML" if n < 1_000_000 else "MED" if n < 4_000_000 else "LRG" if n < 16_000_000 else "XTL"

def valid_day(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value):
        raise RiposteError("DATE_INVALID")
    try:
        return dt.date.fromisoformat(value).isoformat()
    except ValueError:
        raise RiposteError("DATE_INVALID") from None

def extract_day(image, stat, mode: str) -> tuple[str, str]:
    """Read only date values. No EXIF dictionary is serialized, logged, or hashed."""
    if mode == "embedded":
        candidates = []
        try:
            exif = image.getexif()
            for key in (36867, 306, 36868):
                candidates.append(exif.get(key))
            # Original dates are often in the Exif sub-IFD, not the root IFD.
            if 34665 in exif:
                sub = exif.get_ifd(34665)
                candidates.extend(sub.get(key) for key in (36867, 36868))
        except Exception:
            pass
        candidates.append(image.info.get("Creation Time"))
        for candidate in candidates:
            if isinstance(candidate, str):
                token = candidate[:10].replace(":", "-")
                try:
                    return valid_day(token), "embedded"
                except RiposteError:
                    pass
    birth = getattr(stat, "st_birthtime", None)
    # Python 3.11 Windows exposes creation time as ctime, not POSIX ctime.
    if birth is None and os.name == "nt":
        birth = stat.st_ctime
    stamp = birth if mode == "download" and birth is not None else stat.st_mtime
    source = "filesystem_creation" if mode == "download" and birth is not None else "filesystem_modified"
    try:
        # Local calendar date is retained; no timezone/offset is persisted.
        return dt.datetime.fromtimestamp(stamp).date().isoformat(), source
    except (ValueError, OverflowError, OSError):
        raise RiposteError("DATE_UNREADABLE") from None

def folder_for(day: str, width: int, height: int) -> Path:
    date = dt.date.fromisoformat(valid_day(day))
    year = str(date.year) if str(date.year) in YEARS else "EVERYTHING_ELSE"
    return Path(year) / MONTHS[date.month - 1] / size_bin(width, height)


def sort_folder_for(day: str, width: int, height: int, media: str = "img") -> Path:
    """Media layers apply to sorting; existing publishing routes stay compatible."""
    if media not in {"img", "vid"}:
        raise RiposteError("MEDIA_KIND_INVALID")
    folder = folder_for(day, width, height)
    return folder.parent / media / folder.name

def is_link(path: Path) -> bool:
    try:
        s = path.lstat()
        return path.is_symlink() or bool(getattr(s, "st_file_attributes", 0) & 0x400)
    except OSError:
        return True

def same_file_state(a, b) -> bool:
    return (a.st_dev, a.st_ino, a.st_size, a.st_mtime_ns, a.st_ctime_ns) == (b.st_dev, b.st_ino, b.st_size, b.st_mtime_ns, b.st_ctime_ns)

def canonical_path(value: str) -> str:
    match = CANONICAL.fullmatch(value)
    if not match or match.group(3) != match.group(4):
        raise RiposteError("CATALOG_PATH_INVALID")
    return value
