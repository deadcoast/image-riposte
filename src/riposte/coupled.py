"""One-raster masked/codec/early-conditioning projected optimization.

Original RIPOSTE experimental method, not a paper-name reproduction. The
image remains the same constrained variable for every branch. A two-pass
soft-min gradient releases one model graph at a time rather than retaining
an ensemble of graphs at publication resolution.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
from typing import Callable, TYPE_CHECKING
import numpy as np
from PIL import Image
from .errors import RiposteError
from .metrics import fidelity
from .optimizer import _round_ste
from .views import (TRAIN_VIEWS, budget_map, differentiable_view, image_tensor,
                    keep_mask, spectral_direction, tensor_image)

if TYPE_CHECKING:
    from torch import Tensor


@dataclass(frozen=True)
class CoupledConfig:
    epsilon_255: int = 4
    steps: int = 24
    step_255: float = .75
    seed: int = 7
    preserve_white: bool = True
    frequency_weight: float = .65

    def __post_init__(self):
        if (not isinstance(self.epsilon_255, int) or isinstance(self.epsilon_255, bool)
            or not 1 <= self.epsilon_255 <= 16 or not isinstance(self.steps, int)
            or isinstance(self.steps, bool) or not 1 <= self.steps <= 1000 or not math.isfinite(self.step_255)
            or not .05 <= self.step_255 <= 8 or not 0 <= self.frequency_weight <= 1
            or not isinstance(self.seed, int) or isinstance(self.seed, bool) or not 0 <= self.seed < 2**32
            or not isinstance(self.preserve_white, bool)):
            raise RiposteError("GUARD_PARAMETERS_INVALID")


@dataclass(frozen=True)
class Branch:
    kind: str
    index: int
    view: str
    mask: str
    seed: int
    early_fraction: float = .9
    prompt: str = "background"


def _branches(encoders, probe, seed):
    result = [Branch("encoder", i, view, mask, (seed + 97 * j) % 2**32)
              for i in range(len(encoders)) for view in TRAIN_VIEWS
              for j, mask in enumerate(("whole", "center", "left"))]
    if probe is not None:
        result += [Branch("early_denoiser", 0, view, mask, (seed + 701 + j) % 2**32,
                          fraction, prompt)
                   for view in ("identity", "jpeg85")
                   for j, (mask, fraction, prompt) in enumerate((("center", .9, "background"),
                                                                ("left", .98, "material")))]
    return result


def _features(x, branch, encoders, probe):
    viewed = differentiable_view(x, branch.view)
    return _view_features(viewed, branch, encoders, probe)


def _view_features(viewed: Tensor, branch: Branch, encoders: list[Callable[[Tensor], Tensor]],
                   probe: Callable[[Tensor, Tensor, int, float, str], Tensor] | None) -> Tensor:
    keep = keep_mask(viewed.shape[-2:], branch.mask, branch.seed, viewed.device)
    if branch.kind == "encoder":
        return encoders[branch.index](viewed * keep + .5 * (1 - keep))
    if probe is None:
        raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
    return probe(viewed, keep, branch.seed, branch.early_fraction, branch.prompt)


def protect_coupled(image: Image.Image, encoders: list, config: CoupledConfig = CoupledConfig(),
                    probe=None, progress: Callable | None = None) -> tuple[Image.Image, dict]:
    try:
        import torch
    except ImportError:
        raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
    if not encoders:
        raise RiposteError("NO_MODEL_NO_PROTECTION")
    if min(image.size) < 16 or max(image.size) > 4096:
        raise RiposteError("GUARD_DIMENSIONS_INVALID")
    device = getattr(encoders[0], "device", "cpu")
    if any(getattr(m, "device", "cpu") != device for m in encoders + ([probe] if probe else [])):
        raise RiposteError("ENSEMBLE_DEVICE_MISMATCH")
    x = image_tensor(image, device)
    budget = budget_map(x, config.epsilon_255, config.preserve_white)
    if not bool((budget > 0).any()):
        raise RiposteError("NO_EDITABLE_PIXEL_BUDGET")
    low, high = (x - budget).clamp(0, 1), (x + budget).clamp(0, 1)
    rng = torch.Generator("cpu").manual_seed(config.seed)
    candidate = (x + (torch.rand(x.shape, generator=rng).to(device) * 2 - 1) * budget).clamp(0, 1).detach()
    branches = _branches(encoders, probe, config.seed)
    references = []

    def notify(phase, processed, branch=0):
        if progress:
            progress({"phase": phase, "processed": processed, "total": config.steps,
                      "branch": branch, "branches": len(branches)})

    notify("Preparing paired model contexts", 0)
    with torch.no_grad():
        for index, branch in enumerate(branches):
            notify("Preparing paired model contexts", 0, index + 1)
            z = _features(x, branch, encoders, probe).detach()
            if not bool(torch.isfinite(z).all()):
                raise RiposteError("OPTIMIZER_NONFINITE")
            references.append((z.cpu(), max(float(z.square().mean().cpu()), 1e-6)))

    def score(q, branch, reference):
        target, norm = reference
        z = _features(q, branch, encoders, probe)
        value = (z - target.to(device)).square().mean() / norm
        if not bool(torch.isfinite(value)):
            raise RiposteError("OPTIMIZER_NONFINITE")
        return value

    trace, had_gradient = [], False
    for step in range(config.steps):
        q_eval = candidate.detach().mul(255).round() / 255
        values = []
        with torch.no_grad():
            for index, (branch, reference) in enumerate(zip(branches, references, strict=True)):
                notify("Scoring coupled contexts", step, index + 1)
                values.append(float(score(q_eval, branch, reference).cpu()))
        numbers = torch.tensor(values, device=device, dtype=x.dtype)
        tau = numbers.mean().clamp_min(1e-6)
        weights = torch.softmax(-numbers / tau, dim=0).detach()
        objective = -tau * (torch.logsumexp(-numbers / tau, dim=0) - math.log(len(values)))
        total_gradient = torch.zeros_like(x)
        for index, (branch, reference) in enumerate(zip(branches, references, strict=True)):
            notify("Optimizing coupled contexts", step + 1, index + 1)
            leaf = candidate.detach().requires_grad_(True)
            q = _round_ste(leaf * 255) / 255
            value = score(q, branch, reference)
            if not value.requires_grad:
                raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
            gradient = torch.autograd.grad(value, leaf, allow_unused=True)[0]
            if gradient is None:
                raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
            if not bool(torch.isfinite(gradient).all()):
                raise RiposteError("OPTIMIZER_NONFINITE")
            total_gradient.add_(gradient.detach() * weights[index])
            del leaf, q, value, gradient
        total_gradient = spectral_direction(total_gradient, config.frequency_weight)
        had_gradient |= bool(((total_gradient != 0) & (budget > 0)).any())
        candidate = candidate + (config.step_255 / 255) * total_gradient.sign()
        candidate = torch.maximum(torch.minimum(candidate, high), low).detach()
        if step % max(1, config.steps // 12) == 0 or step == config.steps - 1:
            trace.append({"step": step + 1, "soft_worst_shift": float(objective.cpu()),
                          "min_context_shift": min(values)})
    if not had_gradient:
        raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
    notify("Auditing final quantized candidate", config.steps)
    final_tensor = candidate.mul(255).round().clamp(0, 255) / 255
    delta = (final_tensor.mul(255).round() - x.mul(255).round()).abs()
    if bool((delta > budget.mul(255).round()).any()):
        raise RiposteError("PERTURBATION_BUDGET_VIOLATED")
    final = []
    with torch.no_grad():
        for index, (branch, reference) in enumerate(zip(branches, references, strict=True)):
            notify("Auditing final quantized candidate", config.steps, index + 1)
            final.append({"kind": branch.kind, "model": branch.index + 1, "view": branch.view,
                          "mask": branch.mask, "mask_seed": branch.seed,
                          "relative_feature_mse": float(score(final_tensor, branch, reference).cpu()),
                          **({"early_fraction": branch.early_fraction, "prompt_key": branch.prompt}
                             if branch.kind == "early_denoiser" else {})})
    output = tensor_image(final_tensor)
    report = {"method": "RIPOSTE coupled guard / experimental", "engine": "coupled-v1",
              "evidence_level": "EARLY_DENOISER_PROXY_ONLY" if probe else "MASKED_ENCODER_PROXY_ONLY",
              "ai_protection": "UNVERIFIED", "epsilon_255": config.epsilon_255, "steps": config.steps,
              "step_255": config.step_255, "seed": config.seed, "preserve_white": config.preserve_white,
              "frequency_weight": config.frequency_weight, "fidelity": fidelity(image, output),
              "encoders": len(encoders), "models": [getattr(e, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"}) for e in encoders],
              "probe_model": getattr(probe, "identity", None), "trace": trace, "proxy_evaluation": final,
              "optimization_views": list(TRAIN_VIEWS), "optimization_masks": ["whole", "center", "left"],
              "jpeg_forward": "PILLOW_REAL_420", "jpeg_backward": "DCT_444_STE_APPROXIMATION",
              "memory_strategy": "SEQUENTIAL_TWO_PASS_SOFTMIN",
              "limits": "Mask/encoder/early-conditioning shifts are not measured editing, recognition, style-learning or video resistance."}
    return output, report
