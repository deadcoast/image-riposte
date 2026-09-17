"""Experimental, quantization-aware, multi-VAE / multi-transform PGD.

This module optimizes measurable encoder divergence. It neither replicates an
upstream defense nor establishes downstream editing/video/style protection.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
import math
import numpy as np
from PIL import Image
from .errors import RiposteError
from .metrics import fidelity

@dataclass(frozen=True)
class GuardConfig:
    epsilon_255: int = 4
    steps: int = 48
    step_255: float = 1.0
    seed: int = 7
    preserve_white: bool = True
    def __post_init__(self):
        if not 1 <= self.epsilon_255 <= 16 or not 1 <= self.steps <= 1000 or not .05 <= self.step_255 <= 8:
            raise RiposteError("GUARD_PARAMETERS_INVALID")
        if not 0 <= self.seed < 2**32:
            raise RiposteError("SEED_INVALID")

class LocalVAE:
    """An explicit local Diffusers VAE directory; no hub fetch or remote code."""
    def __init__(self, folder: Path, device: str = "auto"):
        import os
        for name in ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "TRANSFORMERS_OFFLINE"):
            os.environ[name] = "1"
        try:
            import torch
            from diffusers import AutoencoderKL
        except ImportError:
            raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
        if not folder.is_dir() or not (folder / "config.json").is_file():
            raise RiposteError("LOCAL_VAE_DIRECTORY_REQUIRED")
        if not list(folder.glob("*.safetensors")):
            raise RiposteError("SAFETENSORS_REQUIRED")
        self.device = "cuda" if device == "auto" and torch.cuda.is_available() else "cpu" if device == "auto" else device
        if self.device not in {"cpu", "cuda", "mps"}:
            raise RiposteError("DEVICE_INVALID")
        try:
            self.model = AutoencoderKL.from_pretrained(str(folder), local_files_only=True,
                use_safetensors=True).to(device=self.device, dtype=torch.float32).eval()
            self.model.requires_grad_(False)
        except Exception:
            raise RiposteError("LOCAL_VAE_LOAD_FAILED") from None
    def __call__(self, x):
        import torch.nn.functional as F
        # Pad, never silently crop. The factor follows the loaded VAE architecture.
        factor = 2 ** (len(self.model.config.block_out_channels)-1)
        h, w = x.shape[-2:]
        x = F.pad(x, (0, (-w)%factor, 0, (-h)%factor), mode="replicate")
        return self.model.encode(x*2-1).latent_dist.mean

def _round_ste(x):
    return x + (x.round()-x).detach()

def jpeg_surrogate(x, quality: int = 85):
    """Differentiable 8x8 DCT + straight-through quantization, 4:4:4.

Evaluation deliberately uses REAL Pillow JPEG 4:2:0; this is an approximation,
not a byte-accurate social-platform encoder.
"""
    import torch
    import torch.nn.functional as F
    if not 1 <= quality <= 100:
        raise RiposteError("JPEG_QUALITY_INVALID")
    n, _, h, w = x.shape
    r, g, b = x[:, 0:1], x[:, 1:2], x[:, 2:3]
    ycc = torch.cat((.299*r+.587*g+.114*b, -.168736*r-.331264*g+.5*b+.5, .5*r-.418688*g-.081312*b+.5), 1)*255-128
    ycc = F.pad(ycc, (0, (-w)%8, 0, (-h)%8), mode="replicate")
    hp, wp = ycc.shape[-2:]
    blocks = ycc.reshape(n, 3, hp//8, 8, wp//8, 8).permute(0,1,2,4,3,5)
    k = torch.arange(8, device=x.device, dtype=x.dtype)
    dct = .5*torch.cos(math.pi*(2*k[None,:]+1)*k[:,None]/16)
    dct[0] *= 1/math.sqrt(2)
    table_y = [[16,11,10,16,24,40,51,61],[12,12,14,19,26,58,60,55],[14,13,16,24,40,57,69,56],[14,17,22,29,51,87,80,62],[18,22,37,56,68,109,103,77],[24,35,55,64,81,104,113,92],[49,64,78,87,103,121,120,101],[72,92,95,98,112,100,103,99]]
    table_c = [[17,18,24,47,99,99,99,99],[18,21,26,66,99,99,99,99],[24,26,56,99,99,99,99,99],[47,66,99,99,99,99,99,99]] + [[99]*8]*4
    tables = torch.tensor([table_y, table_c, table_c], device=x.device, dtype=x.dtype)
    scale = 5000/quality if quality < 50 else 200-2*quality
    quant = ((tables*scale+50)/100).floor().clamp(1,255)[None,:,None,None]
    coefficients = dct @ blocks @ dct.T
    restored = dct.T @ (_round_ste(coefficients/quant)*quant) @ dct
    restored = restored.permute(0,1,2,4,3,5).reshape(n,3,hp,wp)[...,:h,:w]
    restored = (restored+128)/255
    yy, cb, cr = restored[:,0:1], restored[:,1:2]-.5, restored[:,2:3]-.5
    return torch.cat((yy+1.402*cr, yy-.344136*cb-.714136*cr, yy+1.772*cb),1).clamp(0,1)

def eot(x, name: str):
    import torch.nn.functional as F
    if name == "identity":
        return x
    if name == "resize75":
        h, w = x.shape[-2:]
        small = F.interpolate(x, size=(max(1,int(h*.75)),max(1,int(w*.75))), mode="bilinear", align_corners=False, antialias=True)
        return F.interpolate(small, size=(h,w), mode="bilinear", align_corners=False, antialias=True)
    if name == "jpeg85":
        return jpeg_surrogate(x, 85)
    if name == "crop90":
        h,w = x.shape[-2:]
        dy,dx = int(h*.05),int(w*.05)
        return F.interpolate(x[...,dy:h-dy,dx:w-dx], size=(h,w), mode="bilinear", align_corners=False)
    raise RiposteError("EOT_INVALID")

def protect(image: Image.Image, encoders: list, config: GuardConfig = GuardConfig(), progress: Callable | None = None) -> tuple[Image.Image, dict]:
    try:
        import torch
        import torch.nn.functional as F
    except ImportError:
        raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
    if not encoders:
        raise RiposteError("NO_MODEL_NO_PROTECTION")
    if min(image.size) < 16 or max(image.size) > 4096:
        raise RiposteError("GUARD_DIMENSIONS_INVALID")
    device = getattr(encoders[0], "device", "cpu")
    if any(getattr(e, "device", "cpu") != device for e in encoders):
        raise RiposteError("ENSEMBLE_DEVICE_MISMATCH")
    array = np.asarray(image.convert("RGB"), dtype=np.float32)/255
    x = torch.from_numpy(array.copy()).permute(2,0,1)[None].to(device)
    # Preserve smooth white canvas, and reduce budgets around high-contrast edges.
    luma = x.mean(1,keepdim=True)
    local = F.avg_pool2d(F.pad(luma,(1,1,1,1),mode="replicate"),3,stride=1)
    detail = (luma-local).abs()
    mask = torch.where(detail > .08, .5, 1.)
    if config.preserve_white:
        mask = torch.where((x.min(1,keepdim=True).values > .97) & (detail < .005), 0., mask)
    # Integer budgets keep exported 8-bit pixels inside the true per-pixel bound.
    budget = (mask * config.epsilon_255).floor()/255
    if not bool((budget > 0).any()):
        raise RiposteError("NO_EDITABLE_PIXEL_BUDGET")
    low, high = (x-budget).clamp(0,1), (x+budget).clamp(0,1)
    generator = torch.Generator(device=device).manual_seed(config.seed)
    noise = (torch.rand(x.shape, generator=generator, device=device)*2-1)*budget
    candidate = (x+noise).clamp(0,1).detach()
    names = ("identity", "resize75", "jpeg85", "crop90")
    baselines = []
    with torch.no_grad():
        for model in encoders:
            for name in names:
                z = model(eot(x, name)).detach()
                baselines.append((model, name, z, z.square().mean().clamp_min(1e-6)))
    trace = []
    had_gradient = False
    for step in range(config.steps):
        candidate = candidate.detach().requires_grad_(True)
        losses = []
        # Quantize on every forward pass: optimize the pixels that are exported.
        q = _round_ste(candidate*255)/255
        for model, name, target, norm in baselines:
            losses.append((model(eot(q,name))-target).square().mean()/norm)
        values = torch.stack(losses)
        # Adaptive soft minimum: a large win against one transform cannot dominate.
        temperature = values.detach().mean().clamp_min(1e-6)
        objective = -temperature * (torch.logsumexp(-values/temperature,0)-math.log(len(losses)))
        if not torch.isfinite(objective):
            raise RiposteError("OPTIMIZER_NONFINITE")
        if not objective.requires_grad:
            raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
        grad = torch.autograd.grad(objective,candidate,allow_unused=True)[0]
        if grad is None:
            raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
        if not torch.isfinite(grad).all():
            raise RiposteError("OPTIMIZER_NONFINITE")
        had_gradient |= bool(((grad != 0) & (budget > 0)).any())
        candidate = (candidate + config.step_255/255*grad.sign()).detach()
        candidate = torch.maximum(torch.minimum(candidate,high),low)
        if step % max(1,config.steps//12) == 0 or step == config.steps-1:
            point = {"step": step+1, "soft_worst_shift": float(objective.detach().cpu())}
            trace.append(point)
            if progress:
                progress({"phase":"Optimizing experimental candidate", "processed":step+1, "total":config.steps})
    if not had_gradient:
        raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
    quantized = candidate.detach().mul(255).round().clamp(0,255)
    output = Image.fromarray(quantized[0].permute(1,2,0).cpu().numpy().astype(np.uint8))
    final = []
    with torch.no_grad():
        for i,(model,name,target,norm) in enumerate(baselines):
            score = float(((model(eot(quantized/255,name))-target).square().mean()/norm).cpu())
            if not math.isfinite(score):
                raise RiposteError("OPTIMIZER_NONFINITE")
            final.append({"encoder":i//len(names)+1, "transform":name, "relative_feature_mse":score})
    if min(item['relative_feature_mse'] for item in final) <= 0:
        raise RiposteError("NO_USEFUL_CANDIDATE")
    quality = fidelity(image,output)
    if quality["max_channel_delta_255"] > config.epsilon_255:
        raise RiposteError("PERTURBATION_BUDGET_VIOLATED")
    report = {"method":"RIPOSTE EOT-VAE / experimental", "evidence_level":"ENCODER_PROXY_ONLY",
              "ai_protection":"UNVERIFIED", "epsilon_255":config.epsilon_255, "steps":config.steps,
              "seed":config.seed, "encoders":len(encoders), "fidelity":quality, "trace":trace,
              "proxy_evaluation":final,
              "limits":"No training, semantic-recognition, edit-output, or video-protection conclusion follows from these scores."}
    return output, report
