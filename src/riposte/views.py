"""Matched publication views and reproducible keep/edit masks.

Forward JPEG is the real Pillow 4:2:0 codec. Its optimization backward pass is
an explicitly approximate DCT/STE BPDA, not a derivative of JPEG bitstreams.
"""
from __future__ import annotations
import io
import math
import numpy as np
from PIL import Image, ImageFilter
from .errors import RiposteError

TRAIN_VIEWS = ("identity", "jpeg85", "resize75")
HOLDOUT_VIEWS = ("jpeg70", "jpeg60", "resize50-jpeg80", "offset-crop85", "blur06")
MASKS = ("whole", "center", "left", "right", "top", "bottom")


def publication_view(image: Image.Image, name: str) -> Image.Image:
    if name not in TRAIN_VIEWS + HOLDOUT_VIEWS:
        raise RiposteError("PUBLICATION_VIEW_INVALID")
    image = image.convert("RGB")
    w, h = image.size
    if name.startswith("resize"):
        factor = .5 if name.startswith("resize50") else .75
        image = image.resize((max(1, int(w * factor)), max(1, int(h * factor))), Image.Resampling.LANCZOS)
    if "jpeg" in name:
        quality = int(name.split("jpeg")[-1])
        stream = io.BytesIO()
        image.save(stream, "JPEG", quality=quality, subsampling=2, optimize=False)
        stream.seek(0)
        with Image.open(stream) as encoded:
            image = encoded.convert("RGB")
    if name == "offset-crop85":
        box = (int(w * .11), int(h * .03), max(int(w * .11) + 1, int(w * .96)), max(int(h * .03) + 1, int(h * .88)))
        image = image.crop(box).resize((w, h), Image.Resampling.LANCZOS)
    if name == "blur06":
        image = image.filter(ImageFilter.GaussianBlur(.6))
    image.info.clear()
    return image


def tensor_image(x) -> Image.Image:
    return Image.fromarray(x.detach().clamp(0, 1).mul(255).round()[0].permute(1, 2, 0).cpu().numpy().astype(np.uint8))


def image_tensor(image: Image.Image, device="cpu"):
    import torch
    return torch.from_numpy(np.asarray(image.convert("RGB"), dtype=np.float32).copy()).permute(2, 0, 1)[None].to(device) / 255


def differentiable_view(x, name: str):
    import torch.nn.functional as F
    from .optimizer import jpeg_surrogate
    if name not in TRAIN_VIEWS:
        raise RiposteError("TRAIN_VIEW_INVALID")
    if name == "identity":
        return x
    actual = image_tensor(publication_view(tensor_image(x), name), x.device)
    if name == "jpeg85":
        surrogate = jpeg_surrogate(x, 85)
    else:
        surrogate = F.interpolate(x, size=actual.shape[-2:], mode="bilinear", align_corners=False, antialias=True)
    return surrogate + (actual - surrogate).detach()


def keep_mask(shape: tuple[int, int], kind: str, seed: int = 0, device="cpu"):
    import torch
    h, w = shape
    if kind not in MASKS or min(h, w) < 2:
        raise RiposteError("MASK_CONTEXT_INVALID")
    mask = np.ones((h, w), dtype=np.float32)
    if kind != "whole":
        rng = np.random.default_rng(seed)
        scale = float(rng.uniform(.35, .55))
        dy, dx = max(1, int(h * scale)), max(1, int(w * scale))
        cy, cx = h // 2, w // 2
        if kind == "center":
            cy += int(rng.uniform(-.1, .1) * h)
            cx += int(rng.uniform(-.1, .1) * w)
        elif kind == "left":
            cx = dx // 2
        elif kind == "right":
            cx = w - (dx + 1) // 2
        elif kind == "top":
            cy = dy // 2
        else:
            cy = h - (dy + 1) // 2
        y, x = max(0, cy - dy // 2), max(0, cx - dx // 2)
        mask[y:min(h, y + dy), x:min(w, x + dx)] = 0
    return torch.from_numpy(mask)[None, None].to(device)


def budget_map(x, epsilon: int, preserve_white: bool = True):
    import torch
    import torch.nn.functional as F
    if not isinstance(epsilon, int) or isinstance(epsilon, bool) or not 1 <= epsilon <= 16:
        raise RiposteError("GUARD_PARAMETERS_INVALID")
    luma = x.mean(1, keepdim=True)
    local = F.avg_pool2d(F.pad(luma, (1, 1, 1, 1), mode="replicate"), 3, stride=1)
    detail = (luma - local).abs()
    weights = torch.where(detail > .08, .5, 1.)
    if preserve_white:
        weights = torch.where((x.min(1, keepdim=True).values > .97) & (detail < .005), 0., weights)
    return (weights * epsilon).floor() / 255


def spectral_direction(gradient, strength: float):
    """DCT-weighted search direction, NOT a strict frequency-support constraint."""
    import torch
    import torch.nn.functional as F
    if not 0 <= strength <= 1:
        raise RiposteError("FREQUENCY_WEIGHT_INVALID")
    if strength == 0:
        return gradient
    n, c, h, w = gradient.shape
    padded = F.pad(gradient, (0, (-w) % 8, 0, (-h) % 8), mode="replicate")
    hp, wp = padded.shape[-2:]
    blocks = padded.reshape(n, c, hp // 8, 8, wp // 8, 8).permute(0, 1, 2, 4, 3, 5)
    k = torch.arange(8, device=gradient.device, dtype=gradient.dtype)
    dct = .5 * torch.cos(math.pi * (2 * k[None, :] + 1) * k[:, None] / 16)
    dct[0] *= 1 / math.sqrt(2)
    frequency = (k[:, None] + k[None, :]) / 14
    weight = 1 - strength * frequency.square()
    result = dct.T @ ((dct @ blocks @ dct.T) * weight) @ dct
    return result.permute(0, 1, 2, 4, 3, 5).reshape(n, c, hp, wp)[..., :h, :w]


def matched_control(clean: Image.Image, candidate: Image.Image, seed: int) -> Image.Image:
    """Randomize feasible delta signs; exactly preserve each |delta| and RMS.

    Boundary pixels use the feasible sign when only one exists. This is a
    sign-scrambled, magnitude-matched control, not iid Gaussian noise.
    """
    if clean.size != candidate.size or not 0 <= seed < 2**32:
        raise RiposteError("CONTROL_PARAMETERS_INVALID")
    a, b = [np.asarray(im.convert("RGB"), dtype=np.int16) for im in (clean, candidate)]
    magnitude = np.abs(b - a)
    rng = np.random.default_rng(seed)
    sign = rng.choice(np.array([-1, 1], dtype=np.int16), a.shape)
    random_delta = magnitude * sign
    feasible = ((a + random_delta) >= 0) & ((a + random_delta) <= 255)
    delta = np.where(feasible, random_delta, -random_delta)
    return Image.fromarray((a + delta).astype(np.uint8))
