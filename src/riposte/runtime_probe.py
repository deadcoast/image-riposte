"""Execute a selected local model and input gradient. Never download weights."""
from __future__ import annotations
import time
from .errors import RiposteError

def probe_encoder(encoder) -> dict:
    import torch
    device = getattr(encoder, "device", "cpu")
    x = torch.linspace(.1, .9, 3 * 64 * 64, device=device).reshape(1, 3, 64, 64).requires_grad_(True)
    started = time.perf_counter()
    try:
        y = encoder(x)
        if not bool(torch.isfinite(y).all()) or not y.requires_grad:
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        g = torch.autograd.grad(y.square().mean(), x, allow_unused=True)[0]
        if g is None or not bool(torch.isfinite(g).all()) or not bool((g != 0).any()):
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        if device == "cuda": torch.cuda.synchronize()
        return {"status": "FORWARD_AND_INPUT_GRADIENT_EXECUTED", "input_shape": list(x.shape),
                "feature_shape": list(y.shape), "elapsed_seconds": round(time.perf_counter() - started, 6),
                "finite_gradient": True, "nonzero_gradient": True,
                "model": getattr(encoder, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"}),
                "device": device, "ai_protection": "UNVERIFIED"}
    except RiposteError: raise
    except Exception: raise RiposteError("MODEL_EXECUTION_PROBE_FAILED") from None

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
