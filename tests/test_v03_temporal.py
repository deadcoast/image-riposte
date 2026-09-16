from types import SimpleNamespace as NS
import pytest
torch = pytest.importorskip("torch")
import torch.nn.functional as F
from riposte.errors import RiposteError
from riposte.temporal import TemporalConfig, LocalTemporalProbe, letterbox_tensor, v_prediction_original
from riposte.release_guard import temporal_energy

@pytest.mark.parametrize('kw',[{'width':65},{'height':63},{'frames':1},{'frames':26},{'fps':0},{'motion_bucket':256},{'noise_augmentation':float('nan')},{'guidance_max':6},{'generation_steps':1},{'width':True}])
def test_temporal_config_validation(kw):
    with pytest.raises(RiposteError):TemporalConfig(**kw)

def test_differentiable_letterbox_preserves_aspect_and_white():
    x=torch.full((1,3,32,64),.3,requires_grad=True)
    y=letterbox_tensor(x,64,64)
    assert y.shape==(1,3,64,64) and torch.all(y[:,:,:16]==1) and torch.allclose(y[:,:,16:48],x)
    y.sum().backward();assert torch.allclose(x.grad,torch.ones_like(x))

def test_v_prediction_uses_correct_euler_original_formula():
    a=torch.tensor([1.,3.]);v=torch.tensor([2.,4.])
    assert torch.allclose(v_prediction_original(a,v,2),a/5-v*2/(5**.5))

@pytest.fixture
def probe():
    p=LocalTemporalProbe.__new__(LocalTemporalProbe)
    p.config=TemporalConfig(width=64,height=64,frames=3)
    p.device='cpu';p.dtype=torch.float32;p.clip_size=224;p.factor=8;p.sigma=5.;p.initial_sigma=5.;p.timestep=torch.tensor(1.)
    p.mean=torch.tensor([.48,.45,.4])[None,:,None,None];p.std=torch.tensor([.26,.26,.27])[None,:,None,None]
    class VAE:
        def encode(self,x):
            z=F.avg_pool2d(x,8);z=torch.cat((z,z.mean(1,keepdim=True)),1)
            return NS(latent_dist=NS(mode=lambda:z))
    class CLIP:
        def __call__(self,x):return NS(image_embeds=x.mean((2,3)))
    class UNet:
        def __init__(self):self.calls=[]
        def __call__(self,x,t,encoder_hidden_states,added_time_ids):
            self.calls.append({'grad_enabled':torch.is_grad_enabled(),'shape':list(x.shape),'time':added_time_ids.detach().clone(),'conditioning':x[:,:,4:].detach().clone()})
            e=encoder_hidden_states.mean((1,2))[:,None,None,None,None]
            return NS(sample=.1*x[:,:,:4]+.2*x[:,:,4:]+e)
    p.vae=VAE();p.image_encoder=CLIP();p.unet=UNet()
    return p

def test_actual_adapter_graph_has_input_gradient_and_shared_seed(probe):
    x=torch.linspace(.1,.9,3*32*48).reshape(1,3,32,48).requires_grad_(True)
    a=probe(x,7);b=probe(x,7)
    assert a.shape==(1,3,4,8,8) and torch.equal(a,b)
    loss=temporal_energy(a);g=torch.autograd.grad(loss,x)[0]
    assert torch.isfinite(g).all() and (g!=0).any()
    assert [c['grad_enabled'] for c in probe.unet.calls]==[False,True,False,True]
    assert probe.unet.calls[0]['shape']==[1,3,8,8,8]
    assert torch.all(probe.unet.calls[0]['conditioning']==0)
    assert torch.allclose(probe.unet.calls[1]['time'],torch.tensor([[6.,127.,.02]]))

def test_no_global_rng_mutation_and_different_seeds(probe):
    x=torch.full((1,3,32,48),.4)
    before=torch.get_rng_state().clone();a=probe(x,1);b=probe(x,2)
    assert not torch.equal(a,b) and torch.equal(before,torch.get_rng_state())

@pytest.mark.parametrize('seed',[-1,2**32,True])
def test_probe_rejects_invalid_seed(probe,seed):
    with pytest.raises(RiposteError):probe(torch.zeros(1,3,64,64),seed)

@pytest.fixture
def local_tree(tmp_path):
    import json
    root=tmp_path/'model';root.mkdir()
    index={'_class_name':'StableVideoDiffusionPipeline','vae':['diffusers','AutoencoderKLTemporalDecoder'],
        'unet':['diffusers','UNetSpatioTemporalConditionModel'],'image_encoder':['transformers','CLIPVisionModelWithProjection'],
        'scheduler':['diffusers','EulerDiscreteScheduler']}
    (root/'model_index.json').write_text(json.dumps(index))
    for part in ['vae','unet','image_encoder','scheduler','feature_extractor']:(root/part).mkdir()
    for part in ['vae','unet','image_encoder']:(root/part/'diffusion_pytorch_model.safetensors').write_bytes(b'SYNTHETIC_WEIGHTS_NOT_A_PRETRAINED_CHECKPOINT')
    (root/'unet/config.json').write_text(json.dumps({'in_channels':8,'out_channels':4}))
    (root/'scheduler/scheduler_config.json').write_text(json.dumps({'prediction_type':'v_prediction'}))
    (root/'feature_extractor/preprocessor_config.json').write_text(json.dumps({'image_mean':[.48,.45,.4],'image_std':[.26,.26,.27]}))
    return root

@pytest.fixture
def loaders(monkeypatch):
    import sys
    calls=[]
    class Component:
        config=NS(block_out_channels=[1,2,3,4],image_size=224)
        @classmethod
        def from_pretrained(cls,path,**kw):calls.append((path,kw));return cls()
        def to(self,*a):return self
        def eval(self):return self
        def requires_grad_(self,v):assert v is False
    class Scheduler:
        @classmethod
        def from_pretrained(cls,path,**kw):calls.append((path,kw));return cls()
        def set_timesteps(self,n,device):self.sigmas=torch.tensor([5.,1.]);self.init_noise_sigma=5.;self.timesteps=torch.tensor([1.,0.])
    monkeypatch.setitem(sys.modules,'diffusers',NS(AutoencoderKLTemporalDecoder=Component,UNetSpatioTemporalConditionModel=Component,EulerDiscreteScheduler=Scheduler))
    monkeypatch.setitem(sys.modules,'transformers',NS(CLIPVisionModelWithProjection=Component))
    return calls

def test_fixed_class_loader_offline_and_safe_weight_contract(local_tree,loaders,monkeypatch):
    monkeypatch.delenv('HF_HUB_OFFLINE',raising=False)
    import os,json
    p=LocalTemporalProbe(local_tree,'cpu')
    assert len(loaders)==4 and os.environ['HF_HUB_OFFLINE']=='1'
    assert all(k['local_files_only'] for _,k in loaders)
    assert all(k['use_safetensors'] for _,k in loaders[:3])
    assert p.identity['text_conditioned'] is False and p.identity['ai_protection']=='UNVERIFIED'
    assert str(local_tree) not in json.dumps(p.identity)
    assert p.identity['scope']=='FIRST_STEP_PREDICTED_LATENTS_NOT_GENERATED_VIDEO'

@pytest.mark.parametrize('file,key,value,code',[
    ('model_index.json','_class_name','CustomRemotePipeline','ARCHITECTURE'),
    ('model_index.json','unet',['custom','UnsafeUNet'],'ARCHITECTURE'),
    ('unet/config.json','in_channels',9,'CHANNELS'),
    ('unet/config.json','out_channels',8,'CHANNELS'),
    ('scheduler/scheduler_config.json','prediction_type','epsilon','V_PREDICTION'),
    ('feature_extractor/preprocessor_config.json','image_mean',[0,1],'NORMALIZATION'),
    ('feature_extractor/preprocessor_config.json','image_std',[0,0,0],'NORMALIZATION'),
    ('feature_extractor/preprocessor_config.json','image_std',[.2,'PRIVATE',.3],'NORMALIZATION')])
def test_loader_architecture_and_normalization_allowlists(local_tree,loaders,file,key,value,code):
    import json
    f=local_tree/file;data=json.loads(f.read_text());data[key]=value;f.write_text(json.dumps(data))
    with pytest.raises(RiposteError,match=code):LocalTemporalProbe(local_tree,'cpu')
    assert not loaders

def test_loader_requires_safetensors_and_rejects_linked_components(local_tree,loaders,tmp_path):
    (local_tree/'vae/diffusion_pytorch_model.safetensors').unlink()
    with pytest.raises(RiposteError,match='SAFETENSORS'):LocalTemporalProbe(local_tree,'cpu')
    (local_tree/'vae/link').symlink_to(tmp_path)
    with pytest.raises(RiposteError,match='DIRECTORY'):LocalTemporalProbe(local_tree,'cpu')
    assert not loaders
