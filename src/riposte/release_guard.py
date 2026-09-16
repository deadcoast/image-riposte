"""Production candidate search: one raster, bounded damage, best feasible iterate.

This extends the coupled-v1 objective; results remain model-component proxies.
A temporal branch minimizes early predicted-frame differences, not a full-video
success metric. Optimization and selection contexts are never called held out.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import math
import numpy as np
from PIL import Image
from .errors import RiposteError
from .coupled import Branch, _branches, _features
from .optimizer import _round_ste
from .quality import QualityLimits, spatial_budget, quality_report
from .views import image_tensor, tensor_image, spectral_direction, differentiable_view, TRAIN_VIEWS

@dataclass(frozen=True)
class ReleaseConfig:
    steps: int = 24
    restarts: int = 2
    seed: int = 7
    step_255: float = .75
    checkpoint_every: int = 4
    frequency_weight: float = .65

    def __post_init__(self):
        if (type(self.steps) is not int or not 1 <= self.steps <= 1000
            or type(self.restarts) is not int or not 1 <= self.restarts <= 4
            or type(self.seed) is not int or not 0 <= self.seed < 2**32
            or type(self.checkpoint_every) is not int or not 1 <= self.checkpoint_every <= 32
            or not math.isfinite(self.step_255) or not .05 <= self.step_255 <= 8
            or not math.isfinite(self.frequency_weight) or not 0 <= self.frequency_weight <= 1):
            raise RiposteError("RELEASE_GUARD_PARAMETERS_INVALID")


def temporal_energy(frames):
    if frames.ndim != 5 or frames.shape[1] < 2:
        raise RiposteError("TEMPORAL_FEATURE_SHAPE_INVALID")
    return (frames[:, 1:] - frames[:, :-1]).square().mean()


def protect_release(image: Image.Image, encoders: list, config: ReleaseConfig = ReleaseConfig(),
                    limits: QualityLimits = QualityLimits(), probe=None, temporal=None, progress=None):
    import torch
    if not encoders: raise RiposteError("NO_MODEL_NO_PROTECTION")
    if min(image.size) < 16 or max(image.size) > 4096: raise RiposteError("GUARD_DIMENSIONS_INVALID")
    device = getattr(encoders[0], "device", "cpu")
    if any(getattr(m, "device", "cpu") != device for m in encoders + [m for m in (probe, temporal) if m is not None]):
        raise RiposteError("ENSEMBLE_DEVICE_MISMATCH")
    x = image_tensor(image, device)
    caps = spatial_budget(image, limits)
    budget = torch.from_numpy(caps.astype(np.float32))[None, None].to(device) / 255
    if not bool((budget > 0).any()): raise RiposteError("NO_EDITABLE_PIXEL_BUDGET")
    low, high = (x - budget).clamp(0, 1), (x + budget).clamp(0, 1)
    branches = _branches(encoders, probe, config.seed)
    if temporal is not None:
        branches += [Branch("temporal", 0, v, "whole", (config.seed + 1709) % 2**32) for v in ("identity", "jpeg85")]

    def notify(phase, restart=0, step=0, branch=0):
        if progress:
            progress({"phase": phase, "processed": restart * config.steps + step,
                      "total": config.steps * config.restarts, "branch": branch, "branches": len(branches)})

    def feature(q, branch):
        return (temporal(differentiable_view(q, branch.view), branch.seed) if branch.kind == "temporal"
                else _features(q, branch, encoders, probe))

    refs = []
    with torch.no_grad():
        for i, branch in enumerate(branches):
            notify("Preparing protection contexts", branch=i + 1)
            z = feature(x, branch).detach()
            if not bool(torch.isfinite(z).all()): raise RiposteError("OPTIMIZER_NONFINITE")
            if branch.kind == "temporal":
                energy = float(temporal_energy(z).cpu())
                if energy <= 1e-12: raise RiposteError("TEMPORAL_REFERENCE_HAS_NO_SIGNAL")
                refs.append((None, energy))
            else:
                refs.append((z.cpu(), max(float(z.square().mean().cpu()), 1e-6)))

    def score(q, branch, ref):
        z = feature(q, branch)
        val = (1 - temporal_energy(z) / ref[1] if branch.kind == "temporal"
               else (z - ref[0].to(device)).square().mean() / ref[1])
        if not bool(torch.isfinite(val)): raise RiposteError("OPTIMIZER_NONFINITE")
        return val

    def scores(q, restart, step):
        with torch.no_grad():
            values = []
            for i, (branch, ref) in enumerate(zip(branches, refs, strict=True)):
                notify("Measuring quantized protection contexts", restart, step, i + 1)
                values.append(float(score(q, branch, ref).cpu()))
            return values

    best, best_key, best_info, trace, had_gradient = None, None, None, [], False
    for restart in range(config.restarts):
        rng = torch.Generator("cpu").manual_seed((config.seed + restart * 104729) % 2**32)
        candidate = torch.maximum(torch.minimum(x + (torch.rand(x.shape, generator=rng).to(device) * 2 - 1) * budget, high), low).detach()
        step_size, stale, restart_best = config.step_255, 0, None
        initial_scores = scores(candidate.mul(255).round() / 255, restart, 0)
        initial_min = min(initial_scores)
        values = initial_scores
        for step in range(1, config.steps + 1):
            numbers = torch.tensor(values, device=device, dtype=x.dtype)
            tau = numbers.abs().mean().clamp_min(1e-6)
            weights = torch.softmax(-numbers / tau, dim=0).detach()
            gradient = torch.zeros_like(x)
            for index, (branch, ref) in enumerate(zip(branches, refs, strict=True)):
                notify("Optimizing publishing raster", restart, step, index + 1)
                leaf = candidate.detach().requires_grad_(True)
                value = score(_round_ste(leaf * 255) / 255, branch, ref)
                if not value.requires_grad: raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
                g = torch.autograd.grad(value, leaf, allow_unused=True)[0]
                if g is None: raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
                if not bool(torch.isfinite(g).all()): raise RiposteError("OPTIMIZER_NONFINITE")
                gradient.add_(g.detach() * weights[index])
                del g, leaf, value
            gradient = spectral_direction(gradient, config.frequency_weight)
            useful = bool(((gradient != 0) & (budget > 0)).any())
            had_gradient |= useful
            candidate = torch.maximum(torch.minimum(candidate + step_size / 255 * gradient.sign(), high), low).detach()
            q = candidate.mul(255).round() / 255
            values = scores(q, restart, step)
            if step == 1 or step % config.checkpoint_every == 0 or step == config.steps:
                output = tensor_image(q)
                quality = quality_report(image, output, limits)
                key = (min(values), sum(values) / len(values))
                # A random start is never eligible; require an actual useful update
                # and improved worst context compared with that restart's seed.
                eligible = useful and key[0] > max(initial_min + 1e-12, 1e-12) and quality["status"] == "PASS"
                improved = eligible and (best_key is None or key > best_key)
                trace.append({"restart": restart + 1, "step": step, "min_context_score": key[0],
                              "mean_context_score": key[1], "numeric_quality": quality["status"],
                              "eligible": eligible, "selected": improved, "step_255": step_size})
                if improved:
                    best, best_key = output.copy(), key
                    best_info = {"restart": restart + 1, "step": step, "scores": list(values),
                                 "initial_min_context_score": initial_min, "quality": quality}
                if restart_best is None or key > restart_best:
                    restart_best, stale = key, 0
                else:
                    stale += 1
                    if stale >= 2:
                        step_size, stale = max(.05, step_size / 2), 0
    if not had_gradient: raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
    if best is None: raise RiposteError("NO_IMPROVED_FIDELITY_ACCEPTABLE_CANDIDATE")
    notify("Auditing selected final pixels", config.restarts - 1, config.steps)
    quality = quality_report(image, best, limits)
    if quality["status"] != "PASS": raise RiposteError("FINAL_QUALITY_AUDIT_FAILED")
    rows = [{"kind": b.kind, "view": b.view, "mask": b.mask, "model": b.index + 1,
             "mask_seed": b.seed, "score": value}
            for b, value in zip(branches, best_info.pop("scores"), strict=True)]
    return best, {"engine": "release-v1", "method": "RIPOSTE constrained publication guard / experimental",
                  "ai_protection": "UNVERIFIED", "evidence_level": "TEMPORAL_AND_IMAGE_COMPONENT_PROXY" if temporal else "IMAGE_COMPONENT_PROXY",
                  "config": asdict(config), "quality": quality, "selection": {k: v for k, v in best_info.items() if k != "quality"},
                  "trace": trace, "contexts": rows, "optimization_views": list(TRAIN_VIEWS),
                  "optimization_masks": ["whole", "center", "left"], "selection_is_heldout": False,
                  "models": [getattr(e, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"}) for e in encoders],
                  "probe_model": getattr(probe, "identity", None), "temporal_model": getattr(temporal, "identity", None),
                  "jpeg_forward": "PILLOW_REAL_420", "jpeg_backward": "DCT_444_STE_APPROXIMATION",
                  "limits": "Best feasible model-component proxy, not verified editing/video/recognition resistance. Temporal branch is image-conditioned, not text-guided."}
