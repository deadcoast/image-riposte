"""Local visual evidence. Scores are heuristics, never duplicate probabilities."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from PIL import Image

_DCT = np.cos(np.pi * (np.arange(32)[None, :] + .5) * np.arange(8)[:, None] / 32)


@dataclass(frozen=True)
class View:
    name: str
    rotation: int
    mirror: bool
    box: tuple[int, int, int, int]
    phash: int
    coverage: float
    aspect: float


@dataclass(frozen=True)
class Visual:
    pixels: NDArray[np.uint8]
    width: int
    height: int
    views: tuple[View, ...]
    timestamp: float | None = None


def luminance(pixels: NDArray[np.uint8]) -> NDArray[np.float64]:
    rgb = pixels[..., :3].astype(np.float64)
    if pixels.shape[2] == 4:
        alpha = pixels[..., 3:4].astype(np.float64) / 255
        rgb = rgb * alpha + 255 * (1 - alpha)
    return np.asarray(rgb @ np.array([.299, .587, .114]), dtype=np.float64)


def informative(pixels: NDArray[np.uint8]) -> bool:
    grey = luminance(pixels)
    edge = (float(np.abs(np.diff(grey, axis=0)).mean()) + float(np.abs(np.diff(grey, axis=1)).mean())) / 2
    counts = np.bincount((grey.astype(np.uint8) // 16).ravel(), minlength=16)
    p = counts[counts > 0] / grey.size
    entropy = float(-(p * np.log2(p)).sum())
    return float(grey.std()) >= 7.5 and edge >= 1.5 and entropy >= .65


def phash(pixels: NDArray[np.uint8]) -> int:
    grey = luminance(pixels)
    coefficients = (_DCT @ grey @ _DCT.T).ravel()[1:]
    median = float(np.median(coefficients))
    return sum(1 << i for i, value in enumerate(coefficients) if value > median)


def view_pixels(visual: Visual, view: View) -> NDArray[np.uint8]:
    pixels = np.rot90(visual.pixels, view.rotation)
    if view.mirror:
        pixels = np.fliplr(pixels)
    x0, y0, x1, y1 = view.box
    with Image.fromarray(pixels[y0:y1, x0:x1]) as image:
        return np.asarray(image.resize((32, 32), Image.Resampling.LANCZOS), dtype=np.uint8).copy()


def describe(image: Image.Image, *, crops: bool = True, timestamp: float | None = None) -> Visual:
    pixels = np.asarray(image.convert('RGBA').resize((64, 64), Image.Resampling.LANCZOS), dtype=np.uint8).copy()
    base = Visual(pixels, image.width, image.height, (), timestamp)
    candidates: list[View] = []
    for mirror in (False, True):
        for rotation in range(4):
            aspect = image.width / image.height if rotation % 2 == 0 else image.height / image.width
            name = ('mirror+' if mirror else '') + f'rotate-{rotation * 90}'
            candidates.append(View(name, rotation, mirror, (0, 0, 64, 64), 0, 1., aspect))
    if crops:
        for side in (48, 32):
            edge = 64 - side
            for x, y in ((0, 0), (edge, 0), (0, edge), (edge, edge), (edge // 2, edge // 2)):
                candidates.append(View(f'crop-{side}-{x}-{y}', 0, False, (x, y, x + side, y + side),
                                       0, side * side / 4096, image.width / image.height))
    views = []
    for view in candidates:
        sample = view_pixels(base, view)
        if informative(sample):
            views.append(View(view.name, view.rotation, view.mirror, view.box, phash(sample), view.coverage, view.aspect))
    return Visual(pixels, image.width, image.height, tuple(views), timestamp)


def structural(left: NDArray[np.float64], right: NDArray[np.float64]) -> float:
    """Mean 8x8 block SSIM on a 32x32 sample; explicitly not full-resolution SSIM."""
    a = left.reshape(4, 8, 4, 8).transpose(0, 2, 1, 3).reshape(16, 64)
    b = right.reshape(4, 8, 4, 8).transpose(0, 2, 1, 3).reshape(16, 64)
    ma, mb = a.mean(axis=1), b.mean(axis=1)
    va, vb = a.var(axis=1), b.var(axis=1)
    cov = ((a - ma[:, None]) * (b - mb[:, None])).mean(axis=1)
    values = ((2 * ma * mb + 6.5025) * (2 * cov + 58.5225)
              / ((ma * ma + mb * mb + 6.5025) * (va + vb + 58.5225)))
    return float(np.clip(values.mean(), 0, 1))


def compare_views(left: Visual, lv: View, right: Visual, rv: View) -> dict[str, object] | None:
    if lv.coverage < 1 and rv.coverage < 1:
        return None  # Shared tiny patches alone do not qualify a file relationship.
    distance = (lv.phash ^ rv.phash).bit_count()
    if distance > 12:
        return None
    a, b = view_pixels(left, lv), view_pixels(right, rv)
    if not informative(a) or not informative(b):
        return None
    grey_a, grey_b = luminance(a), luminance(b)
    ssim = structural(grey_a, grey_b)
    alpha = 1 - float(np.abs(a[..., 3].astype(float) - b[..., 3]).mean()) / 255
    # Compare visible colour on white, not hidden RGB under transparency.
    aa, ba = a[..., 3:4].astype(float) / 255, b[..., 3:4].astype(float) / 255
    rgb_a, rgb_b = a[..., :3] * aa + 255 * (1 - aa), b[..., :3] * ba + 255 * (1 - ba)
    colour = 1 - float(np.abs(rgb_a - rgb_b).mean()) / 255
    ga = np.concatenate([np.diff(grey_a, axis=0).ravel(), np.diff(grey_a, axis=1).ravel()])
    gb = np.concatenate([np.diff(grey_b, axis=0).ravel(), np.diff(grey_b, axis=1).ravel()])
    denominator = float(np.linalg.norm(ga) * np.linalg.norm(gb))
    gradient = max(0., float(ga @ gb) / denominator) if denominator else 0.
    geometry = abs(math.log(lv.aspect / rv.aspect))
    if ssim < .70 or colour < .78 or alpha < .94 or gradient < .65 or geometry > .12:
        return None
    full = lv.coverage == rv.coverage == 1
    strong = full and ssim >= .92 and colour >= .94 and alpha >= .985 and gradient >= .88 and distance <= 8 and geometry <= .03
    label: Literal["DUPLICATE", "MAYBE DUPLICATE", "CLOSELY RELATED"] = 'MAYBE DUPLICATE' if strong else 'CLOSELY RELATED'
    score = min(99., round(100 * (.5 * ssim + .25 * colour + .15 * gradient + .1 * (1 - distance / 63)), 1))
    return {'label': label, 'confidence': score, 'confidence_kind': 'HEURISTIC_NOT_PROBABILITY',
            'basis': 'FULL_FRAME_SIMILARITY' if full else 'CROP_OVERLAP',
            'metrics': {'structural_32px': round(ssim, 4), 'colour_agreement': round(colour, 4),
                        'alpha_agreement': round(alpha, 4), 'gradient_agreement': round(gradient, 4),
                        'phash_distance': distance, 'aspect_log_difference': round(geometry, 4),
                        'left_coverage': lv.coverage, 'right_coverage': rv.coverage},
            'left_view': lv.name, 'right_view': rv.name,
            'left_time': left.timestamp, 'right_time': right.timestamp}
