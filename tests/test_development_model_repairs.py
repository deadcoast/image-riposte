"""Real CPU autograd with synthetic adapters; no pretrained efficacy claim."""
from pathlib import Path

import pytest
from PIL import Image

from riposte import publication as p
from riposte.errors import RiposteError
from riposte.optimizer import protect, GuardConfig
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog


@pytest.fixture
def torch():
    module = pytest.importorskip('torch')
    module.set_num_threads(1)
    return module


@pytest.mark.parametrize('kind', ['constant', 'detached', 'unrelated'])
def test_legacy_optimizer_rejects_unusable_gradient(torch, kind):
    class Encoder:
        device = 'cpu'
        def __call__(self, x):
            if kind == 'constant':
                return x * 0 + 1
            if kind == 'detached':
                return x.detach()
            return torch.ones_like(x, requires_grad=True)

    with pytest.raises(RiposteError, match='ZERO_GRADIENT_NO_CANDIDATE'):
        protect(Image.new('RGB', (32, 32), (100, 130, 150)), [Encoder()], GuardConfig(steps=2))


def test_legacy_optimizer_rejects_white_canvas(torch):
    class Encoder:
        device = 'cpu'
        def __call__(self, x): return x.square()

    with pytest.raises(RiposteError, match='NO_EDITABLE_PIXEL_BUDGET'):
        protect(Image.new('RGB', (32, 32), 'white'), [Encoder()], GuardConfig(steps=2))


@pytest.mark.parametrize('optional', ['inpaint', 'temporal'])
@pytest.mark.parametrize('behavior', ['valid', 'constant', 'detached', 'nonfinite', 'failure'])
def test_optional_gradients_execute_before_request_commit(root, monkeypatch, torch, optional, behavior):
    import riposte.models as models
    import riposte.temporal as temporal
    Image.new('RGB', (64, 64), (100, 130, 150)).save(root / 'input.png')
    assert organize(root, Policy(date_mode='modified'))['checkpoint'] == 'COMPLETE'
    identifiers = [catalog(root)[0]['id']]
    calls = []

    class Encoder:
        device = 'cpu'
        identity = {'kind': 'SYNTHETIC_ENCODER'}
        def __init__(self, *args): pass
        def __call__(self, x): return x.square() + .1 * x

    class Optional:
        device = 'cpu'
        identity = {'kind': 'SYNTHETIC_OPTIONAL'}
        def __init__(self, *args): pass
        def __call__(self, x, *args):
            assert not list(root.glob('.riposte/publishing/*/request.json'))
            calls.append('forward')
            if behavior == 'failure': raise RuntimeError('PRIVATE_MODEL_FAILURE')
            y = x * 0 + 1 if behavior == 'constant' else x.square()
            if behavior == 'detached': y = y.detach()
            if behavior == 'nonfinite': y = y * float('nan')
            if y.requires_grad:
                y.register_hook(lambda gradient: calls.append('backward'))
            return torch.stack([y, y * 2], dim=1) if optional == 'temporal' else y

    monkeypatch.setattr(models, 'LocalEncoder', Encoder)
    monkeypatch.setattr(models, 'LocalInpaintProbe', Optional)
    monkeypatch.setattr(temporal, 'LocalTemporalProbe', Optional)

    def committed(workspace, request, loaded, progress):
        assert 'backward' in calls
        assert (workspace / '.riposte/publishing' / request['id'] / 'request.json').is_file()
        return request

    monkeypatch.setattr(p, '_run', committed)
    kwargs = {'pipeline_dir' if optional == 'inpaint' else 'temporal_dir': Path('synthetic')}
    if behavior == 'valid':
        result = p.start_publication(root, identifiers, [Path('synthetic')], **kwargs)
        assert len(result['execution_probes']) == 2
        assert result['ai_protection'] == 'UNVERIFIED'
    else:
        with pytest.raises(RiposteError, match='MODEL_(GRADIENT_UNAVAILABLE|EXECUTION_PROBE_FAILED)'):
            p.start_publication(root, identifiers, [Path('synthetic')], **kwargs)
        assert not list(root.glob('.riposte/publishing/*/request.json'))
    assert 'forward' in calls
