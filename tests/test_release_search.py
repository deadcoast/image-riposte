"""Production search regressions using actual gradients, codec views and quality gates."""
from dataclasses import replace
import io
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pytest
from PIL import Image

torch = pytest.importorskip("torch")

from riposte.errors import RiposteError
from riposte.quality import QualityLimits, quality_report, spatial_budget
from riposte.release_guard import ReleaseConfig, protect_release


class Encoder:
    device = "cpu"
    identity = {"kind": "SYNTHETIC_SEARCH_REGRESSION"}

    def __call__(self, x):
        return x.square() + .15 * x


class NonlinearEncoder(Encoder):
    def __call__(self, x):
        return torch.sin(25 * x) + 1.5


def test_selection_retains_intermediate_iterates_independently_of_trace_cadence():
    image = Image.new("RGB", (24, 24), (90, 120, 150))
    config = ReleaseConfig(steps=4, restarts=1, step_255=2, checkpoint_every=1)
    dense, dense_report = protect_release(image, [NonlinearEncoder()], config)
    sparse, sparse_report = protect_release(image, [NonlinearEncoder()], replace(config, checkpoint_every=4))
    assert dense.tobytes() == sparse.tobytes()
    assert dense_report["selection"] == sparse_report["selection"]
    assert dense_report["contexts"] == sparse_report["contexts"]
    assert any(point["selected"] and point["step"] not in (1, 4) for point in sparse_report["trace"])


def test_oversized_step_recovers_without_loosening_quality_or_pixel_budget():
    image = Image.new("RGB", (32, 32), (90, 120, 150))
    before = image.tobytes()
    config = ReleaseConfig(steps=1, restarts=1, step_255=8)
    output, report = protect_release(image, [Encoder()], config)
    assert image.tobytes() == before and output.tobytes() != before
    assert quality_report(image, output)["status"] == "PASS"
    assert report["quality"]["policy"] == QualityLimits().public()
    assert report["selection"]["step_255"] < config.step_255
    assert report["selection"]["backtracks"] > 0
    assert min(row["score"] for row in report["contexts"]) > report["selection"]["initial_min_context_score"]
    caps = spatial_budget(image, QualityLimits())
    assert np.all(np.abs(np.asarray(output, dtype=int) - np.asarray(image, dtype=int)) <= caps[..., None])


def test_recovery_is_deterministic_and_does_not_consume_global_rng():
    image = Image.new("RGB", (32, 32), (90, 120, 150))
    config = ReleaseConfig(steps=3, restarts=2, step_255=8)
    before = torch.get_rng_state().clone()
    a, ar = protect_release(image, [Encoder()], config)
    b, br = protect_release(image, [Encoder()], config)
    assert a.tobytes() == b.tobytes() and ar == br
    assert torch.equal(before, torch.get_rng_state())


def test_cancellation_interrupts_quality_backtracking():
    image = Image.new("RGB", (32, 32), (90, 120, 150))
    events = []

    def progress(update):
        if update["phase"] == "Reducing publishing step for image quality":
            events.append(update)
            raise RiposteError("JOB_CANCELLED")

    with pytest.raises(RiposteError, match="JOB_CANCELLED"):
        protect_release(image, [Encoder()], ReleaseConfig(steps=1, restarts=1, step_255=8), progress=progress)
    assert len(events) == 1


@pytest.mark.parametrize("step_size", [8, .05])
def test_exhausted_quality_retries_are_bounded_and_never_return_random_start(step_size):
    image = Image.new("RGB", (32, 32), (90, 120, 150))
    events = []
    with pytest.raises(RiposteError, match="NO_IMPROVED_FIDELITY_ACCEPTABLE_CANDIDATE"):
        protect_release(image, [Encoder()], ReleaseConfig(steps=1, restarts=1, step_255=step_size),
                        QualityLimits(rms_fraction=.1, delta_e76_p95=.1), progress=events.append)
    reductions = [event for event in events if event["phase"] == "Reducing publishing step for image quality"]
    assert len(reductions) == (8 if step_size == 8 else 0)


def test_publishing_uses_recovered_exact_pixels(root, make_image, monkeypatch):
    from riposte import models, publication
    from riposte.organizer import organize
    from riposte.policy import Policy
    from riposte.sanitize import png_audit
    from riposte.store import catalog, state_relative

    make_image(root / "art.png", size=(32, 32), color=(90, 120, 150))
    organize(root, Policy(date_mode="modified"))
    master = catalog(root)[0]
    master_path = root / master["relative"]
    original = master_path.read_bytes()
    monkeypatch.setattr(models, "LocalEncoder", lambda *args: Encoder())
    recipe = publication.PublishRecipe((64,), ReleaseConfig(steps=1, restarts=1, step_255=8))
    batch = publication.start_publication(root, [master["id"]], [Path("SYNTHETIC_LOCAL_ENCODER")], recipe)
    assert batch["counts"]["READY_FOR_REVIEW"] == 1
    assert batch["counts"]["BLOCKED"] == 0
    item = batch["items"][0]
    folder = root / state_relative(root, f"publishing/{batch['id']}/items/{item['id']}")
    report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
    assert report["guard"]["selection"]["backtracks"] > 0
    raw = publication.publication_pixels(root, batch["id"], item["id"])
    expected, expected_report = protect_release(Image.new("RGB", (32, 32), (90, 120, 150)), [Encoder()], recipe.guard)
    with Image.open(io.BytesIO(raw)) as saved:
        assert saved.tobytes() == expected.tobytes()
    assert report["guard"]["contexts"] == expected_report["contexts"]
    assert png_audit(raw)["date"] == png_audit(original)["date"]
    publication.review_publication(root, batch["id"], [item["id"]], "ACCEPTED", True, True)
    with ZipFile(io.BytesIO(publication.publication_zip(root, batch["id"]))) as exported:
        assert len(exported.namelist()) == 1
        assert exported.read(exported.namelist()[0]) == raw
    assert master_path.read_bytes() == original
