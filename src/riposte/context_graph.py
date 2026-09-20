"""Shared deterministic views, streamed model adjoints, one view VJP per group.

For detached context weights, sum_j w_j J_view.T @ grad_j equals
J_view.T @ sum_j w_j grad_j. This factors the implemented surrogate graph;
it does not certify a derivative of discrete JPEG or protection efficacy.
Callbacks must be pure for fixed input/context. No state survives a call.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING

from .errors import RiposteError
from .optimizer import _round_ste
from .views import differentiable_view

if TYPE_CHECKING:
    from torch import Tensor

ContextScore = Callable[["Tensor", int], "Tensor"]
ContextProgress = Callable[[int], None]


def context_groups(names: Sequence[str]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    groups: dict[str, list[int]] = {}
    for index, name in enumerate(names):
        groups.setdefault(name, []).append(index)
    if not groups:
        raise RiposteError("OPTIMIZER_CONTEXTS_INVALID")
    return tuple((name, tuple(indices)) for name, indices in groups.items())


def context_values(pixels: Tensor, names: Sequence[str], evaluate: ContextScore,
                   progress: ContextProgress | None = None) -> list[float]:
    """Evaluate every context, sharing one graph-free view; retain caller order."""
    import torch
    values = [0.] * len(names)
    completed = 0
    with torch.no_grad():
        for name, indices in context_groups(names):
            viewed = differentiable_view(pixels, name)
            for index in indices:
                completed += 1
                if progress:
                    progress(completed)
                value = evaluate(viewed, index)
                if value.ndim != 0 or not bool(torch.isfinite(value)):
                    raise RiposteError("OPTIMIZER_NONFINITE")
                values[index] = float(value.cpu())
    return values


def context_gradient(candidate: Tensor, names: Sequence[str], values: Sequence[float],
                     evaluate: ContextScore, progress: ContextProgress | None = None) -> Tensor:
    """Exact chain-rule factoring in real arithmetic; FP reductions may differ."""
    import torch
    groups = context_groups(names)
    if len(values) != len(names):
        raise RiposteError("OPTIMIZER_CONTEXTS_INVALID")
    numbers = torch.tensor(values, device=candidate.device, dtype=candidate.dtype)
    tau = numbers.abs().mean().clamp_min(1e-6)
    weights = torch.softmax(-numbers / tau, dim=0).detach()
    if not bool(torch.isfinite(numbers).all()) or not bool(torch.isfinite(weights).all()):
        raise RiposteError("OPTIMIZER_NONFINITE")
    total = torch.zeros_like(candidate)
    completed = 0
    for name, indices in groups:
        leaf = candidate.detach().requires_grad_(True)
        viewed = differentiable_view(_round_ste(leaf * 255) / 255, name)
        adjoint = torch.zeros_like(viewed)
        for index in indices:
            completed += 1
            if progress:
                progress(completed)
            model_input = viewed.detach().requires_grad_(True)
            value = evaluate(model_input, index)
            if value.ndim != 0 or not bool(torch.isfinite(value)):
                raise RiposteError("OPTIMIZER_NONFINITE")
            if not value.requires_grad:
                raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
            gradient = torch.autograd.grad(value, model_input, allow_unused=True)[0]
            if gradient is None:
                raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
            if not bool(torch.isfinite(gradient).all()):
                raise RiposteError("OPTIMIZER_NONFINITE")
            adjoint.add_(gradient.detach() * weights[index])
            del model_input, value, gradient
        gradient = torch.autograd.grad(viewed, leaf, grad_outputs=adjoint, allow_unused=True)[0]
        if gradient is None:
            raise RiposteError("MODEL_GRADIENT_UNAVAILABLE")
        if not bool(torch.isfinite(gradient).all()):
            raise RiposteError("OPTIMIZER_NONFINITE")
        total.add_(gradient.detach())
        del leaf, viewed, adjoint, gradient
    if not bool(torch.isfinite(total).all()):
        raise RiposteError("OPTIMIZER_NONFINITE")
    return total
