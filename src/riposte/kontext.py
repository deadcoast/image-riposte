"""Fixed local FLUX Kontext edit backend with explicit geometry and bundle identity."""
from __future__ import annotations

from collections.abc import Callable, Mapping
from fractions import Fraction
import hashlib
import json
from pathlib import Path
from typing import Protocol, cast

from PIL import Image

from .errors import RiposteError
from .models import _weights, offline, read_config
from .policy import is_link

KIND = "FLUX_KONTEXT_EDIT"
# Resolution data from Diffusers 0.40.0's documented Kontext implementation.
RESOLUTIONS = ((672, 1568), (688, 1504), (720, 1456), (752, 1392), (800, 1328),
               (832, 1248), (880, 1184), (944, 1104), (1024, 1024), (1104, 944),
               (1184, 880), (1248, 832), (1328, 800), (1392, 752), (1456, 720),
               (1504, 688), (1568, 672))
COMPONENTS = {
    "vae": ("diffusers", ("AutoencoderKL",)),
    "transformer": ("diffusers", ("FluxTransformer2DModel",)),
    "scheduler": ("diffusers", ("FlowMatchEulerDiscreteScheduler",)),
    "text_encoder": ("transformers", ("CLIPTextModel",)),
    "text_encoder_2": ("transformers", ("T5EncoderModel",)),
    "tokenizer": ("transformers", ("CLIPTokenizer", "CLIPTokenizerFast")),
    "tokenizer_2": ("transformers", ("T5Tokenizer", "T5TokenizerFast")),
}


def target_size(width: int, height: int) -> tuple[int, int]:
    """Exact nearest aspect ratio among fixed buckets, with a stable lexical tie."""
    if type(width) is not int or type(height) is not int or min(width, height) < 1:
        raise RiposteError("GENERATION_INPUT_INVALID")
    ratio = Fraction(width, height)
    return min(RESOLUTIONS, key=lambda size: (abs(ratio - Fraction(*size)), *size))


def prepare(image: Image.Image) -> Image.Image:
    return image.convert("RGB").resize(target_size(*image.size), Image.Resampling.LANCZOS)


def conditioning() -> dict[str, object]:
    return {"mask_family": None, "prompt": "Preserve the main illustration and add a patterned background.",
            "guidance_scale": 2.5, "true_cfg_scale": 1.0, "max_sequence_length": 512,
            "guidance_mode": "DISTILLED_EMBEDDING", "input_geometry": "NEAREST_ASPECT_KONTEXT_17_V1",
            "resolutions": [list(size) for size in RESOLUTIONS], "resampling": "LANCZOS",
            "auto_resize": False, "output_geometry": "PREPARED_INPUT", "max_area": "prepared_width*prepared_height"}


def bundle_identity(folder: Path) -> dict[str, object]:
    """Hash named local assets, including binary tokenizer data; no remote code."""
    if not folder.is_dir() or is_link(folder) or any(is_link(p) for p in folder.parents):
        raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
    config: Mapping[str, object] = read_config(folder / "model_index.json")
    if config.get("_class_name") != "FluxKontextPipeline":
        raise RiposteError("GENERATION_ARCHITECTURE_UNSUPPORTED")
    for name, (library, classes) in COMPONENTS.items():
        descriptor = config.get(name)
        if (not isinstance(descriptor, list) or len(descriptor) != 2
                or descriptor[0] != library or descriptor[1] not in classes):
            raise RiposteError("GENERATION_COMPONENTS_UNSUPPORTED")
    for name, value in config.items():
        if name in COMPONENTS or name.startswith("_"):
            continue
        if name in {"image_encoder", "feature_extractor"} and value == [None, None]:
            continue
        raise RiposteError("GENERATION_COMPONENTS_UNSUPPORTED")
    assets = {"model_index.json": hashlib.sha256((folder / "model_index.json").read_bytes()).hexdigest()}
    for name in COMPONENTS:
        directory = folder / name
        if not directory.is_dir() or is_link(directory):
            raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
        for path in sorted(directory.iterdir()):
            if is_link(path) or not path.is_file():
                raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
            # Local loading is fixed to safetensors. Alternative executable/weight
            # formats are outside this admitted bundle, even if not selected.
            if path.suffix.lower() in {".py", ".pyc", ".bin", ".pt", ".pth", ".ckpt"}:
                raise RiposteError("GENERATION_COMPONENTS_UNSUPPORTED")
            with path.open("rb") as stream:
                assets[path.relative_to(folder).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    weights = {}
    for name in ("vae", "transformer", "text_encoder", "text_encoder_2"):
        digest = hashlib.sha256()
        for path in _weights(folder / name):
            digest.update(bytes.fromhex(assets[path.relative_to(folder).as_posix()]))
        weights[name] = digest.hexdigest()
    vae: Mapping[str, object] = read_config(folder / "vae/config.json")
    transformer: Mapping[str, object] = read_config(folder / "transformer/config.json")
    channels = vae.get("block_out_channels")
    if (not isinstance(channels, list) or len(channels) != 4 or vae.get("latent_channels") != 16
            or transformer.get("in_channels") != 64 or transformer.get("guidance_embeds") is not True):
        raise RiposteError("KONTEXT_LATENT_LAYOUT_UNSUPPORTED")
    return {"kind": KIND, "bundle_sha256": hashlib.sha256(json.dumps(assets, sort_keys=True).encode()).hexdigest(),
            "bundle_algorithm": "NAMED_FLAT_COMPONENT_ASSETS_SHA256_V1", "asset_files": len(assets),
            "component_sha256": weights, "precision": "bfloat16", "device": "cuda",
            "weight_provenance": "NOT_ATTESTED_BY_ARCHITECTURE_OR_HASH"}


class _Pipeline(Protocol):
    def to(self, device: str) -> _Pipeline: ...
    def set_progress_bar_config(self, *, disable: bool) -> None: ...
    def __call__(self, **kwargs: object) -> object: ...


class KontextGenerator:
    def __init__(self, folder: Path) -> None:
        offline()
        try:
            import torch
            from diffusers import FluxKontextPipeline
        except ImportError:
            raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
        if not torch.cuda.is_available():
            raise RiposteError("GENERATION_BENCHMARK_REQUIRES_CUDA")
        if not torch.cuda.is_bf16_supported(including_emulation=False):
            raise RiposteError("KONTEXT_REQUIRES_NATIVE_BFLOAT16")
        identity = bundle_identity(folder)
        try:
            load = cast(Callable[..., object], FluxKontextPipeline.from_pretrained)
            self.pipeline = cast(_Pipeline, load(str(folder), local_files_only=True, use_safetensors=True,
                                                torch_dtype=torch.bfloat16)).to("cuda")
            self.pipeline.set_progress_bar_config(disable=True)
        except Exception:
            raise RiposteError("LOCAL_PIPELINE_LOAD_FAILED") from None
        if bundle_identity(folder) != identity:
            raise RiposteError("MODEL_BUNDLE_CHANGED")
        self.identity = identity
        self.last_flags: dict[str, object] = {"content_filter_reported": False, "content_filter_flags": None}

    def __call__(self, image: Image.Image, seed: int, steps: int) -> list[Image.Image]:
        import torch
        if (image.mode != "RGB" or any(d % 16 or d < 16 or d > 4096 for d in image.size)
                or type(seed) is not int or not 0 <= seed < 2**32 or type(steps) is not int or not 1 <= steps <= 100):
            raise RiposteError("GENERATION_PARAMETERS_INVALID")
        options = conditioning()
        with torch.inference_mode():
            result = self.pipeline(image=image, prompt=options["prompt"], guidance_scale=options["guidance_scale"],
                true_cfg_scale=options["true_cfg_scale"], max_sequence_length=options["max_sequence_length"],
                height=image.height, width=image.width, max_area=image.width*image.height, _auto_resize=False,
                num_inference_steps=steps, generator=torch.Generator("cuda").manual_seed(seed))
        frames: object = getattr(result, "images", None)
        if (not isinstance(frames, list) or len(frames) != 1
                or not isinstance(frames[0], Image.Image) or frames[0].size != image.size):
            raise RiposteError("GENERATION_OUTPUT_INVALID")
        return [frames[0]]
