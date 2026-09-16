import numpy as np
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.coupled import CoupledConfig, protect_coupled
from riposte.views import image_tensor,budget_map

torch=pytest.importorskip('torch');torch.set_num_threads(1)
class Oracle:
    device='cpu'
    identity={'kind':'SYNTHETIC_TEST_ORACLE','weights_sha256':'a'*64}
    def __call__(self,x):
        import torch.nn.functional as F
        return F.avg_pool2d(x,2)+.15*F.max_pool2d(x,2)

class Probe:
    device='cpu';identity={'kind':'SYNTHETIC_TEST_PROBE'}
    def __call__(self,x,keep,seed,fraction,prompt):
        return Oracle()(x*keep+.5*(1-keep))*(1+fraction)

def drawing():
    arr=np.random.default_rng(12).integers(40,210,(24,32,3),dtype=np.uint8)
    arr[:6,:]=255
    return Image.fromarray(arr)

@pytest.mark.parametrize('probe',[None,Probe()])
def test_coupled_real_gradients_8bit_budget_and_branch_contract(probe):
    image=drawing();events=[]
    result,report=protect_coupled(image,[Oracle()],CoupledConfig(steps=2),probe=probe,progress=events.append)
    a=np.asarray(image,dtype=np.int16);b=np.asarray(result,dtype=np.int16)
    budget=(budget_map(image_tensor(image),4)*255).round()[0].permute(1,2,0).numpy()
    assert np.all(np.abs(a-b)<=budget)
    assert result.tobytes()!=image.tobytes()
    assert np.array_equal(a[:3],b[:3])
    assert report['ai_protection']=='UNVERIFIED'
    assert len(report['proxy_evaluation'])==(13 if probe else 9)
    assert report['jpeg_forward']=='PILLOW_REAL_420'
    assert report['evidence_level']==('EARLY_DENOISER_PROXY_ONLY' if probe else 'MASKED_ENCODER_PROXY_ONLY')
    assert events and events[-1]['processed']==2

def test_same_seed_deterministic_synthetic_and_multiple_models():
    c=CoupledConfig(steps=1)
    a,ra=protect_coupled(drawing(),[Oracle(),Oracle()],c)
    b,rb=protect_coupled(drawing(),[Oracle(),Oracle()],c)
    assert a.tobytes()==b.tobytes() and ra==rb
    assert len(ra['proxy_evaluation'])==18

@pytest.mark.parametrize('kwargs',[{'epsilon_255':0},{'epsilon_255':True},{'steps':0},{'steps':True},
 {'step_255':float('nan')},{'frequency_weight':float('nan')},{'frequency_weight':2},{'seed':-1},
 {'seed':True},{'seed':2**32},{'preserve_white':1}])
def test_invalid_configs(kwargs):
    with pytest.raises(RiposteError,match='PARAMETERS'):CoupledConfig(**kwargs)

def test_missing_model_is_not_noise_fallback():
    with pytest.raises(RiposteError,match='NO_MODEL'):protect_coupled(drawing(),[])

def test_all_white_has_no_editable_budget():
    with pytest.raises(RiposteError,match='NO_EDITABLE'):protect_coupled(Image.new('RGB',(24,24),'white'),[Oracle()])

def test_constant_model_fails_instead_of_storing_noise():
    class Constant(Oracle):
        def __call__(self,x):return x*0
    with pytest.raises(RiposteError,match='ZERO_GRADIENT'):protect_coupled(drawing(),[Constant()],CoupledConfig(steps=1))

def test_detached_model_fails():
    class Detached(Oracle):
        def __call__(self,x):return x.detach()
    with pytest.raises(RiposteError,match='GRADIENT_UNAVAILABLE'):protect_coupled(drawing(),[Detached()],CoupledConfig(steps=1))

def test_nonfinite_model_fails():
    class Nonfinite(Oracle):
        def __call__(self,x):return x*float('nan')
    with pytest.raises(RiposteError,match='NONFINITE'):protect_coupled(drawing(),[Nonfinite()],CoupledConfig(steps=1))

def test_cancellation_at_branch_boundary():
    def stop(event):
        if event['phase']=='Optimizing coupled contexts':raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='JOB_CANCELLED'):protect_coupled(drawing(),[Oracle()],CoupledConfig(steps=2),progress=stop)

def test_cross_device_is_explicit_error():
    other=Oracle();other.device='not-the-same-device'
    with pytest.raises(RiposteError,match='DEVICE_MISMATCH'):protect_coupled(drawing(),[Oracle(),other])
