"""PCUC: real codec/autograd algebra and production integration; synthetic models."""
from collections import Counter
import importlib
import sys

import pytest
from PIL import Image

torch = pytest.importorskip("torch")


@pytest.fixture(autouse=True)
def one_thread():
    old = torch.get_num_threads()
    torch.set_num_threads(1)
    yield
    torch.set_num_threads(old)


class Encoder:
    device = "cpu"
    identity = {"kind": "SYNTHETIC_SHARED_VIEW_REGRESSION"}

    def __call__(self, x):
        return x.square() + .15 * x


@pytest.mark.parametrize("models", [1, 2, 4])
def test_production_reuses_each_transform_in_each_pass(monkeypatch, models):
    from riposte import coupled, release_guard
    from riposte.views import differentiable_view
    calls = Counter()

    def counted(x, name):
        calls[name] += 1
        return differentiable_view(x, name)

    monkeypatch.setattr(coupled, "differentiable_view", counted)
    monkeypatch.setattr(release_guard, "differentiable_view", counted)
    if "riposte.context_graph" in sys.modules:
        monkeypatch.setattr(sys.modules["riposte.context_graph"], "differentiable_view", counted)
    output, report = release_guard.protect_release(
        Image.new("RGB", (32, 24), (90, 120, 150)), [Encoder() for _ in range(models)],
        release_guard.ReleaseConfig(steps=1, restarts=1))
    assert output.size == (32, 24) and report["quality"]["status"] == "PASS"
    # Clean references, initial scores, one gradient pass, accepted scores.
    assert calls == {"identity": 4, "jpeg85": 4, "resize75": 4}
    assert len(report["contexts"]) == 9 * models


@pytest.mark.parametrize("dtype", [torch.float32, torch.float64])
@pytest.mark.parametrize("repeats", [1, 3])
def test_factored_gradient_matches_independent_joint_autograd(dtype, repeats):
    graph = importlib.import_module("riposte.context_graph")
    from riposte.optimizer import _round_ste
    from riposte.views import differentiable_view
    rng = torch.Generator().manual_seed(401)
    x = torch.rand((1, 3, 17, 25), generator=rng, dtype=dtype) * .7 + .15
    names = ["identity", "jpeg85", "resize75"] * repeats

    def score(view, index):
        # Different signs/scales stand in for displacement + temporal losses.
        return (view.sin().square().mean() * (index + 1) - .4 * index)

    values = graph.context_values(x, names, score)
    leaf = x.detach().requires_grad_(True)
    q = _round_ste(leaf * 255) / 255
    # Score the same quantized input in both passes.
    values = graph.context_values(q.detach(), names, score)
    numbers = torch.tensor(values, dtype=dtype)
    tau = numbers.abs().mean().clamp_min(1e-6)
    weights = torch.softmax(-numbers / tau, 0).detach()
    joint = sum(weights[i] * score(differentiable_view(q, name), i) for i, name in enumerate(names))
    expected, = torch.autograd.grad(joint, leaf)
    events = []
    observed = graph.context_gradient(x, names, values, score, events.append)
    torch.testing.assert_close(observed, expected, rtol=2e-5, atol=2e-8 if dtype == torch.float32 else 2e-12)
    assert events == list(range(1, len(names) + 1))
    assert not observed.requires_grad and leaf.grad is None


def test_context_scores_preserve_original_order_and_cancel_between_branches():
    graph = importlib.import_module("riposte.context_graph")
    x = torch.full((1, 3, 16, 16), .5)
    names = ["identity", "jpeg85", "identity", "resize75", "jpeg85"]
    assert graph.context_values(x, names, lambda view, i: view.sum() * 0 + i) == list(range(5))
    visited = []

    def cancel(count):
        visited.append(count)
        if count == 2:
            raise RuntimeError("cancelled")

    with pytest.raises(RuntimeError, match="cancelled"):
        graph.context_gradient(x, names, [1.] * 5, lambda view, i: view.square().mean(), cancel)
    assert visited == [1, 2]


@pytest.mark.parametrize("kind", ["detached", "unrelated", "nonfinite", "nonfinite_gradient"])
def test_invalid_branch_gradients_are_rejected(kind):
    graph = importlib.import_module("riposte.context_graph")
    from riposte.errors import RiposteError
    x = torch.zeros((1, 3, 16, 16))

    def score(view, index):
        if kind == "detached": return view.detach().mean()
        if kind == "unrelated": return torch.ones((), requires_grad=True)
        if kind == "nonfinite": return view.mean() * float("nan")
        return view.sqrt().mean()

    with pytest.raises(RiposteError, match="MODEL_GRADIENT_UNAVAILABLE|OPTIMIZER_NONFINITE"):
        graph.context_gradient(x, ["identity"], [1.], score)


def test_saved_model_graph_memory_does_not_grow_with_context_count():
    graph = importlib.import_module("riposte.context_graph")
    x = torch.full((1, 3, 24, 32), .4)
    peaks = []
    for count in (1, 4, 16):
        live = {"bytes": 0, "peak": 0}

        class Saved:
            def __init__(self, tensor):
                self.tensor = tensor.detach()
                self.size = tensor.numel() * tensor.element_size()
                live["bytes"] += self.size
                live["peak"] = max(live["peak"], live["bytes"])

            def __del__(self):
                live["bytes"] -= self.size

        with torch.autograd.graph.saved_tensors_hooks(Saved, lambda saved: saved.tensor):
            result = graph.context_gradient(x, ["jpeg85"] * count, [1.] * count,
                lambda view, i: (view.sin().square() + view.cos()).mean())
        assert torch.isfinite(result).all()
        assert live["bytes"] == 0
        peaks.append(live["peak"])
    assert peaks[0] > 0 and len(set(peaks)) == 1


@pytest.mark.parametrize("values", [[], [1., 2.], [float("nan")], [float("inf")]])
def test_context_shape_and_nonfinite_weights_fail_closed(values):
    graph = importlib.import_module("riposte.context_graph")
    from riposte.errors import RiposteError
    with pytest.raises(RiposteError, match="OPTIMIZER_CONTEXTS_INVALID|OPTIMIZER_NONFINITE"):
        graph.context_gradient(torch.ones((1, 3, 16, 16)), ["identity"], values, lambda view, i: view.mean())


def test_zero_gradient_stays_zero_without_random_fallback():
    graph = importlib.import_module("riposte.context_graph")
    result = graph.context_gradient(torch.ones((1, 3, 16, 16)), ["identity", "jpeg85"], [0., 0.],
                                    lambda view, i: view.mean() * 0)
    assert torch.count_nonzero(result) == 0
