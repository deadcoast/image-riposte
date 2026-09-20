from collections.abc import Callable, Sequence
from _riposte_types import ModelTensor
from .errors import RiposteError as RiposteError
from .optimizer import _round_ste as _round_ste
from .views import differentiable_view as differentiable_view

ContextScore = Callable[[ModelTensor, int], ModelTensor]
ContextProgress = Callable[[int], None]

def context_groups(names: Sequence[str]) -> tuple[tuple[str, tuple[int, ...]], ...]: ...
def context_values(pixels: ModelTensor, names: Sequence[str], evaluate: ContextScore,
                   progress: ContextProgress | None = None) -> list[float]: ...
def context_gradient(candidate: ModelTensor, names: Sequence[str], values: Sequence[float],
                     evaluate: ContextScore, progress: ContextProgress | None = None) -> ModelTensor: ...
