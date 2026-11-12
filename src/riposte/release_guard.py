"""Production candidate search: one raster, bounded damage, best feasible iterate.

This extends the coupled-v1 objective; results remain model-component proxies.
A temporal branch minimizes early predicted-frame differences, not a full-video
success metric. Optimization and selection contexts are never called held out.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import math
from typing import TYPE_CHECKING
import numpy as np
from PIL import Image
from .errors import RiposteError
from .coupled import Branch, _branches, _features
from .coupled import _view_features
from .context_graph import context_groups, context_values, context_gradient
from .optimizer import _round_ste
from .quality import QualityLimits, spatial_budget, quality_report
from .spatial import ArtistMask
from .views import image_tensor, tensor_image, spectral_direction, differentiable_view, TRAIN_VIEWS

if TYPE_CHECKING:
    from torch import Tensor

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
                    limits: QualityLimits = QualityLimits(), probe=None, temporal=None, progress=None, *, artist_mask: ArtistMask | None = None):
    import torch
    if not encoders: raise RiposteError("NO_MODEL_NO_PROTECTION")
    if min(image.size) < 16 or max(image.size) > 4096: raise RiposteError("GUARD_DIMENSIONS_INVALID")
    device = getattr(encoders[0], "device", "cpu")
    if any(getattr(m, "device", "cpu") != device for m in encoders + [m for m in (probe, temporal) if m is not None]):
        raise RiposteError("ENSEMBLE_DEVICE_MISMATCH")
    x = image_tensor(image, device)
    caps = spatial_budget(image, limits, artist_mask)
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

    def feature(viewed, branch):
        return (temporal(viewed, branch.seed) if branch.kind == "temporal"
                else _view_features(viewed, branch, encoders, probe))

    names = [branch.view for branch in branches]
    refs: dict[int, tuple[Tensor | None, float]] = {}
    completed = 0
    with torch.no_grad():
        for name, indices in context_groups(names):
            viewed = differentiable_view(x, name)
            for i in indices:
                completed += 1
                branch = branches[i]
                notify("Preparing protection contexts", branch=completed)
                z = feature(viewed, branch).detach()
                if not bool(torch.isfinite(z).all()): raise RiposteError("OPTIMIZER_NONFINITE")
                if branch.kind == "temporal":
                    energy = float(temporal_energy(z).cpu())
                    if energy <= 1e-12: raise RiposteError("TEMPORAL_REFERENCE_HAS_NO_SIGNAL")
                    refs[i] = (None, energy)
                else:
                    refs[i] = (z.cpu(), max(float(z.square().mean().cpu()), 1e-6))

    def score(q, branch, ref):
        z = feature(q, branch)
        val = (1 - temporal_energy(z) / ref[1] if branch.kind == "temporal"
               else (z - ref[0].to(device)).square().mean() / ref[1])
        if not bool(torch.isfinite(val)): raise RiposteError("OPTIMIZER_NONFINITE")
        return val

    def scores(q, restart, step):
        return context_values(q, names, lambda viewed, i: score(viewed, branches[i], refs[i]),
                              lambda count: notify("Measuring quantized protection contexts", restart, step, count))

    best, best_key, best_info, trace, had_gradient = None, None, None, [], False
    for restart in range(config.restarts):
        rng = torch.Generator("cpu").manual_seed((config.seed + restart * 104729) % 2**32)
        candidate = torch.maximum(torch.minimum(x + (torch.rand(x.shape, generator=rng).to(device) * 2 - 1) * budget, high), low).detach()
        step_size, stale, restart_best = config.step_255, 0, None
        initial_scores = scores(candidate.mul(255).round() / 255, restart, 0)
        initial_min = min(initial_scores)
        values = initial_scores
        for step in range(1, config.steps + 1):
            gradient = context_gradient(candidate, names, values,
                lambda viewed, i: score(viewed, branches[i], refs[i]),
                lambda count: notify("Optimizing publishing raster", restart, step, count))
            gradient = spectral_direction(gradient, config.frequency_weight)
            useful = bool(((gradient != 0) & (budget > 0)).any())
            had_gradient |= useful
            # Check the exact output pixels before committing an update. Retry
            # from the same iterate so an oversized step does not consume the
            # entire search budget or push subsequent gradients out of bounds.
            accepted = False
            for backtracks in range(9):
                proposal = torch.maximum(torch.minimum(candidate + step_size / 255 * gradient.sign(), high), low).detach()
                q = proposal.mul(255).round() / 255
                output = tensor_image(q)
                quality = quality_report(image, output, limits, artist_mask)
                if quality["status"] == "PASS":
                    values = scores(q, restart, step)
                    candidate, accepted = proposal, True
                    break
                if step_size <= .05 or backtracks == 8:
                    break
                notify("Reducing publishing step for image quality", restart, step)
                step_size = max(.05, step_size / 2)
            key = (min(values), sum(values) / len(values))
            # A random start is never eligible; require an accepted useful update
            # and improved worst context compared with that restart's seed.
            eligible = accepted and useful and key[0] > max(initial_min + 1e-12, 1e-12)
            improved = eligible and (best_key is None or key > best_key)
            # Checkpoint cadence controls reporting only. Never discard a better
            # feasible iterate just because it falls between trace checkpoints.
            if improved or backtracks or not accepted or step == 1 or step % config.checkpoint_every == 0 or step == config.steps:
                trace.append({"restart": restart + 1, "step": step, "min_context_score": key[0],
                              "mean_context_score": key[1], "numeric_quality": quality["status"],
                              "eligible": eligible, "selected": improved, "step_255": step_size,
                              "backtracks": backtracks, "update_accepted": accepted})
            if improved:
                best, best_key = output.copy(), key
                best_info = {"restart": restart + 1, "step": step, "scores": list(values),
                             "initial_min_context_score": initial_min, "quality": quality,
                             "step_255": step_size, "backtracks": backtracks}
            if accepted and (restart_best is None or key > restart_best):
                restart_best, stale = key, 0
            else:
                stale += 1
                if stale >= 2:
                    step_size, stale = max(.05, step_size / 2), 0
    if not had_gradient: raise RiposteError("ZERO_GRADIENT_NO_CANDIDATE")
    if best is None: raise RiposteError("NO_IMPROVED_FIDELITY_ACCEPTABLE_CANDIDATE")
    notify("Auditing selected final pixels", config.restarts - 1, config.steps)
    quality = quality_report(image, best, limits, artist_mask)
    if quality["status"] != "PASS": raise RiposteError("FINAL_QUALITY_AUDIT_FAILED")
    rows = [{"kind": b.kind, "view": b.view, "mask": b.mask, "model": b.index + 1,
             "mask_seed": b.seed, "score": value}
            for b, value in zip(branches, best_info.pop("scores"), strict=True)]
    return best, {"engine": "release-v1", "method": "RIPOSTE constrained publication guard / experimental",
                  "ai_protection": "UNVERIFIED", "evidence_level": "TEMPORAL_AND_IMAGE_COMPONENT_PROXY" if temporal else "IMAGE_COMPONENT_PROXY",
                  "config": asdict(config), "quality": quality, "selection": {k: v for k, v in best_info.items() if k != "quality"},
                  "trace": trace, "contexts": rows, "optimization_views": list(TRAIN_VIEWS),
                  "search_policy": {"selection": "EVERY_ACCEPTED_ITERATE", "quality_backtracks": 8,
                                    "minimum_step_255": .05, "checkpoint_every": "TRACE_ONLY",
                                    "gradient": "SHARED_VIEW_STREAMED_VJP", "unique_views": len(set(names))},
                  "optimization_masks": ["whole", "center", "left"], "selection_is_heldout": False,
                  "models": [getattr(e, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"}) for e in encoders],
                  "probe_model": getattr(probe, "identity", None), "temporal_model": getattr(temporal, "identity", None),
                  "jpeg_forward": "PILLOW_REAL_420", "jpeg_backward": "DCT_444_STE_APPROXIMATION",
                  "limits": "Best feasible model-component proxy, not verified editing/video/recognition resistance. Temporal branch is image-conditioned, not text-guided."}
