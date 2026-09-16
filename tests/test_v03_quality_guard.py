import math
import numpy as np
import pytest
torch = pytest.importorskip("torch")
from PIL import Image
from riposte.errors import RiposteError
from riposte.quality import QualityLimits, quality_report, spatial_budget, _lab
from riposte.release_guard import ReleaseConfig, protect_release, temporal_energy
from riposte.runtime_probe import probe_encoder

class Oracle:
    device = 'cpu'
    identity = {'kind':'SYNTHETIC_TEST_ORACLE', 'weights_sha256':'1'*64}
    def __call__(self,x): return x.square()+.15*x

@pytest.fixture
def art(): return Image.fromarray(np.random.default_rng(10).integers(25,225,(32,40,3),dtype=np.uint8))

@pytest.mark.parametrize('field,value', [('epsilon_255',0),('epsilon_255',17),('epsilon_255',True),('tile_size',0),('tile_size',True),('preserve_white',1),('rms_fraction',0),('rms_fraction',float('nan')),('delta_e76_p95',float('inf')),('delta_e76_p95',0)])
def test_quality_limits(field,value):
    with pytest.raises(RiposteError): QualityLimits(**{field:value})

@pytest.mark.parametrize('field,value', [('steps',0),('steps',True),('restarts',0),('restarts',5),('seed',-1),('seed',2**32),('step_255',float('nan')),('frequency_weight',2),('checkpoint_every',0)])
def test_guard_limits(field,value):
    with pytest.raises(RiposteError): ReleaseConfig(**{field:value})

def test_lab_reference_white_black():
    v=_lab(np.array([[[255,255,255],[0,0,0]]]))
    assert v[0,0,0]==pytest.approx(100,abs=1e-4)
    assert np.abs(v[0,0,1:]).max()<1e-4
    assert np.max(np.abs(v[0,1]))<1e-8

def test_unchanged_pixels_not_protection(art):
    r=quality_report(art,art)
    assert r['status']=='PASS' and r['identical_pixels'] and r['ai_protection']=='UNVERIFIED'

def test_white_and_edges_receive_tight_budget():
    a=np.full((24,32,3),255,np.uint8);a[:,16:]=0
    caps=spatial_budget(Image.fromarray(a),QualityLimits())
    assert caps[12,2]==0 and caps[12,15]==2 and caps[12,16]==2 and caps[12,25]==4

def test_white_change_blocks():
    r=quality_report(Image.new('RGB',(32,32),'white'),Image.new('RGB',(32,32),(254,255,255)))
    assert r['status']=='BLOCKED' and r['protected_pixels_changed']==1024

def test_local_damage_not_hidden_by_global_average():
    a=np.full((128,128,3),120,np.uint8);b=a.copy();b[:32,:32]+=4
    r=quality_report(Image.fromarray(a),Image.fromarray(b))
    assert r['rmse_255']==1 and r['worst_tile_rmse_255']==4
    assert 'LOCAL_RMS_LIMIT_EXCEEDED' in r['blockers']

def test_colour_gate_is_separate():
    a=Image.new('RGB',(32,32),(130,110,100));b=Image.new('RGB',(32,32),(132,110,100))
    assert quality_report(a,b,QualityLimits(delta_e76_p95=.1))['blockers']==['COLOUR_DIFFERENCE_LIMIT_EXCEEDED']

def test_real_cpu_guard_selects_feasible_updated_pixels(art):
    before=np.asarray(art).copy()
    result,r=protect_release(art,[Oracle()],ReleaseConfig(steps=8,restarts=2))
    assert r['quality']['status']=='PASS' and not np.array_equal(before,np.asarray(result))
    assert np.array_equal(before,np.asarray(art)) and not r['selection_is_heldout']
    choices=[(p['min_context_score'],p['mean_context_score'],p['restart'],p['step']) for p in r['trace'] if p['eligible']]
    best=max(choices)
    assert (r['selection']['restart'],r['selection']['step'])==best[2:]
    assert min(x['score'] for x in r['contexts'])>r['selection']['initial_min_context_score']
    assert r['ai_protection']=='UNVERIFIED' and len(r['contexts'])==9
    caps=spatial_budget(art,QualityLimits())
    assert (np.abs(np.asarray(result,dtype=int)-before)<=caps[...,None]).all()

def test_seeded_protection_reproducible_without_global_rng(art):
    torch.manual_seed(219);before=torch.get_rng_state().clone()
    a,ra=protect_release(art,[Oracle()],ReleaseConfig(steps=3,restarts=1))
    b,rb=protect_release(art,[Oracle()],ReleaseConfig(steps=3,restarts=1))
    assert a.tobytes()==b.tobytes() and ra==rb and torch.equal(before,torch.get_rng_state())

@pytest.mark.parametrize('mode,code',[('zero','ZERO_GRADIENT'),('detached','MODEL_GRADIENT'),('nan','NONFINITE')])
def test_unusable_oracles_never_become_noise_candidates(art,mode,code):
    class Bad(Oracle):
        def __call__(self,x): return x*0 if mode=='zero' else x.detach() if mode=='detached' else x*float('nan')
    with pytest.raises(RiposteError,match=code):protect_release(art,[Bad()],ReleaseConfig(steps=2,restarts=1))

def test_no_model_and_no_editable_budget(art):
    with pytest.raises(RiposteError,match='NO_MODEL'): protect_release(art,[])
    with pytest.raises(RiposteError,match='NO_EDITABLE'):protect_release(Image.new('RGB',(32,32),'white'),[Oracle()])

def test_strict_quality_refuses_instead_of_degrading(art):
    with pytest.raises(RiposteError,match='NO_IMPROVED'):
        protect_release(art,[Oracle()],ReleaseConfig(steps=3,restarts=1),QualityLimits(rms_fraction=.1,delta_e76_p95=.1))

def test_cancellation_reaches_each_model_context(art):
    events=[]
    def progress(p):
        events.append(p)
        if 'Optimizing' in p['phase']:raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='JOB_CANCELLED'):protect_release(art,[Oracle()],progress=progress)
    assert len(events)>10

def test_execution_probe_checks_actual_input_gradient():
    r=probe_encoder(Oracle())
    assert r['finite_gradient'] and r['nonzero_gradient'] and r['input_shape']==[1,3,64,64]
    assert r['ai_protection']=='UNVERIFIED'
    class Detached(Oracle):
        def __call__(self,x):return x.detach()
    with pytest.raises(RiposteError,match='GRADIENT'):probe_encoder(Detached())

@pytest.mark.parametrize('shape',[(1,3,8,8),(1,1,3,8,8)])
def test_temporal_feature_axis_validated(shape):
    with pytest.raises(RiposteError,match='TEMPORAL_FEATURE_SHAPE'):temporal_energy(torch.zeros(shape))

def test_temporal_energy_exact_and_differentiable():
    x=torch.tensor([0.,1.,3.]).reshape(1,3,1,1,1).requires_grad_(True)
    y=temporal_energy(x);assert float(y.detach())==2.5
    y.backward();assert torch.allclose(x.grad.flatten(),torch.tensor([-1.,-1.,2.]))

def test_zero_temporal_reference_rejected(art):
    class Static(Oracle):
        def __call__(self,x,seed):return x[:,None].repeat(1,3,1,1,1)
    with pytest.raises(RiposteError,match='NO_SIGNAL'):protect_release(art,[Oracle()],temporal=Static())

def test_temporal_and_image_objectives_share_final_budget(art):
    class Temporal(Oracle):
        def __call__(self,x,seed):
            # Synthetic differentiable temporal oracle; not a pretrained model.
            z=(1+x.square())[:,None]
            return z*torch.tensor([.7,1.,1.5])[None,:,None,None,None]
    result,r=protect_release(art,[Oracle()],ReleaseConfig(steps=8,restarts=1),temporal=Temporal())
    assert r['evidence_level']=='TEMPORAL_AND_IMAGE_COMPONENT_PROXY'
    assert len(r['contexts'])==11 and r['quality']['status']=='PASS'
    assert all(c['score']>0 for c in r['contexts'])
