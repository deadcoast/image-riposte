"""Read-only still-image normalization and bounded local video sampling."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import time

from PIL import Image

from .duplicate_features import Visual, describe
from .errors import RiposteError
from .policy import Policy
from .records import Progress
from .sanitize import decode_clean


@dataclass(frozen=True)
class Signature:
    width: int
    height: int
    pixel_sha256: str | None
    frames: tuple[Visual, ...]
    duration: float | None = None


def normalized_image(path: Path, max_pixels: int = 60_000_000) -> Image.Image:
    clean = decode_clean(path, Policy(max_pixels=max_pixels, max_file_bytes=4 * 1024**3))
    try:
        return clean.pixels.convert('RGBA')
    finally:
        clean.pixels.close()


def image_signature(path: Path, *, max_pixels: int = 60_000_000) -> Signature:
    with normalized_image(path, max_pixels) as image:
        digest = hashlib.sha256(f'{image.width}:{image.height}:RGBA:'.encode() + image.tobytes()).hexdigest()
        return Signature(image.width, image.height, digest, (describe(image),))


def equal_pixels(left: Path, right: Path, *, max_pixels: int = 60_000_000) -> bool:
    with normalized_image(left, max_pixels) as a, normalized_image(right, max_pixels) as b:
        if a.size != b.size:
            return False
        # Compare bounded raster strips instead of retaining two full byte copies.
        for y in range(0, a.height, 128):
            box = (0, y, a.width, min(a.height, y + 128))
            with a.crop(box) as left_strip, b.crop(box) as right_strip:
                if left_strip.tobytes() != right_strip.tobytes():
                    return False
    return True


def local_process(args: list[str], *, limit: int, progress: Progress | None = None) -> bytes:
    process = subprocess.Popen(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                               stderr=subprocess.DEVNULL,
                               creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    deadline = time.monotonic() + 20
    try:
        while True:
            if progress:
                progress({'phase': 'Sampling video frames'})
            try:
                output, _ = process.communicate(timeout=.2)
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() >= deadline:
                    raise RiposteError('DUPLICATE_VIDEO_TIMEOUT') from None
        if process.returncode or len(output) > limit:
            raise RiposteError('DUPLICATE_VIDEO_UNREADABLE')
        return output
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate()


def video_probe(path: Path, progress: Progress | None = None) -> tuple[int, int, float]:
    probe = shutil.which('ffprobe')
    if not probe or not shutil.which('ffmpeg'):
        raise RiposteError('DUPLICATE_VIDEO_TOOLS_UNAVAILABLE')
    output = local_process([probe, '-v', 'error', '-protocol_whitelist', 'file,pipe', '-select_streams', 'v:0',
                            '-show_entries', 'stream=width,height,duration:format=duration', '-of', 'json', str(path)],
                           limit=65_536, progress=progress)
    try:
        data = json.loads(output)
        stream = data['streams'][0]
        width, height = int(stream['width']), int(stream['height'])
        duration = float(data.get('format', {}).get('duration', stream.get('duration', 0)))
        if min(width, height) < 1 or width * height > 60_000_000 or not math.isfinite(duration) or not 0 < duration <= 7 * 86400:
            raise ValueError()
        return width, height, duration
    except (ValueError, TypeError, KeyError, IndexError):
        raise RiposteError('DUPLICATE_VIDEO_UNREADABLE') from None


def video_frame(path: Path, timestamp: float, *, edge: int = 64, progress: Progress | None = None) -> Image.Image:
    executable = shutil.which('ffmpeg')
    if not executable:
        raise RiposteError('DUPLICATE_VIDEO_TOOLS_UNAVAILABLE')
    data = local_process([executable, '-nostdin', '-v', 'error', '-threads', '1', '-protocol_whitelist', 'file,pipe',
                          '-ss', f'{timestamp:.6f}', '-i', str(path), '-map', '0:v:0', '-frames:v', '1',
                          '-an', '-sn', '-vf', f'scale={edge}:{edge}', '-pix_fmt', 'rgba', '-f', 'rawvideo', 'pipe:1'],
                         limit=edge * edge * 4, progress=progress)
    if len(data) != edge * edge * 4:
        raise RiposteError('DUPLICATE_VIDEO_FRAME_UNAVAILABLE')
    return Image.frombytes('RGBA', (edge, edge), data)


def video_signature(path: Path, *, progress: Progress | None = None) -> Signature:
    width, height, duration = video_probe(path, progress)
    frames = []
    for fraction in (.1, .3, .5, .7, .9):
        timestamp = duration * fraction
        sampled, timestamp = sampled_frame(path, timestamp, progress=progress)
        with sampled as image:
            visual = describe(image, crops=False, timestamp=round(timestamp, 6))
        # Sampling resizes to a square, but comparisons retain stream geometry.
        from dataclasses import replace
        views = tuple(replace(view, aspect=width / height if view.rotation % 2 == 0 else height / width) for view in visual.views)
        frames.append(Visual(visual.pixels, width, height, views, visual.timestamp))
    return Signature(width, height, None, tuple(frames), duration)


def sampled_frame(path: Path, timestamp: float, *, edge: int = 64,
                  progress: Progress | None = None) -> tuple[Image.Image, float]:
    # A container's duration includes the display interval of its last frame.
    # Seeking inside that interval may yield EOF, especially for low-FPS clips.
    # Retry earlier bounded positions and retain the actual requested seek time.
    for seek in dict.fromkeys(max(0., timestamp - delta) for delta in (0., .25, .5, 1., 2., 5., timestamp)):
        try:
            return video_frame(path, seek, edge=edge, progress=progress), seek
        except RiposteError as exc:
            if exc.code != 'DUPLICATE_VIDEO_FRAME_UNAVAILABLE': raise
    raise RiposteError('DUPLICATE_VIDEO_FRAME_UNAVAILABLE')


def thumbnail(path: Path, *, media: str, timestamp: float | None = None) -> bytes:
    if media == 'video':
        width, height, duration = video_probe(path)
        sampled, _ = sampled_frame(path, min(duration * .9, max(0, timestamp if timestamp is not None else duration * .5)), edge=384)
        with sampled as square:
            aspect = width / height
            image = square.resize((384, max(1, round(384 / aspect))) if aspect >= 1 else (max(1, round(384 * aspect)), 384))
    elif media == 'image':
        image = normalized_image(path)
        image.thumbnail((768, 768), Image.Resampling.LANCZOS)
    else:
        raise RiposteError('DUPLICATE_PREVIEW_UNAVAILABLE')
    with image:
        # Fresh encoded pixels only: no source metadata or executable formats.
        with Image.new('RGBA', image.size) as clean:
            clean.paste(image)
            output = io.BytesIO()
            clean.save(output, format='PNG')
            return output.getvalue()
