from __future__ import annotations
import io
import json
import re
import uuid
from pathlib import Path
from PIL import Image
from .errors import RiposteError
from .metrics import transport_report, fidelity, difference_image
from .sanitize import decode_clean, encode_clean, social_render, png_audit
from .policy import Policy
from .store import workspace_lock, find_image, safe_child, atomic_clean_write, check_root, state_relative

METHODS = {"external", "glaze", "nightshade", "photoguard", "mist", "diffusionguard", "dct-shield", "i2vguard"}

def _master(root: Path, identifier: str):
    from .organizer import audit_workspace
    if audit_workspace(root)["checkpoint"] != "COMPLETE":
        raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")
    row = find_image(root, identifier)
    with Image.open(safe_child(root, row["relative"])) as im:
        pixels = im.copy()
    return row, pixels

def _store_trial(root: Path, row: dict, clean: Image.Image, candidate: Image.Image, report: dict) -> dict:
    trial = uuid.uuid4().hex
    prefix = state_relative(root, f"lab/{trial}")
    hashes = {}
    sequence = max((item.get("sequence", 0) for item in trials(root)), default=0) + 1
    try:
        for name, image in (("clean", clean), ("candidate", candidate), ("difference", difference_image(clean, candidate))):
            data = encode_clean(image, row["day"])
            hashes[name] = png_audit(data)["sha256"]
            atomic_clean_write(root, f"{prefix}/{name}.png", data)
        # Identity and commit fields are not overridable by method diagnostics.
        report = {**report, "id": trial, "sequence": sequence, "image_id": row["id"], "date": row["day"],
                  "width": clean.width, "height": clean.height, "source_clean_sha256": row["sha256"],
                  "artifact_sha256": hashes, "fidelity": fidelity(clean, candidate),
                  "transport": transport_report(clean, candidate)}
        from .store import atomic_json_write
        atomic_json_write(root, f"{prefix}/report.json", report)
    except Exception:
        import shutil
        folder = safe_child(root, prefix)
        if folder.exists():
            shutil.rmtree(folder)
        raise
    return report

def compare_external(root: Path, identifier: str, candidate_path: Path, max_edge: int = 1536, method: str = "external") -> dict:
    if method not in METHODS:
        raise RiposteError("METHOD_INVALID")
    with workspace_lock(root):
        row, master = _master(root, identifier)
        clean = social_render(master,max_edge)
        # External path remains external. Raw bytes/filename are never imported.
        candidate = decode_clean(candidate_path,Policy()).pixels
        if candidate.size != clean.size:
            raise RiposteError("CANDIDATE_SIZE_MISMATCH")
        candidate = social_render(candidate,max_edge)
        return _store_trial(root,row,clean,candidate,{"method":method,"evidence_level":"PIXEL_TRANSPORT_ONLY",
            "ai_protection":"UNVERIFIED", "external_source":"Not copied into workspace; original outside workspace is unchanged."})

def create_candidate(root: Path, identifier: str, vae_dirs: list[Path], max_edge: int = 1536,
                     epsilon: int = 4, steps: int = 48, seed: int = 7, progress=None,
                     engine: str = "encoder", pipeline_dir: Path | None = None,
                     device: str = "auto", preserve_white: bool = True) -> dict:
    from .optimizer import GuardConfig, protect
    from .models import LocalEncoder, LocalInpaintProbe
    from .coupled import CoupledConfig, protect_coupled
    if not vae_dirs or len(vae_dirs) > 4:
        raise RiposteError("NO_MODEL_NO_PROTECTION")
    if engine not in {"encoder", "coupled"} or (pipeline_dir and engine != "coupled"):
        raise RiposteError("GUARD_ENGINE_INVALID")
    with workspace_lock(root):
        row, master = _master(root, identifier)
        clean = social_render(master, max_edge)
        if progress:
            progress({"phase": "Loading explicitly selected local models", "processed": 0, "total": steps})
        encoders = [LocalEncoder(path, device) for path in vae_dirs]
        if engine == "coupled":
            probe = LocalInpaintProbe(pipeline_dir, encoders[0].device) if pipeline_dir else None
            candidate, report = protect_coupled(clean, encoders,
                CoupledConfig(epsilon_255=epsilon, steps=steps, seed=seed, preserve_white=preserve_white),
                probe=probe, progress=progress)
        else:
            candidate, report = protect(clean, encoders,
                GuardConfig(epsilon_255=epsilon, steps=steps, seed=seed, preserve_white=preserve_white), progress)
            report.update({"engine": "encoder", "models": [e.identity for e in encoders],
                           "optimization_views": ["identity", "jpeg85", "resize75", "crop90"],
                           "optimization_masks": ["whole"]})
        if progress:
            progress({"phase": "Committing clean candidate artifacts", "processed": steps, "total": steps})
        return _store_trial(root, row, clean, candidate, report)

def trial_report(root: Path, identifier: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}",identifier):
        raise RiposteError("TRIAL_NOT_FOUND")
    path = safe_child(root,state_relative(root, f"lab/{identifier}/report.json"))
    try:
        return json.loads(path.read_text())
    except (ValueError,OSError):
        raise RiposteError("TRIAL_NOT_FOUND") from None

def trials(root: Path) -> list[dict]:
    check_root(root)
    folder = safe_child(root,state_relative(root, "lab"))
    if not folder.exists():
        return []
    result=[]
    for path in sorted(folder.iterdir(),reverse=True):
        if re.fullmatch(r"[0-9a-f]{32}",path.name):
            try:
                result.append(trial_report(root,path.name))
            except RiposteError:
                pass
    return sorted(result, key=lambda item: (item.get("sequence", 0), item["id"]), reverse=True)

def export_candidate(root: Path, identifier: str, acknowledge_unverified: bool = False) -> dict:
    if not acknowledge_unverified:
        raise RiposteError("ACKNOWLEDGE_UNVERIFIED_REQUIRED")
    with workspace_lock(root):
        report = trial_report(root,identifier)
        data = safe_child(root,state_relative(root, f"lab/{identifier}/candidate.png")).read_bytes()
        result = png_audit(data)
        if result["sha256"] != report["artifact_sha256"]["candidate"]:
            raise RiposteError("CANDIDATE_CHANGED")
        if result["date"] != report["date"]:
            raise RiposteError("TRIAL_DATE_MISMATCH")
        from .organizer import audit_workspace
        if audit_workspace(root)["checkpoint"] != "COMPLETE":
            raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")
        relative = state_relative(root, f"exports/{identifier}/candidate.png")
        dest = safe_child(root,relative)
        if not dest.exists():
            atomic_clean_write(root,relative,data)
        elif png_audit(dest.read_bytes())["sha256"] != result["sha256"]:
            raise RiposteError("EXPORT_CHANGED")
        return {"relative":relative,"metadata":"DATE_ONLY","ai_protection":"UNVERIFIED"}


def trial_pixels(root: Path, identifier: str, kind: str, view: str = "identity") -> bytes:
    from .qualification import _verified_pair
    from .views import publication_view, TRAIN_VIEWS, HOLDOUT_VIEWS
    if kind not in {"clean", "candidate", "difference"}:
        raise RiposteError("TRIAL_IMAGE_INVALID")
    if view not in TRAIN_VIEWS + HOLDOUT_VIEWS + ("jpeg95", "crop90", "resize75-jpeg85"):
        raise RiposteError("PUBLICATION_VIEW_INVALID")
    report, pair = _verified_pair(root, identifier)
    from .metrics import transform
    fn = publication_view if view in TRAIN_VIEWS + HOLDOUT_VIEWS else transform
    a, b = fn(pair["clean"], view), fn(pair["candidate"], view)
    pixels = difference_image(a, b) if kind == "difference" else a if kind == "clean" else b
    return encode_clean(pixels, report["date"])
