"""Clean / candidate / noise-controlled local generation experiments.

Generation output changes are not an efficacy score. This deliberately requires
human inspection and binds every served raster to its committed report hash.
SD img2img, 9-channel SD inpainting and SVD are reference baselines,
not modern-family coverage. Local pretrained integration is not qualified.
The fixed Kontext editing path adds one architecture, with separate conditioning
and geometry; a declared architecture does not attest to its weights or efficacy.
"""
from __future__ import annotations
from . import __version__
import json
import math
import re
import shutil
import uuid
from pathlib import Path
from collections.abc import Mapping, Sequence
import numpy as np
from PIL import Image, ImageOps
from .errors import RiposteError
from .models import offline, read_config, model_fingerprint, configuration_fingerprint
from .kontext import KIND as KONTEXT_KIND, KontextGenerator, prepare as prepare_kontext
from .experiment import begin_experiment, finish_experiment, conditioning, _object, _text
from .records import Progress
from .qualification import _verified_pair, CONTROL_SEEDS
from .views import publication_view, matched_control, TRAIN_VIEWS, HOLDOUT_VIEWS
from .sanitize import encode_clean, png_audit, social_render
from .metrics import fidelity
from .store import workspace_lock, safe_child, state_relative, atomic_clean_write, atomic_json_write

ALLOWED_COMPONENTS = {
    'diffusers': {'AutoencoderKL', 'AutoencoderKLTemporalDecoder', 'UNet2DConditionModel',
                 'UNetSpatioTemporalConditionModel', 'DDIMScheduler', 'PNDMScheduler',
                 'EulerDiscreteScheduler', 'EulerAncestralDiscreteScheduler', 'LMSDiscreteScheduler',
                 'DPMSolverMultistepScheduler', 'DDPMScheduler'},
    'transformers': {'CLIPTextModel', 'CLIPTokenizer', 'CLIPImageProcessor', 'CLIPFeatureExtractor',
                     'CLIPVisionModelWithProjection'},
    'stable_diffusion': {'StableDiffusionSafetyChecker'},
}


class LocalGenerator:
    identity: dict[str, object]

    def __init__(self, folder: Path, task: str):
        self._kontext: KontextGenerator | None = None
        offline()
        try:
            import torch
            from diffusers import StableDiffusionImg2ImgPipeline, StableDiffusionInpaintPipeline, StableVideoDiffusionPipeline
        except ImportError:
            raise RiposteError('INSTALL_LAB_DEPENDENCIES') from None
        if task not in {'edit', 'inpaint', 'video'}:
            raise RiposteError('GENERATION_TASK_INVALID')
        if not torch.cuda.is_available():
            raise RiposteError('GENERATION_BENCHMARK_REQUIRES_CUDA')
        config = read_config(folder / 'model_index.json')
        if config.get('_class_name') == 'FluxKontextPipeline':
            if task != 'edit':
                raise RiposteError('GENERATION_ARCHITECTURE_UNSUPPORTED')
            self._kontext = KontextGenerator(folder)
            self.identity = self._kontext.identity
            self.task = task
            return
        allowed = ({'StableDiffusionPipeline', 'StableDiffusionImg2ImgPipeline'} if task == 'edit' else
                   {'StableDiffusionInpaintPipeline'} if task == 'inpaint' else {'StableVideoDiffusionPipeline'})
        if config.get('_class_name') not in allowed:
            raise RiposteError('GENERATION_ARCHITECTURE_UNSUPPORTED')
        from .policy import is_link
        if is_link(folder) or any(is_link(p) for p in folder.parents):
            raise RiposteError('LOCAL_MODEL_DIRECTORY_REQUIRED')
        components = {}
        for name, descriptor in config.items():
            if name.startswith('_') or not isinstance(descriptor, list):
                continue
            if descriptor == [None, None]:
                continue
            if (len(descriptor) != 2 or descriptor[0] not in ALLOWED_COMPONENTS
                    or descriptor[1] not in ALLOWED_COMPONENTS[descriptor[0]]
                    or not re.fullmatch(r'[a-z_]+', name)):
                raise RiposteError('GENERATION_COMPONENTS_UNSUPPORTED')
            components[name] = descriptor
        required = {'vae', 'unet', 'scheduler', 'text_encoder', 'tokenizer'} if task != 'video' else {'vae', 'unet', 'scheduler', 'image_encoder', 'feature_extractor'}
        if not required <= components.keys():
            raise RiposteError('GENERATION_COMPONENTS_UNSUPPORTED')
        hashes = {}
        for name in components:
            part = folder / name
            if is_link(part) or any(is_link(item) for item in part.rglob('*')):
                raise RiposteError('LOCAL_MODEL_DIRECTORY_REQUIRED')
            if list(part.glob('*.safetensors')):
                hashes[name] = model_fingerprint(part)
        if not {'vae', 'unet'} <= hashes.keys():
            raise RiposteError('SAFETENSORS_REQUIRED')
        if task == 'inpaint' and read_config(folder / 'unet/config.json').get('in_channels') != 9:
            raise RiposteError('INPAINT_NINE_CHANNEL_REQUIRED')
        configuration = configuration_fingerprint(folder, tuple(components))
        try:
            cls = {'edit': StableDiffusionImg2ImgPipeline, 'inpaint': StableDiffusionInpaintPipeline, 'video': StableVideoDiffusionPipeline}[task]
            self.pipeline = cls.from_pretrained(str(folder), local_files_only=True, use_safetensors=True,
                                                 torch_dtype=torch.float16).to('cuda')
            self.pipeline.set_progress_bar_config(disable=True)
        except Exception:
            raise RiposteError('LOCAL_PIPELINE_LOAD_FAILED') from None
        if configuration_fingerprint(folder, tuple(components)) != configuration:
            raise RiposteError('MODEL_CONFIGURATION_CHANGED')
        if any(model_fingerprint(folder / name) != value for name, value in hashes.items()):
            raise RiposteError('MODEL_WEIGHTS_CHANGED')
        self.task = task
        self.identity = {'kind': {'edit':'SD_IMG2IMG_BASELINE','inpaint':'SD_INPAINT_BASELINE','video':'SVD_I2V_BASELINE'}[task],
                         'component_sha256': hashes, 'configuration_sha256': configuration,
                         'precision': 'float16', 'device': 'cuda'}

    def __call__(self, image: Image.Image, seed: int, steps: int) -> list[Image.Image]:
        if self._kontext is not None:
            frames = self._kontext(image, seed, steps)
            self.last_flags = dict(self._kontext.last_flags)
            return frames
        import torch
        generator = torch.Generator('cuda').manual_seed(seed)
        with torch.inference_mode():
            if self.task != 'video':
                options={}
                if self.task == 'inpaint':
                    from .views import keep_mask
                    keep=keep_mask((image.height,image.width),'right',seed,'cpu')[0,0].numpy()
                    options['mask_image']=Image.fromarray(((1-keep)*255).astype(np.uint8))
                output = self.pipeline(prompt='Preserve the main illustration and add a patterned background.',
                    image=image, strength=.65, guidance_scale=7.5, num_inference_steps=steps, generator=generator, **options)
                flags = getattr(output, 'nsfw_content_detected', None)
                self.last_flags = {'content_filter_reported': flags is not None,
                                   'content_filter_flags': [bool(value) for value in flags] if flags is not None else None}
                return output.images
            self.last_flags = {'content_filter_reported': False, 'content_filter_flags': None}
            return self.pipeline(image, num_frames=14, num_inference_steps=steps,
                                 decode_chunk_size=2, generator=generator).frames[0]


def prepare_input(image: Image.Image, task: str, model: Mapping[str, object] | None = None) -> Image.Image:
    if model is not None and model.get('kind') == KONTEXT_KIND:
        if task != 'edit':
            raise RiposteError('GENERATION_ARCHITECTURE_UNSUPPORTED')
        return prepare_kontext(image)
    if task == 'video':
        return ImageOps.pad(image.convert('RGB'), (1024, 576), color='white')
    if task not in {'edit','inpaint'}:
        raise RiposteError('GENERATION_TASK_INVALID')
    image = social_render(image, 768)
    w, h = image.size
    return image.resize((max(8, w // 8 * 8), max(8, h // 8 * 8)), Image.Resampling.LANCZOS)


def frame_motion(frames: list[Image.Image]) -> float | None:
    """Descriptive adjacent-frame RMSE, not motion quality or success."""
    if len(frames) < 2:
        return None
    return float(np.mean([fidelity(a, b)['rmse_255'] for a, b in zip(frames[:-1], frames[1:], strict=True)]))


def _validate(task: str, seeds: Sequence[int], views: Sequence[str], steps: int) -> None:
    if (task not in {'edit', 'inpaint', 'video'} or not 1 <= len(seeds) <= 8 or len(set(seeds)) != len(seeds)
        or not all(isinstance(s, int) and not isinstance(s, bool) and 0 <= s < 2**32 for s in seeds)
        or not 1 <= len(views) <= 8 or len(set(views)) != len(views)
        or any(v not in TRAIN_VIEWS + HOLDOUT_VIEWS for v in views)
        or not isinstance(steps, int) or isinstance(steps, bool) or not 1 <= steps <= 100):
        raise RiposteError('GENERATION_PARAMETERS_INVALID')


def controlled_generation(root: Path, trial_id: str, model_dir: Path, task='edit', seeds=(7, 19),
                          views=('identity', 'jpeg70'), steps=25, progress=None) -> dict:
    _validate(task, seeds, views, steps)
    with workspace_lock(root):
        from .organizer import audit_workspace
        if audit_workspace(root)['checkpoint'] != 'COMPLETE':
            raise RiposteError('ORGANIZATION_CHECKPOINT_REQUIRED')
        trial, pair = _verified_pair(root, trial_id)
        if progress:
            progress({'phase': 'Loading explicitly selected generation baseline', 'processed': 0, 'total': 1})
        generator = LocalGenerator(model_dir, task)
        sealed = begin_experiment(root, trial, generator.identity, task, seeds, views, steps, CONTROL_SEEDS)
        try:
            report = _execute(root, trial, pair, generator, task, seeds, views, steps, progress, sealed)
        except BaseException as exc:
            cancelled = isinstance(exc, (KeyboardInterrupt, SystemExit)) or isinstance(exc, RiposteError) and exc.code == 'JOB_CANCELLED'
            finish_experiment(root, sealed, 'CANCELLED' if cancelled else 'FAILED')
            raise
        finish_experiment(root, sealed, 'COMPLETE')
        return report


def _execute(root: Path, trial: Mapping[str, object], pair: dict[str, Image.Image], generator: LocalGenerator,
             task: str, seeds: Sequence[int], views: Sequence[str], steps: int, progress: Progress | None,
             experiment: Mapping[str, object] | None = None, *, sequence: int | None = None) -> dict[str, object]:
    # Cohort execution proves these are first attempts under the same workspace lock.
    # Ordinary generation retains discovery of its existing per-trial sequence.
    if sequence is not None and (type(sequence) is not int or sequence < 1):
        raise RiposteError('GENERATION_PARAMETERS_INVALID')
    inputs = dict(pair)
    inputs.update({f'control_{i}': matched_control(pair['clean'], pair['candidate'], seed)
                   for i, seed in enumerate(CONTROL_SEEDS, 1)})
    run_id = _text(_object(experiment['protocol'])['id']) if experiment is not None else uuid.uuid4().hex
    prefix = state_relative(root, f'generations/{run_id}')
    groups: list[dict[str, object]] = []
    artifacts: dict[str, str] = {}
    total, processed = len(views) * len(seeds) * len(inputs), 0
    try:
        for view_index, view in enumerate(views):
            prepared = {role: prepare_input(publication_view(image, view), task, generator.identity) for role, image in inputs.items()}
            for seed_index, seed in enumerate(seeds):
                key = f'V{view_index:02d}-S{seed_index:02d}'
                outputs: dict[str, list[Image.Image]] = {}
                roles: dict[str, list[str]] = {}
                flags: dict[str, object] = {}
                for role, image in prepared.items():
                    if progress:
                        progress({'phase': f'Generating matched {task} baseline', 'processed': processed, 'total': total})
                    frames = generator(image, seed, steps)
                    flags[role] = dict(getattr(generator, 'last_flags', {'content_filter_reported': False, 'content_filter_flags': None}))
                    if (not isinstance(frames, list) or not 1 <= len(frames) <= 32
                        or not all(isinstance(frame, Image.Image) and max(frame.size) <= 4096 for frame in frames)):
                        raise RiposteError('GENERATION_OUTPUT_INVALID')
                    if any(frame.size != frames[0].size for frame in frames):
                        raise RiposteError('GENERATION_FRAME_DIMENSIONS_MISMATCH')
                    outputs[role] = frames
                    roles[role] = []
                    for fi, frame in enumerate(frames):
                        if progress:
                            progress({'phase': 'Writing date-only review frames', 'processed': processed, 'total': total})
                        relative = f'{key}-{role}/F{fi:03d}.png'
                        data = encode_clean(frame.convert('RGB'), _text(trial['date']))
                        atomic_clean_write(root, f'{prefix}/{relative}', data)
                        artifacts[relative] = png_audit(data)['sha256']
                        roles[role].append(relative)
                    processed += 1
                if any(len(frames) != len(outputs['clean']) for frames in outputs.values()):
                    raise RiposteError('GENERATION_FRAME_COUNT_MISMATCH')
                comparisons = {role: [fidelity(a, b) for a, b in zip(outputs['clean'], frames, strict=True)]
                               for role, frames in outputs.items() if role != 'clean'}
                groups.append({'view': view, 'seed': seed, 'roles': roles, 'comparisons_to_clean': comparisons,
                               'adjacent_frame_rmse_255': {role: frame_motion(frames) for role, frames in outputs.items()},
                               'prepared_input_fidelity': {role: fidelity(prepared['clean'], image)
                                                          for role, image in prepared.items() if role != 'clean'},
                               'pipeline_flags': flags, 'review': 'HUMAN_REVIEW_REQUIRED',
                               **({'prepared_input_size': list(prepared['clean'].size)} if generator.identity.get('kind') == KONTEXT_KIND else {})})
        if progress:
            progress({'phase': 'Committing generation review', 'processed': total, 'total': total})
        report: dict[str, object] = {'id': run_id, 'trial_id': trial['id'], 'date': trial['date'], 'candidate_sha256': _object(trial['artifact_sha256'])['candidate'],
                  'sequence': sequence if sequence is not None else max((r.get('sequence', 0) for r in generation_runs(root, _text(trial['id']))), default=0) + 1,
                  'protocol': 'riposte-five-arm-v1', 'application_version': __version__,
                  'task': task, 'conditioning': conditioning(task, generator.identity), 'model': generator.identity, 'seeds': list(seeds), 'steps': steps, 'views': list(views),
                  'controls': {'kind': 'FEASIBLE_SIGN_SCRAMBLED_MATCHED_MAGNITUDE', 'seeds': list(CONTROL_SEEDS),
                    'matching_scope': 'Before publication transforms; post-transform input fidelity recorded separately.'},
                  'groups': groups, 'artifacts': artifacts, 'evidence_level': 'CONTROLLED_GENERATIONS_UNSCORED',
                  'ai_protection': 'UNVERIFIED',
                  'limits': 'Same-seed output divergence and temporal RMSE are not protection scores. Review task success, source preservation and quality for every arm. CUDA kernels may be nondeterministic. SVD is not text-guided video.'}
        if experiment is not None:
            report['experiment_sha256'] = experiment['sha256']
        atomic_json_write(root, f'{prefix}/report.json', report)
        return report
    except BaseException:
        folder = safe_child(root, prefix)
        if folder.exists():
            shutil.rmtree(folder)
        raise


def generation_report(root: Path, identifier: str) -> dict:
    if not re.fullmatch(r'[0-9a-f]{32}', identifier):
        raise RiposteError('GENERATION_NOT_FOUND')
    path = safe_child(root, state_relative(root, f'generations/{identifier}/report.json'))
    try:
        result = json.loads(path.read_text())
    except (OSError, ValueError):
        raise RiposteError('GENERATION_NOT_FOUND') from None
    from .lab import trial_report
    trial = trial_report(root, result['trial_id'])
    if result['candidate_sha256'] != trial['artifact_sha256']['candidate']:
        raise RiposteError('GENERATION_TRIAL_MISMATCH')
    return result


def generation_runs(root: Path, trial_id: str) -> list[dict]:
    from .lab import trial_report
    trial_report(root, trial_id)
    folder = safe_child(root, state_relative(root, 'generations'))
    if not folder.exists():
        return []
    result = []
    for child in folder.iterdir():
        if re.fullmatch(r'[0-9a-f]{32}', child.name):
            try:
                report = generation_report(root, child.name)
                if report['trial_id'] == trial_id:
                    result.append(report)
            except RiposteError:
                pass
    return sorted(result, key=lambda item: (item.get('sequence', 0), item['id']))


def generation_frame(root: Path, identifier: str, relative: str) -> bytes:
    report = generation_report(root, identifier)
    if relative not in report['artifacts']:
        raise RiposteError('GENERATION_FRAME_NOT_FOUND')
    # A report is not permission to escape its run directory.
    if not re.fullmatch(r'V\d{2}-S\d{2}-(clean|candidate|control_[123])/F\d{3}\.png', relative):
        raise RiposteError('GENERATION_FRAME_NOT_FOUND')
    data = safe_child(root, state_relative(root, f'generations/{identifier}/{relative}')).read_bytes()
    audit = png_audit(data)
    if audit['sha256'] != report['artifacts'][relative] or audit['date'] != report['date']:
        raise RiposteError('GENERATION_FRAME_CHANGED')
    return data
