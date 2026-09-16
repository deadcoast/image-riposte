import numpy as np
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.optimizer import protect,GuardConfig,jpeg_surrogate,eot,LocalVAE

torch=pytest.importorskip('torch')
torch.set_num_threads(1)
class ToyEncoder:
    device='cpu'
    def __call__(self,x):
        # Synthetic differentiable test oracle, NOT a generative AI model.
        return torch.cat((x,x*x,torch.sin(x*3)),dim=1)
def fixture_image():
    rng=np.random.default_rng(41);a=rng.integers(20,230,(32,48,3),dtype=np.uint8);a[:6]=255;return Image.fromarray(a)
@pytest.mark.parametrize('epsilon',[1,2,4,8,16])
def test_budget_and_white_canvas(epsilon):
    image=fixture_image();out,r=protect(image,[ToyEncoder()],GuardConfig(epsilon_255=epsilon,steps=3))
    a,b=np.asarray(image,dtype=np.int16),np.asarray(out,dtype=np.int16)
    assert np.abs(a-b).max()<=epsilon;assert np.array_equal(a[:4],b[:4]);assert r['ai_protection']=='UNVERIFIED';assert r['evidence_level']=='ENCODER_PROXY_ONLY';assert len(r['proxy_evaluation'])==4

def test_deterministic_seed():
    config=GuardConfig(steps=4);image=fixture_image();a,_=protect(image,[ToyEncoder()],config);b,_=protect(image,[ToyEncoder()],config);assert np.array_equal(a,b)
def test_ensemble():
    _,r=protect(fixture_image(),[ToyEncoder(),ToyEncoder()],GuardConfig(steps=2));assert r['encoders']==2;assert len(r['proxy_evaluation'])==8
@pytest.mark.parametrize('quality',[50,75,85,95,100])
def test_jpeg_differentiability(quality):
    x=torch.rand((1,3,29,45),requires_grad=True);y=jpeg_surrogate(x,quality);assert y.shape==x.shape;assert torch.isfinite(y).all();y.mean().backward();assert torch.isfinite(x.grad).all();assert x.grad.abs().sum()>0
@pytest.mark.parametrize('name',['identity','resize75','jpeg85','crop90'])
def test_eot_shape(name):
    x=torch.rand((1,3,32,48));assert eot(x,name).shape==x.shape
@pytest.mark.parametrize('kwargs',[{'epsilon_255':0},{'epsilon_255':17},{'steps':0},{'steps':1001},{'step_255':0},{'seed':-1}])
def test_invalid_config(kwargs):
    with pytest.raises(RiposteError):GuardConfig(**kwargs)
def test_none_rejected():
    with pytest.raises(RiposteError,match='NO_MODEL'):protect(fixture_image(),[])
def test_proxy_changes_do_not_certify():
    _,r=protect(fixture_image(),[ToyEncoder()],GuardConfig(steps=5))
    assert min(i['relative_feature_mse'] for i in r['proxy_evaluation'])>0
    assert r['ai_protection']=='UNVERIFIED'
def test_nonfinite_model():
    class Bad:
        device='cpu'
        def __call__(self,x):return x*float('nan')
    with pytest.raises(RiposteError,match='NONFINITE'):protect(fixture_image(),[Bad()],GuardConfig(steps=1))

def test_local_loader_offline_and_no_empty_directory_fallback(tmp_path,monkeypatch):
    import sys,os
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(AutoencoderKL=object))
    for name in ('HF_HUB_OFFLINE','HF_HUB_DISABLE_TELEMETRY','TRANSFORMERS_OFFLINE'):
        monkeypatch.delenv(name,raising=False)
    with pytest.raises(RiposteError,match='LOCAL_VAE_DIRECTORY_REQUIRED'):
        LocalVAE(tmp_path)
    for name in ('HF_HUB_OFFLINE','HF_HUB_DISABLE_TELEMETRY','TRANSFORMERS_OFFLINE'):
        assert os.environ[name]=='1'
