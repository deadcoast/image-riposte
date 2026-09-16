"""Optional paired generation runner. A runner, not a calibrated success scorer.

SD img2img and SVD are reference baselines, NOT a claim of modern-model coverage.
Model integration is source-inspected and unit tested; full-weight GPU runs are
required before claiming generation-level efficacy.
"""
from __future__ import annotations
import json
import uuid
from pathlib import Path
from PIL import Image
from .errors import RiposteError
from .lab import trial_report
from .metrics import transform, fidelity
from .sanitize import encode_clean, social_render, png_audit
from .store import workspace_lock, safe_child, atomic_clean_write, state_relative

PROMPTS=("Preserve the main illustration and add a patterned background.",
         "Animate this illustration with a gentle camera movement.")

def run_benchmark(root: Path, trial_id: str, model_dir: Path, task: str = "edit", seeds: tuple[int,...]=(7,19),
                  transforms: tuple[str,...] = ("identity","jpeg85","resize75"), steps: int = 25) -> dict:
    import os
    for name in ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "TRANSFORMERS_OFFLINE"):
        os.environ[name] = "1"
    try:
        import torch
        from diffusers import StableDiffusionImg2ImgPipeline, StableVideoDiffusionPipeline
    except ImportError:
        raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
    if task not in {"edit","video"} or not model_dir.is_dir() or not (model_dir/"model_index.json").is_file():
        raise RiposteError("LOCAL_PIPELINE_REQUIRED")
    if not torch.cuda.is_available():
        raise RiposteError("GENERATION_BENCHMARK_REQUIRES_CUDA")
    if not seeds or len(seeds)>16 or not all(0<=s<2**32 for s in seeds) or not 1<=steps<=100:
        raise RiposteError("BENCHMARK_PARAMETERS_INVALID")
    with workspace_lock(root):
        from .organizer import audit_workspace
        if audit_workspace(root)["checkpoint"] != "COMPLETE":
            raise RiposteError("ORGANIZATION_CHECKPOINT_REQUIRED")
        report=trial_report(root,trial_id)
        for role in ("clean","candidate"):
            checked=png_audit(safe_child(root,state_relative(root, f"lab/{trial_id}/{role}.png")).read_bytes())
            if checked["sha256"] != report["artifact_sha256"][role] or checked["date"] != report["date"]:
                raise RiposteError("TRIAL_ARTIFACT_CHANGED")
        try:
            cls=StableDiffusionImg2ImgPipeline if task=="edit" else StableVideoDiffusionPipeline
            pipe=cls.from_pretrained(str(model_dir),local_files_only=True,use_safetensors=True,torch_dtype=torch.float16).to("cuda")
            pipe.set_progress_bar_config(disable=True)
        except Exception:
            raise RiposteError("LOCAL_PIPELINE_LOAD_FAILED") from None
        inputs={}
        for name in ("clean","candidate"):
            with Image.open(safe_child(root,state_relative(root, f"lab/{trial_id}/{name}.png"))) as im:
                inputs[name]=im.convert("RGB")
        benchmark=uuid.uuid4().hex
        prefix=state_relative(root, f"benchmarks/{benchmark}")
        pairs=[]
        for ti,tx in enumerate(transforms):
            for si,seed in enumerate(seeds):
                outputs={}
                for role,image in inputs.items():
                    image=transform(image,tx)
                    # SVD reference pipeline has a fixed evaluation raster.
                    if task=="video":
                        from PIL import ImageOps
                        image=ImageOps.pad(image,(1024,576),color="white")
                    else:
                        image=social_render(image,768)
                        w,h=image.size
                        image=image.resize((max(8,w//8*8),max(8,h//8*8)),Image.Resampling.LANCZOS)
                    generator=torch.Generator("cuda").manual_seed(seed)
                    with torch.inference_mode():
                        if task=="edit":
                            frames=pipe(prompt=PROMPTS[0],image=image,strength=.65,guidance_scale=7.5,
                                num_inference_steps=steps,generator=generator).images
                        else:
                            frames=pipe(image,num_frames=14,num_inference_steps=steps,
                                decode_chunk_size=2,generator=generator).frames[0]
                    outputs[role]=frames
                    for fi,frame in enumerate(frames):
                        atomic_clean_write(root,f"{prefix}/T{ti:02d}-S{si:02d}-{role}/F{fi:03d}.png",encode_clean(frame,report["date"]))
                pair={"transform":tx,"seed":seed,"frames":len(outputs["clean"]),
                      "paired_output_pixel_metrics":[fidelity(a,b) for a,b in zip(outputs["clean"],outputs["candidate"],strict=True)],
                      "success_judgment":"HUMAN_REVIEW_REQUIRED"}
                pairs.append(pair)
        summary={"id":benchmark,"trial_id":trial_id,"task":task,"seeds":list(seeds),"steps":steps,
            "evidence_level":"PAIRED_GENERATIONS_UNSCORED","ai_protection":"UNVERIFIED",
            "pairs":pairs,"model_family":"SD-img2img" if task=="edit" else "SVD-i2v",
            "limits":"Output differences alone do not establish attack failure. Review task success, source preservation and quality against matched clean controls."}
        safe_child(root,f"{prefix}/report.json").write_text(json.dumps(summary,indent=2,allow_nan=False))
        return summary
