"""Kontext contracts: synthetic loader fixtures and a tiny real-library pipeline."""
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest
from PIL import Image

from riposte.errors import RiposteError
from riposte.experiment import conditioning, experiment_status, review_packet
from riposte.generation import prepare_input


def test_modern_conditioning_has_no_sd_strength():
    options = conditioning('edit', {'kind': 'FLUX_KONTEXT_EDIT'})
    assert options['guidance_scale'] == 2.5 and 'strength' not in options
    assert options['true_cfg_scale'] == 1 and options['auto_resize'] is False


def test_modern_preparation_uses_explicit_bucket():
    result = prepare_input(Image.new('RGB', (32,32)), 'edit', {'kind':'FLUX_KONTEXT_EDIT'})
    assert result.size == (1024,1024)


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value),encoding='utf-8')


@pytest.fixture
def bundle(tmp_path):
    from riposte.kontext import COMPONENTS
    folder=tmp_path/'kontext'
    config={'_class_name':'FluxKontextPipeline', **{k:[lib,classes[0]] for k,(lib,classes) in COMPONENTS.items()}}
    config.update(image_encoder=[None,None],feature_extractor=[None,None])
    write(folder/'model_index.json',config)
    for part in COMPONENTS:
        write(folder/part/'config.json',{'private':'DO_NOT_DISCLOSE'})
    for part in ('vae','transformer','text_encoder','text_encoder_2'):
        (folder/part/'model.safetensors').write_bytes(b'SYNTHETIC_LOADER_FIXTURE')
    write(folder/'vae/config.json',{'block_out_channels':[32]*4,'latent_channels':16})
    write(folder/'transformer/config.json',{'in_channels':64,'guidance_embeds':True})
    (folder/'tokenizer_2/spiece.model').write_bytes(b'BINARY_TOKENIZER_FIXTURE')
    return folder


@pytest.fixture
def loader(monkeypatch):
    torch=pytest.importorskip('torch')
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    monkeypatch.setattr(torch.cuda,'is_bf16_supported',lambda **kw:True)
    original=torch.Generator
    monkeypatch.setattr(torch,'Generator',lambda device:original('cpu'))
    calls=[]
    class Pipeline:
        @classmethod
        def from_pretrained(cls,path,**kwargs):
            calls.append(('load',path,kwargs))
            return cls()
        def to(self,device):
            assert device=='cuda';return self
        def set_progress_bar_config(self,**kwargs): pass
        def __call__(self,**kwargs):
            calls.append(('call',kwargs))
            return SimpleNamespace(images=[kwargs['image'].copy()])
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(FluxKontextPipeline=Pipeline,
        StableDiffusionImg2ImgPipeline=Pipeline,StableDiffusionInpaintPipeline=Pipeline,StableVideoDiffusionPipeline=Pipeline))
    return Pipeline,calls


def test_fixed_local_backend_and_model_aware_calls(bundle,loader):
    from riposte.generation import LocalGenerator
    generator=LocalGenerator(bundle,'edit')
    image=prepare_input(Image.new('RGB',(64,32)),'edit',generator.identity)
    result=generator(image,7,2)
    assert result[0].size==image.size
    assert not generator.last_flags['content_filter_reported']
    load=loader[1][0][2]
    assert load['local_files_only'] and load['use_safetensors']
    assert str(load['torch_dtype'])=='torch.bfloat16'
    call=loader[1][1][1]
    assert 'strength' not in call and call['_auto_resize'] is False
    assert call['max_area']==image.width*image.height
    assert (call['width'],call['height'])==image.size
    assert call['generator'].initial_seed()==7
    assert generator.identity['kind']=='FLUX_KONTEXT_EDIT'
    assert str(bundle) not in json.dumps(generator.identity)
    assert 'DO_NOT_DISCLOSE' not in json.dumps(generator.identity)
    for task in ('video','inpaint'):
        with pytest.raises(RiposteError,match='ARCHITECTURE_UNSUPPORTED'):
            LocalGenerator(bundle,task)


@pytest.mark.parametrize('relative',['tokenizer_2/spiece.model','tokenizer/config.json','vae/model.safetensors','model_index.json'])
def test_every_loaded_asset_is_bound_across_loading(bundle,loader,relative):
    from riposte.kontext import KontextGenerator
    cls=loader[0]
    def mutate(cls,path,**kwargs):
        target=Path(path)/relative
        target.write_bytes(target.read_bytes()+b' ')
        return cls()
    cls.from_pretrained=classmethod(mutate)
    with pytest.raises(RiposteError,match='MODEL_BUNDLE_CHANGED'):
        KontextGenerator(bundle)


def test_named_assets_relocation_and_single_pass_weight_hashing(bundle,tmp_path,monkeypatch):
    from riposte.kontext import bundle_identity
    from riposte.models import model_fingerprint
    before=bundle_identity(bundle)
    relocated=tmp_path/'relocated';shutil.copytree(bundle,relocated)
    assert bundle_identity(relocated)==before
    weights=bundle/'vae/model.safetensors'
    weights.rename(bundle/'vae/renamed.safetensors')
    assert bundle_identity(bundle)!=before
    assert model_fingerprint(bundle/'vae')==before['component_sha256']['vae']
    opened=[]; original=Path.open
    def count(path,*args,**kwargs):
        if path.suffix=='.safetensors':opened.append(path)
        return original(path,*args,**kwargs)
    monkeypatch.setattr(Path,'open',count)
    bundle_identity(bundle)
    assert len(opened)==len(set(opened))==4
    (bundle/'tokenizer/PRIVATE_FILENAME.txt').write_text('PRIVATE_CONTENT')
    assert 'PRIVATE' not in json.dumps(bundle_identity(bundle))


@pytest.mark.parametrize('mutation',['role','unknown','missing','unsafe','layout','shard','subdirectory'])
def test_bundle_preflight_rejects_unadmitted_content(bundle,loader,mutation):
    from riposte.kontext import KontextGenerator
    config=json.loads((bundle/'model_index.json').read_text())
    if mutation=='role':config['vae']=['diffusers','UNet2DConditionModel']
    elif mutation=='unknown':config['custom']=['remote_package','ExecuteCode']
    elif mutation=='missing':del config['text_encoder_2']
    elif mutation=='unsafe':(bundle/'vae/pytorch_model.bin').write_bytes(b'not allowed')
    elif mutation=='layout':write(bundle/'vae/config.json',{'block_out_channels':[32]*3,'latent_channels':16})
    elif mutation=='shard':write(bundle/'vae/model.safetensors.index.json',{'weight_map':{'x':'../escape.safetensors'}})
    else:(bundle/'tokenizer/nested').mkdir()
    write(bundle/'model_index.json',config)
    with pytest.raises(RiposteError):KontextGenerator(bundle)
    assert not loader[1]


def test_cuda_and_native_bfloat16_are_explicit_gates(bundle,loader,monkeypatch):
    import torch
    from riposte.kontext import KontextGenerator
    monkeypatch.setattr(torch.cuda,'is_bf16_supported',lambda **kw:False)
    with pytest.raises(RiposteError,match='NATIVE_BFLOAT16'):KontextGenerator(bundle)
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    with pytest.raises(RiposteError,match='REQUIRES_CUDA'):KontextGenerator(bundle)
    assert not loader[1]


def test_real_ordinary_cohort_and_panel_plumbing(root,tmp_path,make_image,bundle,loader):
    from riposte.generation import controlled_generation
    from riposte.cohort import cohort_challenge
    from riposte.lab import compare_external
    from riposte.organizer import organize,plan
    from riposte.policy import Policy
    from riposte.store import catalog
    from riposte.review_panel import create_panel,panel_packet
    for index in range(2):make_image(root/f'{index}.png',size=(32,32),color=(90+index*30,100,150))
    policy=Policy(date_mode='modified');organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    trials=[compare_external(root,row['id'],root/row['relative']) for row in catalog(root)]
    run=controlled_generation(root,trials[0]['id'],bundle,seeds=(7,),views=('identity',),steps=1)
    status=experiment_status(root,run['id'])
    assert status['protocol']['conditioning']==run['conditioning']==conditioning('edit',run['model'])
    assert run['groups'][0]['prepared_input_size']==[1024,1024]
    assert len([c for c in loader[1] if c[0]=='call'])==5
    assert len({c[1]['generator'].initial_seed() for c in loader[1] if c[0]=='call'})==1
    cohort=cohort_challenge(root,[trials[1]['id']],bundle,1,seeds=(7,),views=('identity',),steps=1)
    assert cohort['protocol']['conditioning']==run['conditioning']
    panel=create_panel(root,[run['id'],cohort['members'][0]['run_id']])
    reviewer=next(iter(panel['protocol']['reviewers']))
    receipt=panel_packet(root,panel['protocol']['id'],reviewer)
    from zipfile import ZipFile
    with ZipFile(root/receipt['relative']) as archive:
        tasks=[json.loads(archive.read(name)) for name in archive.namelist() if name.endswith('task.json')]
        assert len(tasks)==10 and all(task==run['conditioning'] for task in tasks)


def test_real_tiny_random_pipeline_cpu_numeric_path(tmp_path,monkeypatch,request):
    """Actual library components and serialized weights; test-only CPU placement."""
    torch=pytest.importorskip('torch')
    from diffusers import FluxKontextPipeline,FluxTransformer2DModel,AutoencoderKL,FlowMatchEulerDiscreteScheduler
    from transformers import CLIPTokenizer,CLIPTextConfig,CLIPTextModel,T5Tokenizer,T5Config,T5EncoderModel
    from riposte.kontext import KontextGenerator
    rng_state=torch.get_rng_state()
    request.addfinalizer(lambda:torch.set_rng_state(rng_state))
    torch.manual_seed(21)
    clip=CLIPTokenizer(vocab={'<|startoftext|>':0,'<|endoftext|>':1,**{chr(97+i):i+2 for i in range(26)}},merges=[],model_max_length=77)
    t5=T5Tokenizer(vocab=[('<pad>',0.0),('</s>',0.0),('<unk>',0.0),('▁',0.0),*[(chr(97+i),-1.0) for i in range(26)]],extra_ids=0)
    pipeline=FluxKontextPipeline(
        scheduler=FlowMatchEulerDiscreteScheduler(),
        vae=AutoencoderKL(block_out_channels=(32,32,32,32),down_block_types=('DownEncoderBlock2D',)*4,
            up_block_types=('UpDecoderBlock2D',)*4,latent_channels=16,norm_num_groups=8,sample_size=32,
            scaling_factor=.3611,shift_factor=.1159),
        text_encoder=CLIPTextModel(CLIPTextConfig(vocab_size=len(clip),hidden_size=32,intermediate_size=64,
            num_hidden_layers=1,num_attention_heads=4,bos_token_id=0,eos_token_id=1,pad_token_id=1)),
        tokenizer=clip,
        text_encoder_2=T5EncoderModel(T5Config(vocab_size=len(t5),d_model=32,d_ff=64,num_layers=1,num_heads=4,d_kv=8)),
        tokenizer_2=t5,
        transformer=FluxTransformer2DModel(in_channels=64,out_channels=64,num_layers=1,num_single_layers=1,
            attention_head_dim=32,num_attention_heads=2,joint_attention_dim=32,pooled_projection_dim=32,
            guidance_embeds=True,axes_dims_rope=(8,12,12)))
    folder=tmp_path/'tiny-real-kontext';pipeline.save_pretrained(folder,safe_serialization=True)
    del pipeline
    original_to=FluxKontextPipeline.to
    def cpu(self,*args,**kwargs):
        if args==('cuda',):return original_to(self,'cpu',dtype=torch.float32)
        return original_to(self,*args,**kwargs)
    monkeypatch.setattr(FluxKontextPipeline,'to',cpu)
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    monkeypatch.setattr(torch.cuda,'is_bf16_supported',lambda **kw:True)
    original_generator=torch.Generator
    monkeypatch.setattr(torch,'Generator',lambda device:original_generator('cpu'))
    generator=KontextGenerator(folder)
    assert str(generator.pipeline._execution_device)=='cpu'
    shapes=[]
    def capture(module,args,kwargs):
        shapes.append(tuple(kwargs['hidden_states'].shape))
    handle=generator.pipeline.transformer.register_forward_pre_hook(capture,with_kwargs=True)
    request.addfinalizer(handle.remove)
    image=Image.new('RGB',(32,48),(80,110,140))
    first=generator(image,7,2)[0];second=generator(image,7,2)[0]
    assert first.size==second.size==image.size and first.tobytes()==second.tobytes()
    assert first.tobytes()!=image.tobytes()
    changed=generator(Image.new('RGB',image.size,(190,40,80)),7,2)[0]
    assert changed.tobytes()!=first.tobytes()
    assert shapes==[(1,12,64)]*6  # Six target plus six image-context tokens, two steps per call.
    assert not generator.last_flags['content_filter_reported']


def test_linked_component_is_rejected_before_loader(bundle,loader,monkeypatch):
    import riposte.kontext as module
    original=module.is_link
    monkeypatch.setattr(module,'is_link',lambda path:path==bundle/'tokenizer' or original(path))
    with pytest.raises(RiposteError,match='LOCAL_MODEL_DIRECTORY_REQUIRED'):
        module.KontextGenerator(bundle)
    assert not loader[1]


@pytest.mark.parametrize('size',[(0,1),(1,0),(-1,2),(True,2),(1.5,2)])
def test_invalid_input_geometry_is_rejected(size):
    from riposte.kontext import target_size
    with pytest.raises(RiposteError,match='INPUT_INVALID'):target_size(*size)


def test_wrong_pipeline_output_and_failed_load_do_not_become_success(bundle,loader):
    from riposte.kontext import KontextGenerator
    generator=KontextGenerator(bundle)
    loader[0].__call__=lambda self,**kwargs:SimpleNamespace(images=[Image.new('RGB',(16,16))])
    with pytest.raises(RiposteError,match='OUTPUT_INVALID'):
        generator(Image.new('RGB',(32,32)),7,1)
    def fail(cls,*args,**kwargs):raise OSError('private model path')
    loader[0].from_pretrained=classmethod(fail)
    with pytest.raises(RiposteError,match='LOCAL_PIPELINE_LOAD_FAILED'):
        KontextGenerator(bundle)
