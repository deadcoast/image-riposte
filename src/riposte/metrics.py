from __future__ import annotations
import io
import math
from PIL import Image, ImageFilter
import numpy as np
from .errors import RiposteError

TRANSFORMS = ("identity", "jpeg95", "jpeg85", "jpeg70", "resize75", "crop90", "blur06", "resize75-jpeg85")

def transform(image: Image.Image, name: str) -> Image.Image:
    if name not in TRANSFORMS:
        raise RiposteError("TRANSFORM_INVALID")
    image = image.convert("RGB")
    if name.startswith("resize75"):
        w, h = image.size
        image = image.resize((max(1, int(w*.75)), max(1, int(h*.75))), Image.Resampling.LANCZOS)
    if "jpeg" in name:
        quality = int(name.split("jpeg")[-1])
        buf = io.BytesIO()
        image.save(buf, "JPEG", quality=quality, subsampling=2)
        buf.seek(0)
        with Image.open(buf) as encoded:
            image = encoded.convert("RGB")
    if name == "crop90":
        w, h = image.size
        x, y = int(w*.05), int(h*.05)
        image = image.crop((x, y, w-x, h-y)).resize((w, h), Image.Resampling.LANCZOS)
    if name == "blur06":
        image = image.filter(ImageFilter.GaussianBlur(.6))
    return image

def fidelity(clean: Image.Image, candidate: Image.Image) -> dict:
    if clean.size != candidate.size:
        raise RiposteError("IMAGE_SIZE_MISMATCH")
    a, b = (np.asarray(im.convert("RGB"), dtype=np.float64) for im in (clean, candidate))
    d = a-b
    mse = float(np.mean(d*d))
    # Global SSIM is deliberately not used: it can hide local damage to line art.
    edge_errors = []
    for axis in (0, 1):
        if a.shape[axis] > 1:
            edge_errors.append(float(np.abs(np.diff(a, axis=axis)-np.diff(b, axis=axis)).mean()))
    return {"psnr_db": round(10*math.log10(255**2/mse), 5) if mse else None,
            "identical_pixels": bool(mse == 0), "rmse_255": round(math.sqrt(mse), 6),
            "max_channel_delta_255": int(np.abs(d).max()),
            "mean_channel_delta_255": round(float(np.abs(d).mean()), 6),
            "edge_error_255": round(float(np.mean(edge_errors)), 6) if edge_errors else 0.0}

def transport_report(clean: Image.Image, candidate: Image.Image) -> dict:
    """Matched transforms isolate residual perturbation from codec distortion."""
    rows = []
    for name in TRANSFORMS:
        a, b = transform(clean, name), transform(candidate, name)
        rows.append({"transform": name, **fidelity(a, b)})
    return {"evidence_level": "PIXEL_TRANSPORT_ONLY", "ai_protection": "UNVERIFIED",
            "profiles": "Generic stress tests; not claims about any platform's current encoder.",
            "rows": rows}

def difference_image(clean: Image.Image, candidate: Image.Image, gain: int = 12) -> Image.Image:
    if clean.size != candidate.size:
        raise RiposteError("IMAGE_SIZE_MISMATCH")
    a, b = (np.asarray(im.convert("RGB"), dtype=np.float32) for im in (clean, candidate))
    return Image.fromarray(np.clip(np.abs(a-b)*gain, 0, 255).astype(np.uint8))
