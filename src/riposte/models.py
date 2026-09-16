"""Local model capability checks and fixed-class adapters; no hub or remote code.

Only allowlisted technical fields leave this module. Resource paths and arbitrary
model-config strings are deliberately absent from diagnostics and trial records.
"""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path

from .errors import RiposteError
from .policy import is_link

VAE_CLASSES = {"AutoencoderKL", "AutoencoderTiny"}
DEPENDENCIES = ("torch", "diffusers", "transformers", "safetensors", "accelerate")


def offline() -> None:
    for name in ("HF_HUB_OFFLINE", "HF_HUB_DISABLE_TELEMETRY", "TRANSFORMERS_OFFLINE"):
        os.environ[name] = "1"


def read_config(path: Path) -> dict:
    try:
        if not path.is_file() or is_link(path) or path.stat().st_size > 1_048_576:
            raise RiposteError("MODEL_CONFIG_INVALID")
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise RiposteError("MODEL_CONFIG_INVALID")
        return data
    except (ValueError, OSError):
        raise RiposteError("MODEL_CONFIG_INVALID") from None


def _weights(folder: Path) -> list[Path]:
    if not folder.is_dir() or is_link(folder) or any(is_link(p) for p in folder.parents):
        raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
    weights = sorted(folder.glob("*.safetensors"))
    if not weights or any(is_link(p) or p.stat().st_size == 0 for p in weights):
        raise RiposteError("SAFETENSORS_REQUIRED")
    for index in folder.glob("*.safetensors.index.json"):
        mapping = read_config(index).get("weight_map", {})
        if not isinstance(mapping, dict) or not mapping:
            raise RiposteError("MODEL_INDEX_INVALID")
        for value in mapping.values():
            if not isinstance(value, str) or Path(value).name != value or "\\" in value or value not in {p.name for p in weights}:
                raise RiposteError("MODEL_INDEX_INVALID")
    return weights


def model_fingerprint(folder: Path) -> str:
    """Hash only explicitly selected model weights, never input-image bytes."""
    digest = hashlib.sha256()
    for path in _weights(folder):
        part = hashlib.sha256()
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1 << 20), b""):
                part.update(block)
        digest.update(part.digest())
    return digest.hexdigest()


def inspect_vae(folder: Path, fingerprint: bool = False) -> dict:
    if not folder.is_dir() or not (folder / "config.json").is_file():
        raise RiposteError("LOCAL_VAE_DIRECTORY_REQUIRED")
    config = read_config(folder / "config.json")
    kind = config.get("_class_name")
    if kind not in VAE_CLASSES:
        raise RiposteError("VAE_ARCHITECTURE_UNSUPPORTED")
    weights = _weights(folder)
    result = {"kind": kind, "weights_format": "safetensors", "weight_files": len(weights),
              "weight_bytes": sum(p.stat().st_size for p in weights),
              "scope": "DISTILLED_ENCODER_PROXY" if kind == "AutoencoderTiny" else "ENCODER_PROXY",
              "preflight": "FILES_PRESENT_NOT_EXECUTED", "ai_protection": "UNVERIFIED"}
    if fingerprint:
        result["weights_sha256"] = model_fingerprint(folder)
    return result


def runtime_capabilities() -> dict:
    versions, missing = {}, []
    for name in DEPENDENCIES:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            missing.append(name)
    result = {"versions": versions, "missing": missing, "cpu": True, "cuda": False, "mps": False,
              "recommended_device": "cpu", "model_loading": "EXPLICIT_LOCAL_ONLY",
              "privacy": "NO_IMAGE_UPLOADS", "pretrained_qualification": "NOT_IMPLIED_BY_PREFLIGHT"}
    try:
        import torch
        result["cuda"] = bool(torch.cuda.is_available())
        result["mps"] = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
        result["recommended_device"] = "cuda" if result["cuda"] else "mps" if result["mps"] else "cpu"
        if result["cuda"]:
            free, total = torch.cuda.mem_get_info()
            result["cuda_memory_mib"] = {"free": free // (1024**2), "total": total // (1024**2)}
    except Exception:
        result["runtime_code"] = "TORCH_UNAVAILABLE_OR_UNUSABLE"
    return result


def select_device(requested: str = "auto") -> str:
    try:
        import torch
    except ImportError:
        raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
    if requested not in {"auto", "cpu", "cuda", "mps"}:
        raise RiposteError("DEVICE_INVALID")
    cuda = torch.cuda.is_available()
    mps = hasattr(torch.backends, "mps") and torch.backends.mps.is_available()
    device = ("cuda" if cuda else "mps" if mps else "cpu") if requested == "auto" else requested
    if (device == "cuda" and not cuda) or (device == "mps" and not mps):
        raise RiposteError("DEVICE_UNAVAILABLE")
    return device


class LocalEncoder:
    """A fixed, local AutoencoderKL or AutoencoderTiny; no implicit conversion."""
    def __init__(self, folder: Path, device: str = "auto"):
        offline()
        try:
            import torch
            from diffusers import AutoencoderKL, AutoencoderTiny
        except ImportError:
            raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
        self.identity = inspect_vae(folder, fingerprint=True)
        self.device = select_device(device)
        self.kind = self.identity["kind"]
        cls = AutoencoderKL if self.kind == "AutoencoderKL" else AutoencoderTiny
        try:
            self.model = cls.from_pretrained(str(folder), local_files_only=True, use_safetensors=True,
                                            torch_dtype=torch.float32).to(self.device).eval()
            self.model.requires_grad_(False)
            channels = (self.model.config.block_out_channels if self.kind == "AutoencoderKL"
                        else self.model.config.encoder_block_out_channels)
            self.factor = 2 ** (len(channels) - 1)
        except Exception:
            raise RiposteError("LOCAL_VAE_LOAD_FAILED") from None

    def __call__(self, x):
        import torch.nn.functional as F
        h, w = x.shape[-2:]
        padded = F.pad(x, (0, (-w) % self.factor, 0, (-h) % self.factor), mode="replicate")
        output = self.model.encode(padded * 2 - 1)
        return output.latent_dist.mean if self.kind == "AutoencoderKL" else output.latents


PROMPTS = {
    "background": "a detailed illustration with a textured background",
    "material": "an illustration rendered in sculpted clay, clear subject and composition",
}


class LocalInpaintProbe:
    """Early *conditioning* probe for standard 9-channel SD inpainting UNets.

    Shared noise, mask, timestep and prompt isolate changes in the image
    conditioning. It is not a generated-edit score, a video objective, or an
    implementation claimed to reproduce DiffusionGuard.
    """
    def __init__(self, folder: Path, device: str = "auto"):
        offline()
        try:
            import torch
            from diffusers import AutoencoderKL, UNet2DConditionModel, DDIMScheduler
            from transformers import CLIPTextModel, CLIPTokenizer
        except ImportError:
            raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
        self.device = select_device(device)
        if not folder.is_dir() or not (folder / "model_index.json").is_file():
            raise RiposteError("LOCAL_INPAINT_PIPELINE_REQUIRED")
        for part in (folder, folder / "tokenizer", folder / "scheduler"):
            if is_link(part) or any(is_link(parent) for parent in part.parents):
                raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
        for part in ("tokenizer", "scheduler"):
            for item in (folder / part).rglob("*"):
                if is_link(item):
                    raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
        index = read_config(folder / "model_index.json")
        if index.get("_class_name") != "StableDiffusionInpaintPipeline":
            raise RiposteError("INPAINT_ARCHITECTURE_UNSUPPORTED")
        expected = {"vae": ["diffusers", "AutoencoderKL"], "unet": ["diffusers", "UNet2DConditionModel"],
                    "text_encoder": ["transformers", "CLIPTextModel"], "tokenizer": ["transformers", "CLIPTokenizer"]}
        if any(index.get(k) != v for k, v in expected.items()):
            raise RiposteError("INPAINT_COMPONENTS_UNSUPPORTED")
        unet_config = read_config(folder / "unet/config.json")
        if unet_config.get("in_channels") != 9 or unet_config.get("addition_embed_type") is not None:
            raise RiposteError("INPAINT_NINE_CHANNEL_REQUIRED")
        fingerprints = {part: model_fingerprint(folder / part) for part in ("vae", "unet", "text_encoder")}
        try:
            load = {"local_files_only": True, "use_safetensors": True, "torch_dtype": torch.float32}
            self.vae = AutoencoderKL.from_pretrained(str(folder / "vae"), **load).to(self.device).eval()
            self.unet = UNet2DConditionModel.from_pretrained(str(folder / "unet"), **load).to(self.device).eval()
            encoder = CLIPTextModel.from_pretrained(str(folder / "text_encoder"), **load).to(self.device).eval()
            tokenizer = CLIPTokenizer.from_pretrained(str(folder / "tokenizer"), local_files_only=True)
            self.scheduler = DDIMScheduler.from_pretrained(str(folder / "scheduler"), local_files_only=True)
            for model in (self.vae, self.unet, encoder):
                model.requires_grad_(False)
            self.embeddings = {}
            with torch.no_grad():
                for name, prompt in PROMPTS.items():
                    tokens = tokenizer(prompt, padding="max_length", max_length=tokenizer.model_max_length,
                                       truncation=True, return_tensors="pt")
                    self.embeddings[name] = encoder(tokens.input_ids.to(self.device))[0].detach()
            del encoder
            self.factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
            self.scaling = float(self.vae.config.scaling_factor)
            self.timesteps = int(self.scheduler.config.num_train_timesteps)
        except Exception:
            raise RiposteError("LOCAL_INPAINT_LOAD_FAILED") from None
        self.identity = {"kind": "SD_9CHANNEL_EARLY_CONDITIONING", "component_sha256": fingerprints,
                         "scope": "EARLY_DENOISER_PROXY", "ai_protection": "UNVERIFIED"}

    def __call__(self, x, keep, seed: int, early_fraction: float, prompt_key: str):
        import torch
        import torch.nn.functional as F
        if prompt_key not in self.embeddings or not .5 <= early_fraction < 1:
            raise RiposteError("PROBE_CONTEXT_INVALID")
        h, w = x.shape[-2:]
        padding = (0, (-w) % self.factor, 0, (-h) % self.factor)
        masked = F.pad((x * 2 - 1) * keep, padding, mode="replicate")
        z = self.vae.encode(masked).latent_dist.mean * self.scaling
        edit = F.interpolate(F.pad(1 - keep, padding, mode="replicate"), size=z.shape[-2:], mode="nearest")
        # CPU RNG avoids global RNG state and works for CUDA, MPS and CPU.
        noise = torch.randn(z.shape, generator=torch.Generator("cpu").manual_seed(seed), dtype=z.dtype).to(z.device)
        timestep = torch.tensor(int(early_fraction * (self.timesteps - 1)), device=z.device, dtype=torch.long)
        model_input = torch.cat((noise, edit, z), dim=1)
        return self.unet(model_input, timestep, encoder_hidden_states=self.embeddings[prompt_key]).sample
