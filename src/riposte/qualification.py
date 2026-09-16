"""Scoped encoder qualification with true-codec views and matched controls.

This records the experiment that ran. It cannot convert surrogate measurements
into a security certificate, even when all the control comparisons are positive.
"""
from __future__ import annotations
import json
import math
import uuid
from pathlib import Path
from PIL import Image
from .errors import RiposteError
from .metrics import fidelity
from .sanitize import encode_clean, png_audit
from .store import safe_child, state_relative, workspace_lock, atomic_clean_write
from .views import TRAIN_VIEWS, HOLDOUT_VIEWS, publication_view, image_tensor, keep_mask, matched_control

CONTROL_SEEDS = (101, 211, 307)
EVAL_MASKS = ("whole", "right", "bottom")


def evaluate_pair(clean: Image.Image, candidate: Image.Image, encoders: list,
                  training_identities: list | None = None, control_seeds=CONTROL_SEEDS,
                  progress=None, optimization_views: list | None = None,
                  optimization_masks: list | None = None) -> dict:
    try:
        import torch
    except ImportError:
        raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
    if not encoders:
        raise RiposteError("NO_MODEL_NO_QUALIFICATION")
    if clean.size != candidate.size or min(clean.size) < 16:
        raise RiposteError("QUALIFICATION_DIMENSIONS_INVALID")
    if (not 2 <= len(control_seeds) <= 8 or len(set(control_seeds)) != len(control_seeds)
        or not all(isinstance(seed, int) and 0 <= seed < 2**32 for seed in control_seeds)):
        raise RiposteError("CONTROL_SEEDS_INVALID")
    inputs = {"clean": clean, "candidate": candidate}
    inputs.update({f"control_{i+1}": matched_control(clean, candidate, seed) for i, seed in enumerate(control_seeds)})
    control_fidelity = [fidelity(clean, inputs[f"control_{i+1}"]) for i in range(len(control_seeds))]
    original_quality = fidelity(clean, candidate)
    if any(row["rmse_255"] != original_quality["rmse_255"] or
           row["max_channel_delta_255"] != original_quality["max_channel_delta_255"] for row in control_fidelity):
        raise RiposteError("CONTROL_MATCH_FAILED")
    # External candidates have no known optimization protocol. Never call a
    # transform "held out" merely because it differs from RIPOSTE's defaults.
    known_views = set(optimization_views) if optimization_views is not None else None
    known_masks = set(optimization_masks) if optimization_masks is not None else None
    training_weights = {identity.get("weights_sha256") for identity in (training_identities or [])
                        if identity.get("weights_sha256")}
    views = TRAIN_VIEWS + HOLDOUT_VIEWS
    total = len(encoders) * len(views) * len(EVAL_MASKS)
    rows, models = [], []
    with torch.no_grad():
        for model_number, model in enumerate(encoders, 1):
            identity = getattr(model, "identity", {"kind": "UNIDENTIFIED_LOCAL_ORACLE"})
            fingerprint = identity.get("weights_sha256")
            relation = ("SAME_OPTIMIZATION_WEIGHTS" if fingerprint in training_weights else
                        "DIFFERENT_WEIGHTS_ARCHITECTURE_NOT_ESTABLISHED" if fingerprint and training_weights else
                        "RELATION_NOT_ESTABLISHED")
            models.append({**identity, "relation_to_optimization": relation})
            device = getattr(model, "device", "cpu")
            for view in views:
                tensors = {role: image_tensor(publication_view(image, view), device) for role, image in inputs.items()}
                for mask_kind in EVAL_MASKS:
                    if progress:
                        progress({"phase": "Challenging candidate against matched controls", "processed": len(rows), "total": total})
                    keep = keep_mask(tensors["clean"].shape[-2:], mask_kind, seed=2027, device=device)
                    features = {}
                    for role, tensor in tensors.items():
                        z = model(tensor * keep + .5 * (1 - keep)).detach()
                        if not bool(torch.isfinite(z).all()):
                            raise RiposteError("QUALIFICATION_NONFINITE")
                        features[role] = z.cpu()
                    base = features.pop("clean")
                    norm = max(float(base.square().mean()), 1e-6)
                    scores = {role: float((z - base).square().mean()) / norm for role, z in features.items()}
                    if not all(math.isfinite(value) for value in scores.values()):
                        raise RiposteError("QUALIFICATION_NONFINITE")
                    controls = [scores[f"control_{i+1}"] for i in range(len(control_seeds))]
                    strongest = max(controls)
                    margin = scores["candidate"] - strongest
                    tolerance = max(1e-10, strongest * 1e-6)
                    rows.append({"model": model_number, "view": view, "mask": mask_kind,
                                 "view_scope": ("OPTIMIZATION_PROTOCOL_UNKNOWN" if known_views is None else
                                                "OPTIMIZATION_VIEW_FAMILY" if view in known_views else "HELD_OUT_TRANSFORM"),
                                 "mask_scope": ("UNMASKED" if mask_kind == "whole" else
                                                "OPTIMIZATION_PROTOCOL_UNKNOWN" if known_masks is None else
                                                "OPTIMIZATION_MASK_FAMILY" if mask_kind in known_masks else "HELD_OUT_MASK_FAMILY"),
                                 "candidate_shift": scores["candidate"], "control_shifts": controls,
                                 "strongest_control": strongest, "margin_above_control": margin,
                                 "above_all_controls": margin > tolerance,
                                 "ratio_to_strongest_control": scores["candidate"] / strongest if strongest > 0 else None})
    heldout = [row for row in rows if row["view_scope"] == "HELD_OUT_TRANSFORM"]
    signal = sum(row["above_all_controls"] for row in heldout)
    all_signal = sum(row["above_all_controls"] for row in rows)
    return {"mode": "ENCODER_QUALIFICATION", "evidence_level": "CONTROLLED_ENCODER_PROXY",
            "ai_protection": "UNVERIFIED", "status": ("PROTOCOL_UNKNOWN_SCOPED_COMPARISON" if known_views is None else
                "PROXY_SIGNAL_OBSERVED" if signal else "NO_HELDOUT_PROXY_ADVANTAGE"),
            "optimization_protocol": {"views_known": known_views is not None, "masks_known": known_masks is not None},
            "models": models, "control": {"kind": "FEASIBLE_SIGN_SCRAMBLED_MATCHED_MAGNITUDE",
            "seeds": list(control_seeds), "per_channel_magnitude_matched": True, "fidelity": control_fidelity},
            "input_fidelity": original_quality, "rows": rows,
            "summary": {"cells": len(rows), "cells_above_all_controls": all_signal, "heldout_transform_cells": len(heldout),
                        "heldout_cells_above_all_controls": signal},
            "limits": "No actual edits or videos were scored. Larger encoder shifts do not prove copying failed. Different weights do not prove an unseen model family."}


def _verified_pair(root: Path, trial: str):
    from .lab import trial_report
    report = trial_report(root, trial)
    images = {}
    for role in ("clean", "candidate"):
        path = safe_child(root, state_relative(root, f"lab/{trial}/{role}.png"))
        audit = png_audit(path.read_bytes())
        if audit["sha256"] != report["artifact_sha256"][role] or audit["date"] != report["date"]:
            raise RiposteError("TRIAL_ARTIFACT_CHANGED")
        with Image.open(path) as image:
            images[role] = image.convert("RGB")
    return report, images


def qualify_trial(root: Path, trial_id: str, vae_dirs: list[Path], device: str = "auto", progress=None) -> dict:
    from .models import LocalEncoder
    from .organizer import audit_workspace
    if not vae_dirs or len(vae_dirs) > 4:
        raise RiposteError("NO_MODEL_NO_QUALIFICATION")
    with workspace_lock(root):
        if audit_workspace(root)["checkpoint"] != "COMPLETE":
            raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")
        report, images = _verified_pair(root, trial_id)
        encoders = [LocalEncoder(path, device) for path in vae_dirs]
        result = evaluate_pair(images["clean"], images["candidate"], encoders, report.get("models", []), progress=progress,
                               optimization_views=report.get("optimization_views"), optimization_masks=report.get("optimization_masks"))
        if progress:
            progress({"phase": "Committing scoped qualification", "processed": 1, "total": 1})
        result.update({"id": uuid.uuid4().hex, "trial_id": trial_id, "date": report["date"],
                       "candidate_sha256": report["artifact_sha256"]["candidate"],
                       "sequence": max((item.get("sequence", 0) for item in evaluations(root, trial_id)), default=0) + 1})
        prefix = state_relative(root, f"lab/{trial_id}/evaluations/{result['id']}")
        # Artifacts are already clean. Report is the final commit marker.
        try:
            for i, seed in enumerate(CONTROL_SEEDS, 1):
                atomic_clean_write(root, f"{prefix}/control-{i}.png",
                                   encode_clean(matched_control(images["clean"], images["candidate"], seed), report["date"]))
            from .store import atomic_json_write
            atomic_json_write(root, f"{prefix}/report.json", result)
        except Exception:
            import shutil
            dest = safe_child(root, prefix)
            if dest.exists():
                shutil.rmtree(dest)
            raise
        return result


def evaluations(root: Path, trial_id: str) -> list[dict]:
    from .lab import trial_report
    import re
    report = trial_report(root, trial_id)
    parent = safe_child(root, state_relative(root, f"lab/{trial_id}/evaluations"))
    if not parent.exists():
        return []
    result = []
    for entry in sorted(parent.iterdir()):
        if re.fullmatch(r"[0-9a-f]{32}", entry.name):
            path = safe_child(root, state_relative(root, f"lab/{trial_id}/evaluations/{entry.name}/report.json"))
            try:
                value = json.loads(path.read_text())
                if value.get("trial_id") == trial_id and value.get("candidate_sha256") == report["artifact_sha256"]["candidate"]:
                    result.append(value)
            except (OSError, ValueError):
                pass
    return sorted(result, key=lambda item: (item.get("sequence", 0), item["id"]))
