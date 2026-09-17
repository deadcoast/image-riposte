"""Configuration identity through real adapters with deterministic component fixtures."""
import json
import shutil
import sys
from types import SimpleNamespace as NS

import pytest

from riposte import models, publication
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.release_guard import ReleaseConfig
from riposte.store import catalog, state_relative


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def bundle(tmp_path):
    folder = tmp_path / "local-model"
    write_json(folder / "config.json", {"_class_name": "AutoencoderKL", "scaling_factor": .18,
                                       "private": "PRIVATE_CONFIG_VALUE"})
    (folder / "model.safetensors").write_bytes(b"SYNTHETIC_COMPONENT_FIXTURE")
    return folder


@pytest.fixture
def components(monkeypatch):
    torch = pytest.importorskip("torch")
    mutations = []

    class Component(torch.nn.Module):
        config = NS(block_out_channels=(1, 2, 3, 4), encoder_block_out_channels=(1, 2, 3, 4),
                    scaling_factor=.18, image_size=224)

        @classmethod
        def from_pretrained(cls, path, **kwargs):
            assert kwargs["local_files_only"] and kwargs["use_safetensors"]
            if mutations:
                mutations.pop(0)()
            return cls()

        def encode(self, x):
            return NS(latent_dist=NS(mean=x.square() + .15 * x), latents=x.square() + .15 * x)

        def forward(self, x):
            return (x.float()[..., None],)

    class Scheduler:
        config = NS(num_train_timesteps=1000)

        @classmethod
        def from_pretrained(cls, path, **kwargs):
            assert kwargs["local_files_only"]
            return cls()

        def set_timesteps(self, n, device):
            self.sigmas = torch.tensor([5., 1.])
            self.init_noise_sigma = 5.
            self.timesteps = torch.tensor([1., 0.])

    class Tokenizer:
        model_max_length = 4

        @classmethod
        def from_pretrained(cls, path, **kwargs):
            assert kwargs["local_files_only"]
            return cls()

        def __call__(self, *args, **kwargs):
            return NS(input_ids=torch.ones(1, 4, dtype=torch.long))

    monkeypatch.setitem(sys.modules, "diffusers", NS(AutoencoderKL=Component, AutoencoderTiny=Component,
        UNet2DConditionModel=Component, DDIMScheduler=Scheduler, AutoencoderKLTemporalDecoder=Component,
        UNetSpatioTemporalConditionModel=Component, EulerDiscreteScheduler=Scheduler))
    monkeypatch.setitem(sys.modules, "transformers", NS(CLIPTextModel=Component, CLIPTokenizer=Tokenizer,
                                                       CLIPVisionModelWithProjection=Component))
    return mutations


@pytest.fixture
def pipeline(tmp_path):
    def create(kind):
        folder = tmp_path / kind
        temporal = kind == "temporal"
        parts = {"vae": ["diffusers", "AutoencoderKLTemporalDecoder" if temporal else "AutoencoderKL"],
                 "unet": ["diffusers", "UNetSpatioTemporalConditionModel" if temporal else "UNet2DConditionModel"],
                 "scheduler": ["diffusers", "EulerDiscreteScheduler" if temporal else "DDIMScheduler"]}
        if temporal:
            parts["image_encoder"] = ["transformers", "CLIPVisionModelWithProjection"]
        else:
            parts.update(text_encoder=["transformers", "CLIPTextModel"], tokenizer=["transformers", "CLIPTokenizer"])
        write_json(folder / "model_index.json", {"_class_name": "StableVideoDiffusionPipeline" if temporal else "StableDiffusionInpaintPipeline", **parts})
        for part in ("vae", "unet", "image_encoder" if temporal else "text_encoder"):
            write_json(folder / part / "config.json", {"in_channels": 8 if temporal else 9, "out_channels": 4})
            (folder / part / "model.safetensors").write_bytes(b"SYNTHETIC_COMPONENT_FIXTURE")
        write_json(folder / "scheduler/scheduler_config.json", {"prediction_type": "v_prediction", "num_train_timesteps": 1000})
        if temporal:
            write_json(folder / "feature_extractor/preprocessor_config.json", {"image_mean": [.48, .45, .4], "image_std": [.26, .26, .27]})
        else:
            write_json(folder / "tokenizer/vocab.json", {"word": 1})
            (folder / "tokenizer/merges.txt").write_text("#version: 0.2\na b\n", encoding="utf-8")
        return folder
    return create


def test_encoder_config_edit_changes_identity_without_changing_weights(bundle, components):
    before = models.LocalEncoder(bundle, "cpu").identity
    config = json.loads((bundle / "config.json").read_text())
    config["scaling_factor"] = .36
    write_json(bundle / "config.json", config)
    after = models.LocalEncoder(bundle, "cpu").identity
    assert before["weights_sha256"] == after["weights_sha256"]
    assert before != after
    assert "PRIVATE_CONFIG_VALUE" not in json.dumps(after) and str(bundle) not in json.dumps(after)


@pytest.mark.parametrize("kind,relative", [("inpaint", "tokenizer/merges.txt"),
    ("inpaint", "tokenizer/vocab.json"), ("inpaint", "scheduler/scheduler_config.json"),
    ("inpaint", "vae/config.json"), ("temporal", "feature_extractor/preprocessor_config.json"),
    ("temporal", "scheduler/scheduler_config.json"), ("temporal", "image_encoder/config.json")])
def test_pipeline_configuration_changes_identity(pipeline, components, kind, relative):
    from riposte.temporal import LocalTemporalProbe
    folder = pipeline(kind)
    adapter = LocalTemporalProbe if kind == "temporal" else models.LocalInpaintProbe
    before = adapter(folder, "cpu").identity
    path = folder / relative
    if relative.endswith(".txt"):
        path.write_text("#version: 0.2\nb c\n", encoding="utf-8")
    else:
        config = json.loads(path.read_text())
        key, value = (("image_mean", [.1, .2, .3]) if "preprocessor" in relative else
                      ("num_train_timesteps", 900) if "scheduler" in relative else
                      ("word", 2) if "vocab" in relative else ("hidden_act", "relu"))
        config[key] = value
        write_json(path, config)
    after = adapter(folder, "cpu").identity
    assert before["component_sha256"] == after["component_sha256"]
    assert before != after


@pytest.mark.parametrize("kind", ["encoder", "inpaint", "temporal"])
def test_configuration_mutated_during_loading_is_rejected(bundle, pipeline, components, kind):
    from riposte.temporal import LocalTemporalProbe
    folder = bundle if kind == "encoder" else pipeline(kind)
    adapter = {"encoder": models.LocalEncoder, "inpaint": models.LocalInpaintProbe, "temporal": LocalTemporalProbe}[kind]
    path = folder / ("config.json" if kind == "encoder" else "scheduler/scheduler_config.json")
    config = json.loads(path.read_text())
    config["changed_during_load"] = True
    components.append(lambda: write_json(path, config))
    with pytest.raises(RiposteError, match="MODEL_CONFIGURATION_CHANGED"):
        adapter(folder, "cpu")


@pytest.mark.parametrize("change", [False, True])
def test_interrupted_publication_resume_checks_configuration(root, make_image, bundle, components, tmp_path, change):
    for name in ("first.png", "second.png"):
        make_image(root / name, size=(32, 32), color=(90, 120, 150))
    organize(root, Policy(date_mode="modified"))
    ids = [row["id"] for row in catalog(root)]
    recipe = publication.PublishRecipe((64,), ReleaseConfig(steps=3, restarts=1))

    def stop(update):
        if update.get("item") == 2:
            raise RiposteError("JOB_CANCELLED")

    with pytest.raises(RiposteError, match="JOB_CANCELLED"):
        publication.start_publication(root, ids, [bundle], recipe, device="cpu", progress=stop)
    batch = publication.publication_status(root, publication.publications(root)[0]["id"])
    assert batch["counts"]["READY_FOR_REVIEW"] == 1
    committed = root / state_relative(root, f"publishing/{batch['id']}/items/{batch['items'][0]['id']}")
    before = {p.name: p.read_bytes() for p in committed.iterdir()}
    relocated = tmp_path / "relocated-model"
    shutil.copytree(bundle, relocated)
    if change:
        config = json.loads((relocated / "config.json").read_text())
        config["scaling_factor"] = .36
        write_json(relocated / "config.json", config)
        with pytest.raises(RiposteError, match="PUBLICATION_RESUME_MODEL_MISMATCH"):
            publication.resume_publication(root, batch["id"], [relocated], device="cpu")
        assert publication.publication_status(root, batch["id"])["counts"]["READY_FOR_REVIEW"] == 1
    else:
        result = publication.resume_publication(root, batch["id"], [relocated], device="cpu")
        assert result["counts"]["READY_FOR_REVIEW"] == 2
    assert before == {p.name: p.read_bytes() for p in committed.iterdir()}


@pytest.mark.parametrize("change", ["add", "remove", "rename"])
def test_configuration_file_set_is_bound(bundle, change):
    extra = bundle / "added_tokens.json"
    if change != "add":
        write_json(extra, {"private": 1})
    before = models.configuration_fingerprint(bundle)
    if change == "add":
        write_json(extra, {"private": 1})
    elif change == "remove":
        extra.unlink()
    else:
        extra.rename(bundle / "tokenizer_config.json")
    assert models.configuration_fingerprint(bundle) != before


def test_linked_configuration_is_rejected_without_reading_it(bundle, monkeypatch):
    path = bundle / "tokenizer_config.json"
    write_json(path, {"private": "PRIVATE_VALUE"})
    original = models.is_link
    monkeypatch.setattr(models, "is_link", lambda item: item == path or original(item))
    with pytest.raises(RiposteError, match="MODEL_CONFIG_INVALID"):
        models.configuration_fingerprint(bundle)


def test_actual_local_vae_activation_change_alters_features_and_identity(tmp_path):
    torch = pytest.importorskip("torch")
    diffusers = pytest.importorskip("diffusers")
    # Build a tiny randomly initialized fixture entirely locally; exercise the
    # installed loader and adapter with no substituted model implementation.
    folder = tmp_path / "tiny-vae"
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(17)
        vae = diffusers.AutoencoderKL(block_out_channels=(8,), norm_num_groups=4,
                                     latent_channels=4, sample_size=16)
        vae.save_pretrained(folder, safe_serialization=True)
    first = models.LocalEncoder(folder, "cpu")
    x = torch.linspace(.1, .9, 3 * 16 * 16).reshape(1, 3, 16, 16).requires_grad_(True)
    before = first(x)
    config = json.loads((folder / "config.json").read_text())
    config["act_fn"] = "relu"
    write_json(folder / "config.json", config)
    second = models.LocalEncoder(folder, "cpu")
    after = second(x)
    assert first.identity["weights_sha256"] == second.identity["weights_sha256"]
    assert first.identity["configuration_sha256"] != second.identity["configuration_sha256"]
    assert not torch.allclose(before, after)
    gradient = torch.autograd.grad(after.square().mean(), x)[0]
    assert torch.isfinite(gradient).all() and (gradient != 0).any()
