"""Differentiable SVD first-step temporal-conditioning objective adapter.

Uses fixed local classes; never calls a no-grad generation pipeline. This is an
original *early predicted-latent temporal-energy* proxy, not Vid-Freeze, a full
video loss, or text-guided video protection. Its default probe resolution is
512x288, deliberately recorded rather than represented as native evaluation.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
import math
from pathlib import Path
from .errors import RiposteError
from .models import offline, read_config, model_fingerprint, configuration_fingerprint, select_device
from .policy import is_link

@dataclass(frozen=True)
class TemporalConfig:
    width: int = 512
    height: int = 288
    frames: int = 14
    generation_steps: int = 25
    fps: int = 7
    motion_bucket: int = 127
    noise_augmentation: float = .02
    guidance_max: float = 3.0

    def __post_init__(self):
        if (any(type(v) is not int for v in (self.width, self.height, self.frames, self.generation_steps, self.fps, self.motion_bucket))
            or not 64 <= self.width <= 1024 or not 64 <= self.height <= 1024
            or self.width % 8 or self.height % 8 or not 2 <= self.frames <= 25
            or not 2 <= self.generation_steps <= 100 or not 1 <= self.fps <= 60
            or not 0 <= self.motion_bucket <= 255 or not math.isfinite(self.noise_augmentation)
            or not 0 <= self.noise_augmentation <= .2 or not math.isfinite(self.guidance_max)
            or not 1 <= self.guidance_max <= 5):
            raise RiposteError("TEMPORAL_PARAMETERS_INVALID")


def letterbox_tensor(x, width, height):
    import torch.nn.functional as F
    h, w = x.shape[-2:]
    factor = min(width / w, height / h)
    nw, nh = max(1, round(w * factor)), max(1, round(h * factor))
    fitted = F.interpolate(x, (nh, nw), mode="bicubic", align_corners=False, antialias=True).clamp(0, 1)
    left, top = (width - nw) // 2, (height - nh) // 2
    return F.pad(fitted, (left, width - nw - left, top, height - nh - top), value=1.)


def v_prediction_original(sample, velocity, sigma):
    """Euler v-prediction's predicted original sample, before its Euler step."""
    return sample / (sigma * sigma + 1) - velocity * sigma / (sigma * sigma + 1) ** .5


class LocalTemporalProbe:
    def __init__(self, folder: Path, device="auto", config: TemporalConfig = TemporalConfig()):
        offline()
        try:
            import torch
            from diffusers import AutoencoderKLTemporalDecoder, UNetSpatioTemporalConditionModel, EulerDiscreteScheduler
            from transformers import CLIPVisionModelWithProjection
        except ImportError:
            raise RiposteError("INSTALL_LAB_DEPENDENCIES") from None
        self.config, self.device = config, select_device(device)
        components = ("vae", "unet", "image_encoder", "scheduler", "feature_extractor")
        configuration = configuration_fingerprint(folder, components)
        index = read_config(folder / "model_index.json")
        expected = {"vae": ["diffusers", "AutoencoderKLTemporalDecoder"],
                    "unet": ["diffusers", "UNetSpatioTemporalConditionModel"],
                    "image_encoder": ["transformers", "CLIPVisionModelWithProjection"],
                    "scheduler": ["diffusers", "EulerDiscreteScheduler"]}
        if index.get("_class_name") != "StableVideoDiffusionPipeline" or any(index.get(k) != v for k, v in expected.items()):
            raise RiposteError("TEMPORAL_ARCHITECTURE_UNSUPPORTED")
        if is_link(folder) or any(is_link(p) for p in folder.parents):
            raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
        for part in (*expected, "feature_extractor"):
            if not (folder / part).is_dir() or any(is_link(p) for p in [folder / part, *(folder / part).rglob("*")]):
                raise RiposteError("LOCAL_MODEL_DIRECTORY_REQUIRED")
        unet_config = read_config(folder / "unet/config.json")
        scheduler_config = read_config(folder / "scheduler/scheduler_config.json")
        if unet_config.get("in_channels") != 8 or unet_config.get("out_channels") != 4:
            raise RiposteError("TEMPORAL_CHANNELS_UNSUPPORTED")
        if scheduler_config.get("prediction_type") != "v_prediction":
            raise RiposteError("TEMPORAL_V_PREDICTION_REQUIRED")
        processor = read_config(folder / "feature_extractor/preprocessor_config.json")
        mean, std = processor.get("image_mean"), processor.get("image_std")
        if (not isinstance(mean, list) or not isinstance(std, list) or len(mean) != 3 or len(std) != 3
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in mean + std)
            or any(v <= 0 for v in std)):
            raise RiposteError("TEMPORAL_IMAGE_NORMALIZATION_INVALID")
        hashes = {p: model_fingerprint(folder / p) for p in ("vae", "unet", "image_encoder")}
        self.dtype = torch.float16 if self.device == "cuda" else torch.float32
        def kwargs(part, dtype):
            options = {"local_files_only": True, "use_safetensors": True, "torch_dtype": dtype}
            if (not list((folder / part).glob("*model.safetensors"))
                and list((folder / part).glob("*model.fp16.safetensors"))):
                options["variant"] = "fp16"
            return options
        try:
            self.vae = AutoencoderKLTemporalDecoder.from_pretrained(str(folder / "vae"), **kwargs("vae", torch.float32)).to(self.device).eval()
            self.unet = UNetSpatioTemporalConditionModel.from_pretrained(str(folder / "unet"), **kwargs("unet", self.dtype)).to(self.device).eval()
            self.image_encoder = CLIPVisionModelWithProjection.from_pretrained(str(folder / "image_encoder"), **kwargs("image_encoder", self.dtype)).to(self.device).eval()
            for m in (self.vae, self.unet, self.image_encoder): m.requires_grad_(False)
            scheduler = EulerDiscreteScheduler.from_pretrained(str(folder / "scheduler"), local_files_only=True)
            scheduler.set_timesteps(config.generation_steps, device=self.device)
            self.sigma, self.initial_sigma = float(scheduler.sigmas[0]), float(scheduler.init_noise_sigma)
            self.timestep = scheduler.timesteps[0].detach()
            self.factor = 2 ** (len(self.vae.config.block_out_channels) - 1)
            self.clip_size = int(self.image_encoder.config.image_size)
            self.mean = torch.tensor(mean, device=self.device)[None, :, None, None]
            self.std = torch.tensor(std, device=self.device)[None, :, None, None]
            if self.clip_size not in (224, 336) or self.factor not in (4, 8, 16):
                raise RiposteError("TEMPORAL_COMPONENT_SHAPE_UNSUPPORTED")
        except RiposteError: raise
        except Exception: raise RiposteError("LOCAL_TEMPORAL_LOAD_FAILED") from None
        if configuration_fingerprint(folder, components) != configuration:
            raise RiposteError("MODEL_CONFIGURATION_CHANGED")
        self.identity = {"kind": "SVD_EARLY_TEMPORAL_ENERGY", "component_sha256": hashes,
                         "configuration_sha256": configuration,
                         "settings": asdict(config), "sigma": self.sigma, "initial_sigma": self.initial_sigma,
                         "unet_precision": "float16" if self.device == "cuda" else "float32", "vae_precision": "float32",
                         "scope": "FIRST_STEP_PREDICTED_LATENTS_NOT_GENERATED_VIDEO", "text_conditioned": False,
                         "image_preprocessing": "DIFFERENTIABLE_BICUBIC_ANTIALIAS_NOT_PIPELINE_EQUIVALENCE_CERTIFIED",
                         "ai_protection": "UNVERIFIED"}

    def __call__(self, x, seed: int):
        import torch
        import torch.nn.functional as F
        if type(seed) is not int or not 0 <= seed < 2**32 or x.shape[0] != 1:
            raise RiposteError("TEMPORAL_INPUT_INVALID")
        cfg = self.config
        pixels = letterbox_tensor(x, cfg.width, cfg.height)
        clip = F.interpolate(pixels, (self.clip_size, self.clip_size), mode="bicubic", align_corners=False, antialias=True)
        embedding = self.image_encoder(((clip - self.mean) / self.std).to(self.dtype)).image_embeds[:, None]
        rng = torch.Generator("cpu").manual_seed(seed)
        augmentation = torch.randn(pixels.shape, generator=rng, dtype=torch.float32).to(x.device)
        z = self.vae.encode(pixels * 2 - 1 + cfg.noise_augmentation * augmentation).latent_dist.mode()
        cond = z[:, None].repeat(1, cfg.frames, 1, 1, 1).to(self.dtype)
        noise = torch.randn(cond.shape, generator=rng, dtype=torch.float32).to(x.device) * self.initial_sigma
        scaled = (noise / math.sqrt(self.sigma**2 + 1)).to(self.dtype)
        time_ids = torch.tensor([[cfg.fps - 1, cfg.motion_bucket, cfg.noise_augmentation]], device=x.device, dtype=self.dtype)
        # Unconditional response cannot depend on image pixels; do not retain its graph.
        with torch.no_grad():
            uncond = self.unet(torch.cat((scaled, torch.zeros_like(cond)), dim=2), self.timestep,
                               encoder_hidden_states=torch.zeros_like(embedding), added_time_ids=time_ids).sample
        conditional = self.unet(torch.cat((scaled, cond), dim=2), self.timestep,
                                encoder_hidden_states=embedding, added_time_ids=time_ids).sample
        guidance = torch.linspace(1., cfg.guidance_max, cfg.frames, device=x.device)[None, :, None, None, None]
        velocity = uncond.float() + guidance * (conditional.float() - uncond.float())
        return v_prediction_original(noise, velocity, self.sigma)
