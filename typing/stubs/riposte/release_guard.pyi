from .spatial import ArtistMask as ArtistMask
from _riposte_types import EncoderT
# Source-derived external stub; see typing/README.md for scope.
from PIL.Image import Image as _Image
from _riposte_types import Report, ModelTensor, Encoder, InpaintProbe, TemporalProbe
from _riposte_types import Progress as _Progress
from .coupled import Branch as Branch, _branches as _branches, _features as _features
from .coupled import _view_features as _view_features
from .context_graph import context_groups as context_groups, context_values as context_values, context_gradient as context_gradient
from .errors import RiposteError as RiposteError
from .optimizer import _round_ste as _round_ste
from .quality import QualityLimits as QualityLimits, quality_report as quality_report, spatial_budget as spatial_budget
from .views import TRAIN_VIEWS as TRAIN_VIEWS, differentiable_view as differentiable_view, image_tensor as image_tensor, spectral_direction as spectral_direction, tensor_image as tensor_image
from PIL import Image as Image
from dataclasses import dataclass

@dataclass(frozen=True)
class ReleaseConfig:
    steps: int = ...
    restarts: int = ...
    seed: int = ...
    step_255: float = ...
    checkpoint_every: int = ...
    frequency_weight: float = ...

    def __post_init__(self) -> None: ...

def temporal_energy(frames: ModelTensor) -> ModelTensor: ...

def protect_release(image: Image.Image, encoders: list[EncoderT], config: ReleaseConfig=..., limits: QualityLimits=..., probe: InpaintProbe | None=None, temporal: TemporalProbe | None=None, progress: _Progress | None=None, *, artist_mask: ArtistMask | None=None) -> tuple[_Image, Report]: ...
