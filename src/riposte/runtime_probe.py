"""Execute a selected local model and input gradient. Never download weights."""
from __future__ import annotations
import time
from .errors import RiposteError

def _probe_gradient(model, forward, objective) -> dict:
    import torch
    device = getattr(model, "device", "cpu")
    x = torch.linspace(.1, .9, 3 * 64 * 64, device=device).reshape(1, 3, 64, 64).requires_grad_(True)
    started = time.perf_counter()
    try:
        y = forward(x)
        if not bool(torch.isfinite(y).all()) or not y.requires_grad:
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        loss = objective(y)
        if not bool(torch.isfinite(loss)) or not loss.requires_grad:
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        g = torch.autograd.grad(loss, x, allow_unused=True)[0]
        if g is None or not bool(torch.isfinite(g).all()) or not bool((g != 0).any()):
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        if device == "cuda": torch.cuda.synchronize()
        return {"status": "FORWARD_AND_INPUT_GRADIENT_EXECUTED", "input_shape": list(x.shape),
                "feature_shape": list(y.shape), "elapsed_seconds": round(time.perf_counter() - started, 6),
                "finite_gradient": True, "nonzero_gradient": True,
                "model": getattr(model, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"}),
                "device": device, "ai_protection": "UNVERIFIED"}
    except RiposteError: raise
    except Exception: raise RiposteError("MODEL_EXECUTION_PROBE_FAILED") from None


def probe_encoder(encoder) -> dict:
    return _probe_gradient(encoder, encoder, lambda y: y.square().mean())


def probe_inpaint(probe) -> dict:
    from .views import keep_mask
    contexts = []
    for mask, fraction, prompt in (("center", .9, "background"), ("left", .98, "material")):
        def forward(x):
            keep = keep_mask(x.shape[-2:], mask, 7, x.device)
            return probe(x, keep, 7, fraction, prompt)
        contexts.append({**_probe_gradient(probe, forward, lambda y: y.square().mean()),
                         "mask": mask, "early_fraction": fraction, "prompt": prompt})
    return {"kind": "INPAINT_INPUT_GRADIENT", "contexts": contexts, "ai_protection": "UNVERIFIED"}


def probe_temporal(probe) -> dict:
    from .release_guard import temporal_energy
    def objective(y):
        energy = temporal_energy(y)
        if float(energy.detach().cpu()) <= 1e-12:
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        return energy
    return {**_probe_gradient(probe, lambda x: probe(x, 7), objective),
            "kind": "TEMPORAL_ENERGY_INPUT_GRADIENT"}

def execute_local_probe(vae_dirs, device="auto", progress=None) -> dict:
    from .models import LocalEncoder, runtime_capabilities
    if not 1 <= len(vae_dirs) <= 4: raise RiposteError("NO_MODEL_NO_PROTECTION")
    rows = []
    for i, path in enumerate(vae_dirs):
        if progress: progress({"phase": "Executing model and input gradient", "processed": i, "total": len(vae_dirs)})
        encoder = LocalEncoder(path, device)
        rows.append(probe_encoder(encoder))
        del encoder
    return {"mode": "LOCAL_MODEL_EXECUTION", "models": rows, "runtime": runtime_capabilities(),
            "evidence_level": "EXECUTION_ONLY", "ai_protection": "UNVERIFIED"}
