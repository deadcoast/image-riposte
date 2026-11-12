"""Local publication fidelity gates; never aesthetic or AI-efficacy certificates."""
from __future__ import annotations
from dataclasses import asdict, dataclass
import math
import numpy as np
from PIL import Image
from .errors import RiposteError
from .metrics import fidelity
from .spatial import ArtistMask, budget_identity

@dataclass(frozen=True)
class QualityLimits:
    epsilon_255: int = 4
    preserve_white: bool = True
    rms_fraction: float = .95
    delta_e76_p95: float = 6.0
    tile_size: int = 32

    def __post_init__(self):
        if (type(self.epsilon_255) is not int or not 1 <= self.epsilon_255 <= 16
            or type(self.preserve_white) is not bool or type(self.tile_size) is not int
            or not 8 <= self.tile_size <= 128
            or not math.isfinite(self.rms_fraction) or not .1 <= self.rms_fraction <= 1
            or not math.isfinite(self.delta_e76_p95) or not .1 <= self.delta_e76_p95 <= 40):
            raise RiposteError("QUALITY_LIMITS_INVALID")

    def public(self):
        return asdict(self)

def spatial_budget(image: Image.Image, limits: QualityLimits, artist_mask: ArtistMask | None = None) -> np.ndarray:
    """Integer per-pixel channel cap. Smooth white: zero; hard edges: half."""
    x = np.asarray(image.convert("RGB"), dtype=np.float32) / 255
    luma = x.mean(axis=2)
    p = np.pad(luma, 1, mode="edge")
    local = sum(p[y:y + luma.shape[0], z:z + luma.shape[1]]
                for y in range(3) for z in range(3)) / 9
    detail = np.abs(luma - local)
    caps = np.where(detail > .08, limits.epsilon_255 // 2, limits.epsilon_255)
    if limits.preserve_white:
        caps = np.where((x.min(axis=2) > .97) & (detail < .005), 0, caps)
    if artist_mask is not None:
        caps = caps * artist_mask.raster(image.size).astype(np.uint16) // 255
    return caps.astype(np.uint8)

def _lab(rgb):
    c = rgb.astype(np.float64) / 255
    linear = np.where(c <= .04045, c / 12.92, ((c + .055) / 1.055) ** 2.4)
    xyz = linear @ np.array([[.4124564, .2126729, .0193339],
                            [.3575761, .7151522, .1191920],
                            [.1804375, .0721750, .9503041]]) / [.95047, 1., 1.08883]
    d = 6 / 29
    f = np.where(xyz > d**3, np.cbrt(xyz), xyz / (3 * d**2) + 4 / 29)
    return np.stack((116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
                     200 * (f[..., 1] - f[..., 2])), axis=-1)

def quality_report(clean, candidate, limits: QualityLimits = QualityLimits(), artist_mask: ArtistMask | None = None) -> dict:
    if clean.size != candidate.size:
        raise RiposteError("IMAGE_SIZE_MISMATCH")
    a, b = [np.asarray(im.convert("RGB"), dtype=np.int16) for im in (clean, candidate)]
    delta = np.abs(a - b)
    caps = spatial_budget(clean, limits, artist_mask)
    violations = int(np.any(delta > caps[..., None], axis=-1).sum())
    white_changed = int(np.any(delta[caps == 0] != 0, axis=-1).sum())
    square = delta.astype(np.float64) ** 2
    worst = max(float(np.sqrt(square[y:y + limits.tile_size, x:x + limits.tile_size].mean()))
                for y in range(0, a.shape[0], limits.tile_size)
                for x in range(0, a.shape[1], limits.tile_size))
    colour_p95 = float(np.percentile(np.linalg.norm(_lab(a) - _lab(b), axis=-1), 95))
    blocked = []
    if violations: blocked.append("SPATIAL_PIXEL_BUDGET_EXCEEDED")
    if worst > limits.epsilon_255 * limits.rms_fraction + 1e-8: blocked.append("LOCAL_RMS_LIMIT_EXCEEDED")
    if colour_p95 > limits.delta_e76_p95 + 1e-8: blocked.append("COLOUR_DIFFERENCE_LIMIT_EXCEEDED")
    return {"status": "PASS" if not blocked else "BLOCKED", "policy": limits.public(),
            **({"spatial_budget": budget_identity(caps, artist_mask)} if artist_mask else {}),
            "blockers": blocked, **fidelity(clean, candidate),
            "worst_tile_rmse_255": round(worst, 6), "delta_e76_p95": round(colour_p95, 6),
            "budget_violating_pixels": violations, "protected_pixels_changed": white_changed,
            "visual_approval": "REQUIRED", "ai_protection": "UNVERIFIED",
            "scope": "NUMERIC_FIDELITY_ONLY; Delta E 1976, not CIEDE2000 or an imperceptibility certificate."}
