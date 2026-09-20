"""Paired original/current engine CPU measurements using explicitly synthetic models."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import statistics
import sys
import time
import types
from unittest.mock import patch
from zipfile import ZipFile

import torch
from PIL import Image
from riposte import context_graph, coupled, release_guard
from riposte.views import differentiable_view

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def original_module(name, filename):
    with ZipFile(HERE / "source-before.zip") as archive:
        source = archive.read(filename)
    module = types.ModuleType("riposte." + name)
    module.__package__ = "riposte"
    sys.modules[module.__name__] = module
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


class Encoder:
    device = "cpu"
    identity = {"kind": "SYNTHETIC_CPU_MEASUREMENT"}

    def __init__(self, calls, heavy=False):
        self.calls = calls
        rng = torch.Generator().manual_seed(806)
        self.weights = [torch.randn(shape, generator=rng) * .05 for shape in
                        ((32, 3, 3, 3), (32, 32, 3, 3), (3, 32, 3, 3))] if heavy else []

    def __call__(self, x):
        self.calls["encoder"] += 1
        y = x
        for weight in self.weights:
            y = torch.nn.functional.silu(torch.nn.functional.conv2d(y, weight, padding=1))
        return x.square() + .15 * x + (.01 * y if self.weights else 0)


class Probe(Encoder):
    def __call__(self, x, keep, seed, fraction, prompt):
        self.calls["inpaint"] += 1
        return (x * keep + .5 * (1 - keep)).square() + .1 * x


class Temporal(Encoder):
    def __call__(self, x, seed):
        self.calls["temporal"] += 1
        # Deterministic image-dependent frame differences with real gradients.
        return torch.stack((x, x * (1 + x.mean())), dim=1)


def main():
    torch.set_num_threads(1)
    old = original_module("_pcuc_old_release", "src/riposte/release_guard.py")
    old_coupled = original_module("_pcuc_old_coupled", "src/riposte/coupled.py")
    old._features = old_coupled._features
    cases = []
    for width, height, models, optional, heavy in ((32, 24, 1, False, False), (64, 48, 2, False, False),
            (128, 96, 4, False, False), (64, 48, 2, True, False), (128, 96, 4, False, True)):
        image = Image.new("RGB", (width, height), (90, 120, 150))
        case = {"width": width, "height": height, "encoders": models, "optional_branches": optional,
                "synthetic_convolutional_model": heavy}
        results = {"before": [], "after": []}
        for sample in range(4):
            for label, engine in (("before", old), ("after", release_guard)):
                calls = Counter()

                def view(x, name):
                    calls["view:" + name] += 1
                    return differentiable_view(x, name)

                encoders = [Encoder(calls, heavy) for _ in range(models)]
                options = {"probe": Probe(calls), "temporal": Temporal(calls)} if optional else {}
                with patch.object(old_coupled, "differentiable_view", view), patch.object(old, "differentiable_view", view), \
                        patch.object(release_guard, "differentiable_view", view), patch.object(context_graph, "differentiable_view", view):
                    start = time.perf_counter()
                    output, report = engine.protect_release(image, encoders,
                        engine.ReleaseConfig(steps=3, restarts=1), **options)
                    elapsed = time.perf_counter() - start
                assert report["quality"]["status"] == "PASS"
                if sample:
                    results[label].append({"seconds": elapsed, "calls": dict(calls),
                        "output_sha256": hashlib.sha256(output.tobytes()).hexdigest(),
                        "contexts": report["contexts"], "selection": report["selection"], "quality": report["quality"]})
        for label, samples in results.items():
            assert len({row["output_sha256"] for row in samples}) == 1
            assert all(row["calls"] == samples[0]["calls"] for row in samples)
            case[label] = {"median_seconds": statistics.median(row["seconds"] for row in samples), "samples": samples}
        a, b = results["before"][0], results["after"][0]
        case["same_pixels"] = a["output_sha256"] == b["output_sha256"]
        case["same_selection"] = a["selection"] == b["selection"]
        case["same_context_scores"] = a["contexts"] == b["contexts"]
        assert all(a["calls"][key] == b["calls"][key] for key in ("encoder", "inpaint", "temporal") if key in a["calls"])
        case["speedup"] = case["before"]["median_seconds"] / case["after"]["median_seconds"]
        cases.append(case)
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    return {"result": "PASS", "platform": sys.platform, "python": sys.version, "torch": torch.__version__,
            "threads": torch.get_num_threads(), "warmup_runs_per_case_and_engine": 1,
            "measured_runs_per_case_and_engine": 3, "sources": sources, "cases": cases,
            "scope": "Paired CPU synthetic-model full-engine runs with real JPEG/resize and quality gates. Timings include instrumentation. Not pretrained/GPU acceleration or efficacy evidence."}


if __name__ == "__main__":
    (HERE / "measurements.json").write_text(json.dumps(main(), indent=2) + "\n", encoding="utf-8")
