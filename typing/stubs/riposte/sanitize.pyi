# Source-derived external stub; see typing/README.md for scope.
from pathlib import Path
from _riposte_types import PngAudit
import os
from .errors import RiposteError as RiposteError
from .policy import FORMAT_NAMES as FORMAT_NAMES, Policy as Policy, extract_day as extract_day, same_file_state as same_file_state, valid_day as valid_day
from PIL import Image
from dataclasses import dataclass

@dataclass
class CleanImage:
    pixels: Image.Image
    day: str
    date_source: str
    source_format: str
    source_stat: os.stat_result
PNG_MAGIC: bytes

def png_audit(data: bytes) -> PngAudit: ...

def fresh_pixels(image: Image.Image) -> Image.Image: ...

def decode_clean(path: Path, policy: Policy=...) -> CleanImage: ...

def encode_clean(image: Image.Image, day: str) -> bytes: ...

def timestamp_day(path: Path, day: str) -> None: ...

def social_render(image: Image.Image, max_edge: int=1536) -> Image.Image: ...
