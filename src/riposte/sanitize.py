"""Decode → apply orientation/color → fresh pixels → date-only PNG.

No source bytes, input path strings, thumbnails, profiles, or metadata objects
are copied into output records. This is NOT pixel-steganography detection.
"""
from __future__ import annotations
import binascii
import datetime as dt
import hashlib
import io
import struct
import warnings
import zlib
from dataclasses import dataclass
from pathlib import Path
import numpy as np
from PIL import Image, ImageCms, ImageOps, PngImagePlugin
from .errors import RiposteError
from .policy import Policy, FORMAT_NAMES, extract_day, valid_day, same_file_state

@dataclass
class CleanImage:
    pixels: Image.Image
    day: str
    date_source: str
    source_format: str
    source_stat: object

# Structural bytes, not personal metadata. Reject all ancillary chunks except date.
PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

def png_audit(data: bytes) -> dict:
    if not data.startswith(PNG_MAGIC):
        raise RiposteError("NOT_CANONICAL_PNG")
    pos, kinds, day, idat_count = 8, [], None, 0
    compressed = []
    expected = None
    while pos < len(data):
        if pos + 12 > len(data):
            raise RiposteError("PNG_TRUNCATED")
        length = struct.unpack(">I", data[pos:pos+4])[0]
        end = pos + 12 + length
        if end > len(data):
            raise RiposteError("PNG_TRUNCATED")
        kind, payload = data[pos+4:pos+8], data[pos+8:end-4]
        crc = struct.unpack(">I", data[end-4:end])[0]
        if binascii.crc32(kind + payload) & 0xffffffff != crc:
            raise RiposteError("PNG_CRC_INVALID")
        if kind not in {b"IHDR", b"IDAT", b"IEND", b"tEXt"}:
            raise RiposteError("PNG_METADATA_REJECTED")
        if kind == b"IHDR":
            if kinds or length != 13 or payload[8] != 8 or payload[9] not in (2, 6):
                raise RiposteError("PNG_HEADER_INVALID")
            width, height = struct.unpack(">II", payload[:8])
            if min(width, height) < 1 or width * height > 60_000_000 or payload[10:] != b"\x00\x00\x00":
                raise RiposteError("PNG_HEADER_INVALID")
            expected = (width * (3 if payload[9] == 2 else 4) + 1) * height
        elif not kinds:
            raise RiposteError("PNG_HEADER_INVALID")
        if kind == b"tEXt":
            if day is not None or not payload.startswith(b"Creation Time\x00"):
                raise RiposteError("PNG_METADATA_REJECTED")
            try:
                day = valid_day(payload.split(b"\x00", 1)[1].decode("ascii"))
            except (UnicodeError, RiposteError):
                raise RiposteError("PNG_DATE_INVALID") from None
        if kind == b"IDAT":
            idat_count += 1
            compressed.append(payload)
        kinds.append(kind.decode("ascii"))
        pos = end
        if kind == b"IEND":
            if length or pos != len(data):
                raise RiposteError("PNG_TRAILING_DATA")
            break
    if not kinds or kinds[-1] != "IEND" or idat_count == 0 or day is None:
        raise RiposteError("PNG_INCOMPLETE")
    try:
        decoder = zlib.decompressobj()
        raster = decoder.decompress(b"".join(compressed), expected + 1)
        if len(raster) != expected or not decoder.eof or decoder.unused_data or decoder.unconsumed_tail:
            raise RiposteError("PNG_HIDDEN_COMPRESSED_DATA")
        del raster, compressed
        with Image.open(io.BytesIO(data)) as check:
            check.load()
            if set(check.info) != {"Creation Time"} or check.getexif():
                raise RiposteError("PNG_METADATA_REJECTED")
            if check.mode == "RGBA":
                a = np.asarray(check)
                if np.any(a[..., :3][a[..., 3] == 0]):
                    raise RiposteError("HIDDEN_ALPHA_RGB")
            width, height = check.size
    except RiposteError:
        raise
    except Exception:
        raise RiposteError("PNG_DECODE_FAILED") from None
    return {"date": day, "width": width, "height": height,
            "chunks": sorted(set(kinds)), "metadata": "DATE_ONLY",
            "sha256": hashlib.sha256(data).hexdigest()}

def fresh_pixels(image: Image.Image) -> Image.Image:
    mode = "RGBA" if "A" in image.getbands() or "transparency" in image.info else "RGB"
    converted = image.convert(mode)
    arr = np.array(converted, dtype=np.uint8, copy=True)
    if mode == "RGBA":
        arr[..., :3][arr[..., 3] == 0] = 0
    return Image.fromarray(arr)

def decode_clean(path: Path, policy: Policy = Policy()) -> CleanImage:
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with path.open("rb") as stream:
                import os
                before = os.fstat(stream.fileno())
                if before.st_nlink > 1:
                    raise RiposteError("HARDLINK_REQUIRES_REVIEW")
                if before.st_size > policy.max_file_bytes:
                    raise RiposteError("FILE_LIMIT")
                prefix = stream.read(32)
                stream.seek(0)
                if prefix.startswith(PNG_MAGIC) and len(prefix) > 24 and prefix[24] > 8:
                    raise RiposteError("HIGH_BIT_DEPTH_REQUIRES_REVIEW")
                with Image.open(stream) as source:
                    if source.format not in FORMAT_NAMES:
                        raise RiposteError("FORMAT_REQUIRES_REVIEW")
                    if source.width * source.height > policy.max_pixels:
                        raise RiposteError("PIXEL_LIMIT")
                    if getattr(source, "n_frames", 1) != 1:
                        raise RiposteError("MULTIFRAME_REQUIRES_REVIEW")
                    if source.mode in {"I", "F", "I;16", "I;16B", "I;16L"}:
                        raise RiposteError("HIGH_BIT_DEPTH_REQUIRES_REVIEW")
                    if source.format == "TIFF":
                        bits = source.tag_v2.get(258, (8,))
                        bits = (bits,) if isinstance(bits, int) else bits
                        if max(bits) > 8:
                            raise RiposteError("HIGH_BIT_DEPTH_REQUIRES_REVIEW")
                    day, date_source = extract_day(source, before, policy.date_mode)
                    fmt = source.format
                    source.load()
                    oriented = ImageOps.exif_transpose(source)
                    profile = source.info.get("icc_profile")
                    if profile:
                        try:
                            icc = ImageCms.ImageCmsProfile(io.BytesIO(profile))
                            alpha = oriented.convert("RGBA").getchannel("A") if "A" in oriented.getbands() or "transparency" in oriented.info else None
                            mode = "CMYK" if oriented.mode == "CMYK" else "LAB" if oriented.mode == "LAB" else "RGB"
                            oriented = ImageCms.profileToProfile(oriented.convert(mode), icc,
                                ImageCms.createProfile("sRGB"), outputMode="RGB")
                            if alpha is not None:
                                oriented.putalpha(alpha)
                        except Exception:
                            raise RiposteError("COLOR_PROFILE_REQUIRES_REVIEW") from None
                    elif oriented.mode in {"CMYK", "LAB"}:
                        raise RiposteError("UNTAGGED_COLOR_REQUIRES_REVIEW")
                    pixels = fresh_pixels(oriented)
                after = os.fstat(stream.fileno())
                if not same_file_state(before, after):
                    raise RiposteError("SOURCE_CHANGED")
        return CleanImage(pixels, day, date_source, fmt, after)
    except RiposteError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise RiposteError("PIXEL_LIMIT") from None
    except Exception:
        raise RiposteError("DECODE_FAILED") from None

def encode_clean(image: Image.Image, day: str) -> bytes:
    day = valid_day(day)
    out = io.BytesIO()
    info = PngImagePlugin.PngInfo()
    info.add_text("Creation Time", day)
    clean = fresh_pixels(image)
    clean.save(out, format="PNG", pnginfo=info, optimize=False, compress_level=6)
    data = out.getvalue()
    result = png_audit(data)
    if (result["width"], result["height"]) != clean.size:
        raise RiposteError("ENCODE_MISMATCH")
    return data

def timestamp_day(path: Path, day: str) -> None:
    import os
    # Noon avoids several midnight daylight-saving transitions; date is primary.
    stamp = dt.datetime.combine(dt.date.fromisoformat(day), dt.time(12)).timestamp()
    os.utime(path, (stamp, stamp))

def social_render(image: Image.Image, max_edge: int = 1536) -> Image.Image:
    if not 64 <= max_edge <= 4096:
        raise RiposteError("PUBLISH_SIZE_INVALID")
    if image.mode == "RGBA":
        base = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(base, image).convert("RGB")
    else:
        image = image.convert("RGB")
    image.thumbnail((max_edge, max_edge), Image.Resampling.LANCZOS)
    return fresh_pixels(image)
