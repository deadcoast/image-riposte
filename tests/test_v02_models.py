import json
import sys
from types import SimpleNamespace
import pytest
from riposte.errors import RiposteError
from riposte.models import inspect_vae,read_config,model_fingerprint,runtime_capabilities,select_device,LocalEncoder,LocalInpaintProbe

def folder(tmp_path,kind='AutoencoderKL'):
    p=tmp_path/'model';p.mkdir();(p/'config.json').write_text(json.dumps({'_class_name':kind,'private':'DO_NOT_PERSIST_CONFIG_PAYLOAD'}))
    (p/'diffusion_pytorch_model.safetensors').write_bytes(b'not-real-weights-file-preflight-only')
    return p

@pytest.mark.parametrize('kind',['AutoencoderKL','AutoencoderTiny'])
def test_file_preflight_not_execution_or_metadata_dump(tmp_path,kind):
    p=folder(tmp_path,kind);r=inspect_vae(p,True)
    assert r['preflight']=='FILES_PRESENT_NOT_EXECUTED' and r['kind']==kind
    assert r['ai_protection']=='UNVERIFIED' and len(r['weights_sha256'])==64
    text=json.dumps(r);assert str(tmp_path) not in text and 'DO_NOT_PERSIST' not in text

def test_preflight_unsupported_class(tmp_path):
    with pytest.raises(RiposteError,match='ARCHITECTURE'):inspect_vae(folder(tmp_path,'UnknownClass'))

@pytest.mark.parametrize('value',['[]','bad-json','"text"'])
def test_config_must_be_bounded_mapping(tmp_path,value):
    p=tmp_path/'config.json';p.write_text(value)
    with pytest.raises(RiposteError,match='CONFIG_INVALID'):read_config(p)

def test_large_config_rejected(tmp_path):
    p=tmp_path/'config.json';p.write_text(' '*1_048_577)
    with pytest.raises(RiposteError,match='CONFIG_INVALID'):read_config(p)

def test_symlink_weights_rejected(tmp_path):
    p=folder(tmp_path);q=p/'diffusion_pytorch_model.safetensors';q.unlink()
    real=tmp_path/'not-a-model';real.write_bytes(b'content');q.symlink_to(real)
    with pytest.raises(RiposteError,match='SAFETENSORS'):inspect_vae(p)

@pytest.mark.parametrize('value',['../elsewhere.safetensors','..\\elsewhere.safetensors','not-present.safetensors',None])
def test_weight_index_cannot_escape_or_point_to_missing_file(tmp_path,value):
    p=folder(tmp_path);(p/'model.safetensors.index.json').write_text(json.dumps({'weight_map':{'weight':value}}))
    with pytest.raises(RiposteError,match='INDEX_INVALID'):inspect_vae(p)

def test_weight_digest_changes_on_weight_edit(tmp_path):
    p=folder(tmp_path);a=model_fingerprint(p);(p/'diffusion_pytorch_model.safetensors').write_bytes(b'different')
    assert model_fingerprint(p)!=a

@pytest.mark.parametrize('kind',['AutoencoderKL','AutoencoderTiny'])
def test_fixed_encoder_loader_and_gradient_with_stub_model(tmp_path,monkeypatch,kind):
    torch=pytest.importorskip('torch');p=folder(tmp_path,kind);calls=[]
    class Model(torch.nn.Module):
        config=SimpleNamespace(block_out_channels=(1,2,3),encoder_block_out_channels=(1,2,3))
        @classmethod
        def from_pretrained(cls,path,**kw):
            assert kw['local_files_only'] and kw['use_safetensors'];calls.append(path);return cls()
        def encode(self,x):
            assert x.shape[-1]%4==0 and x.shape[-2]%4==0
            return SimpleNamespace(latent_dist=SimpleNamespace(mean=x),latents=x)
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(AutoencoderKL=Model,AutoencoderTiny=Model))
    model=LocalEncoder(p,'cpu');x=torch.rand(1,3,19,23,requires_grad=True);result=model(x);result.mean().backward()
    assert x.grad is not None and calls==[str(p)]
    assert model.factor==4

def test_probe_real_tensor_conditioning_shape_noise_seed_and_gradient():
    torch=pytest.importorskip('torch')
    import torch.nn.functional as F
    p=LocalInpaintProbe.__new__(LocalInpaintProbe);p.factor=2;p.scaling=.18;p.timesteps=1000;p.embeddings={'background':torch.ones(1,4,8)}
    captured=[]
    class VAE:
        def encode(self,x):
            y=F.avg_pool2d(x,2);return SimpleNamespace(latent_dist=SimpleNamespace(mean=torch.cat((y,y.mean(1,keepdim=True)),1)))
    class UNet:
        def __call__(self,x,t,encoder_hidden_states):
            captured.append((x.detach().clone(),int(t)));return SimpleNamespace(sample=x[:,:4]+x[:,5:9])
    p.vae=VAE();p.unet=UNet();x=torch.rand(1,3,23,29,requires_grad=True);keep=torch.ones(1,1,23,29);keep[:,:,8:13,4:12]=0
    a=p(x,keep,7,.9,'background');b=p(x,keep,7,.9,'background')
    assert torch.equal(a,b) and captured[0][0].shape[1]==9 and captured[0][1]==899
    a.square().mean().backward();assert torch.isfinite(x.grad).all() and (x.grad!=0).any()
    assert torch.all(x.grad[:,:,8:13,4:12]==0)
    with pytest.raises(RiposteError,match='CONTEXT'):p(x,keep,7,.1,'background')

def test_explicit_device_unavailable_and_runtime_safe(monkeypatch):
    torch=pytest.importorskip('torch');monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    assert select_device('cpu')=='cpu'
    with pytest.raises(RiposteError,match='UNAVAILABLE'):select_device('cuda')
    with pytest.raises(RiposteError,match='INVALID'):select_device('magic')
    assert runtime_capabilities()['pretrained_qualification']=='NOT_IMPLIED_BY_PREFLIGHT'
