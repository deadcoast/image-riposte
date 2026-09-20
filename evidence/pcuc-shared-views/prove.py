"""Independent sequential VJP reference and retained-tensor measurements."""
import hashlib
import json
from pathlib import Path
import torch
from riposte.context_graph import context_gradient, context_values
from riposte.optimizer import _round_ste
from riposte.views import differentiable_view, keep_mask

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    torch.set_num_threads(1)
    comparisons = []
    for dtype in (torch.float32, torch.float64):
        for repetitions in (1, 4):
            for height, width in ((17, 25), (32, 48)):
                x = torch.rand((1, 3, height, width), generator=torch.Generator().manual_seed(753), dtype=dtype) * .8 + .1
                names = ["identity", "jpeg85", "resize75"] * repetitions

                def score(view, index):
                    keep = keep_mask(view.shape[-2:], ("whole", "center", "left")[index % 3], 93 + index)
                    y = view * keep + .5 * (1 - keep)
                    return (y.sin().square() + .2 * y.pow(3)).mean() * (1 + index) - .3 * index

                values = context_values(x.mul(255).round() / 255, names, score)
                numbers = torch.tensor(values, dtype=dtype)
                weights = torch.softmax(-numbers / numbers.abs().mean().clamp_min(1e-6), 0)
                expected = torch.zeros_like(x)
                # Independent old execution: a fresh full view+model graph per context.
                for index, name in enumerate(names):
                    leaf = x.detach().requires_grad_(True)
                    value = score(differentiable_view(_round_ste(leaf * 255) / 255, name), index)
                    gradient, = torch.autograd.grad(value, leaf)
                    expected += weights[index] * gradient
                observed = context_gradient(x, names, values, score)
                tolerance = 2e-8 if dtype == torch.float32 else 2e-12
                torch.testing.assert_close(observed, expected, rtol=2e-5, atol=tolerance)
                difference = observed - expected
                comparisons.append({"dtype": str(dtype), "contexts": len(names), "height": height, "width": width,
                    "atol": tolerance, "rtol": 2e-5, "max_absolute_error": float(difference.abs().max()),
                    "relative_l2_error": float(difference.norm() / expected.norm()),
                    "different_gradient_signs": int((observed.sign() != expected.sign()).sum())})
    memory = []
    for count in (1, 4, 16):
        state = {"live": 0, "peak": 0}

        class Saved:
            def __init__(self, tensor):
                self.tensor = tensor.detach()
                self.size = tensor.numel() * tensor.element_size()
                state["live"] += self.size
                state["peak"] = max(state["peak"], state["live"])

            def __del__(self):
                state["live"] -= self.size

        with torch.autograd.graph.saved_tensors_hooks(Saved, lambda obj: obj.tensor):
            context_gradient(torch.full((1, 3, 24, 32), .4), ["jpeg85"] * count, [1.] * count,
                lambda view, index: (view.sin().square() + view.cos()).mean())
        memory.append({"contexts": count, "peak_saved_tensor_bytes": state["peak"], "remaining_bytes": state["live"]})
    assert len({row["peak_saved_tensor_bytes"] for row in memory}) == 1
    assert all(row["remaining_bytes"] == 0 for row in memory)
    sources = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    return {"result": "PASS", "comparisons": comparisons, "saved_tensors": memory, "sources": sources,
            "cuda_available": torch.cuda.is_available(), "torch": torch.__version__,
            "scope": "CPU surrogate-graph algebra, finite-sample gradient error and logical autograd saved-tensor storage. Saved tensor aliases may be counted more than once; excludes all model weights, references, allocator/RSS and device memory."}


if __name__ == "__main__":
    (HERE / "proof.json").write_text(json.dumps(main(), indent=2) + "\n", encoding="utf-8")
