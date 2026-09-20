from __future__ import annotations
import datetime as dt
import os
import re
import unicodedata
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
FLOAT_DIRECTORIES = frozenset({"_float_", "__float__"})
CANONICAL = re.compile(r"^(202[456]|EVERYTHING_ELSE)/(" + "|".join(MONTHS) + r")/(?:img/(?:(?P<category>[^/]+)/)?)?(SML|MED|LRG|XTL)/(SML|MED|LRG|XTL)([0-9]{2,})\.png$")

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

def sort_excluded(directory: Path) -> bool:
    """Reserved user directories and their descendants are outside sorting.

    Pass a directory (a file's parent for catalog records). Protection intake
    deliberately does not use this policy. Match exact names, ignoring case.
    """
    return any(part.casefold() in FLOAT_DIRECTORIES for part in directory.parts)


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


def category_slug(value: str) -> str:
    reserved = {"con", "prn", "aux", "nul"} | {f"{p}{n}" for p in ("com", "lpt") for n in range(1, 10)}
    if (not isinstance(value, str) or not 1 <= len(value) <= 80 or value in reserved
            or value != unicodedata.normalize("NFKC", unicodedata.normalize("NFKC", value).casefold())
            or any(not part or unicodedata.category(part[0])[0] not in "LN"
                   or any(unicodedata.category(c)[0] not in "LNM" for c in part) for part in value.split("-"))):
        raise RiposteError("CATEGORY_SLUG_INVALID")
    return value


def path_category(relative: str) -> str | None:
    parts = relative.split("/")
    return category_slug(parts[3]) if len(parts) == 6 and parts[2] in {"img", "vid"} else None


def sort_folder_for(day: str, width: int, height: int, media: str = "img", category: str | None = None) -> Path:
    """Media layers apply to sorting; existing publishing routes stay compatible."""
    if media not in {"img", "vid"}:
        raise RiposteError("MEDIA_KIND_INVALID")
    folder = folder_for(day, width, height)
    base = folder.parent / media
    return base / category_slug(category) / folder.name if category is not None else base / folder.name

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
    if not match or match.group(4) != match.group(5):
        raise RiposteError("CATALOG_PATH_INVALID")
    if match.group("category") is not None:
        category_slug(match.group("category"))
    return value
