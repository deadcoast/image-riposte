import numpy as np
import json
from pathlib import Path
import pytest
from PIL import Image
from riposte import __version__
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog
from riposte.lab import compare_external
from riposte.generation import controlled_generation,generation_runs,generation_frame,prepare_input,frame_motion
from riposte.sanitize import png_audit,encode_clean

@pytest.fixture
def trial(root,tmp_path,make_image):
    make_image(root/'a.png',size=(32,24));organize(root,Policy(date_mode='modified'))
    path=make_image(tmp_path/'candidate.png',size=(32,24),color=(33,93,153))
    return compare_external(root,catalog(root)[0]['id'],path)

@pytest.fixture
def stub(monkeypatch):
    import riposte.generation as generation
    calls=[]
    class Generator:
        identity={'kind':'SYNTHETIC_TEST_GENERATOR'}
        def __init__(self,path,task):self.task=task
        def __call__(self,image,seed,steps):
            calls.append((seed,steps,image.size,image.tobytes()))
            return [image.copy()] if self.task!='video' else [image.copy(),image.copy()]
    monkeypatch.setattr(generation,'LocalGenerator',Generator)
    return calls

@pytest.mark.parametrize('task',['edit','inpaint','video'])
def test_five_arm_generation_has_matched_seeds_date_only_frames(root,tmp_path,trial,stub,task):
    result=controlled_generation(root,trial['id'],tmp_path,task,seeds=(7,),views=('identity','jpeg70'),steps=1)
    assert result['application_version'] == __version__
    assert result['evidence_level']=='CONTROLLED_GENERATIONS_UNSCORED' and result['ai_protection']=='UNVERIFIED'
    assert len(result['groups'])==2 and len(stub)==10
    assert all(call[0]==7 for call in stub)
    assert all(set(g['roles'])=={'clean','candidate','control_1','control_2','control_3'} for g in result['groups'])
    assert all(g['review']=='HUMAN_REVIEW_REQUIRED' for g in result['groups'])
    assert len(result['artifacts'])==(20 if task=='video' else 10)
    assert generation_runs(root,trial['id'])[0]['id']==result['id']
    for file in result['artifacts']:
        audit=png_audit(generation_frame(root,result['id'],file));assert audit['date']==trial['date']
    json.dumps(result,allow_nan=False)
    assert str(tmp_path) not in json.dumps(result)

def test_temporal_metrics_descriptive_not_success():
    a=Image.new('RGB',(16,16),(50,50,50));b=Image.new('RGB',a.size,(54,54,54))
    assert frame_motion([a]) is None and frame_motion([a,b])==4

def test_generation_real_codec_then_resize_records_mismatch(root,tmp_path,trial,stub):
    result=controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('jpeg70',),steps=1)
    assert 'Before publication transforms' in result['controls']['matching_scope']
    assert set(result['groups'][0]['prepared_input_fidelity'])=={'candidate','control_1','control_2','control_3'}

def test_generation_frame_changed_not_served(root,tmp_path,trial,stub):
    result=controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    relative=next(iter(result['artifacts']))
    path=root/f".riposte/generations/{result['id']}/{relative}"
    path.write_bytes(encode_clean(Image.new('RGB',(32,24),'red'),trial['date']))
    with pytest.raises(RiposteError,match='FRAME_CHANGED'):generation_frame(root,result['id'],relative)

def test_generation_frame_escape_not_served(root,tmp_path,trial,stub):
    result=controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    with pytest.raises(RiposteError,match='NOT_FOUND'):generation_frame(root,result['id'],'../../catalog.sqlite3')

def test_cancel_after_write_rolls_back_run(root,tmp_path,trial,stub):
    def stop(update):
        if update.get('processed',0)>=1:raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='CANCELLED'):controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1,progress=stop)
    assert not generation_runs(root,trial['id'])
    assert not list((root/'.riposte/generations').rglob('*.png'))

def test_mismatched_frame_count_rolls_back(root,tmp_path,trial,monkeypatch):
    import riposte.generation as generation
    class Generator:
        identity={'kind':'SYNTHETIC_TEST_GENERATOR'}
        def __init__(self,*args):self.calls=0
        def __call__(self,image,seed,steps):
            self.calls+=1;return [image.copy()]*(1 if self.calls==1 else 2)
    monkeypatch.setattr(generation,'LocalGenerator',Generator)
    with pytest.raises(RiposteError,match='FRAME_COUNT_MISMATCH'):controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    assert not generation_runs(root,trial['id'])

@pytest.mark.parametrize('kwargs',[{'seeds':()},{'seeds':(7,7)},{'seeds':(-1,)},{'seeds':(True,)},
 {'views':()},{'views':('identity','identity')},{'views':('made-up-platform',)},{'steps':0},{'steps':True},{'task':'unknown'}])
def test_invalid_generation_parameters(root,tmp_path,trial,kwargs):
    with pytest.raises(RiposteError,match='PARAMETERS_INVALID'):controlled_generation(root,trial['id'],tmp_path,**kwargs)

def test_generation_sequence_monotonic(root,tmp_path,trial,stub):
    a=controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    b=controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    assert [r['sequence'] for r in generation_runs(root,trial['id'])]==[1,2]

def test_generation_requires_clean_checkpoint(root,tmp_path,trial,stub):
    (root/'unprocessed.xmp').write_text('PRIVATE_FIXTURE_PAYLOAD')
    with pytest.raises(RiposteError,match='CHECKPOINT'):controlled_generation(root,trial['id'],tmp_path,seeds=(7,),views=('identity',),steps=1)
    assert not stub

@pytest.mark.parametrize('task',['edit','inpaint','video'])
def test_fixed_local_generation_loader_with_stub_components(tmp_path,monkeypatch,task):
    """Exercise actual adapter code; the returned model remains a test double."""
    import sys
    from types import SimpleNamespace
    from riposte.generation import LocalGenerator
    torch=pytest.importorskip('torch')
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    original_generator=torch.Generator
    monkeypatch.setattr(torch,'Generator',lambda device:original_generator('cpu'))
    model=tmp_path/'model';model.mkdir()
    config={'_class_name':{'edit':'StableDiffusionImg2ImgPipeline','inpaint':'StableDiffusionInpaintPipeline','video':'StableVideoDiffusionPipeline'}[task],
        'vae':['diffusers','AutoencoderKLTemporalDecoder' if task=='video' else 'AutoencoderKL'],
        'unet':['diffusers','UNetSpatioTemporalConditionModel' if task=='video' else 'UNet2DConditionModel'],
        'scheduler':['diffusers','EulerDiscreteScheduler']}
    config.update({'image_encoder':['transformers','CLIPVisionModelWithProjection'],'feature_extractor':['transformers','CLIPImageProcessor']}
        if task=='video' else {'text_encoder':['transformers','CLIPTextModel'],'tokenizer':['transformers','CLIPTokenizer']})
    (model/'model_index.json').write_text(json.dumps(config))
    for name in config:
        if not name.startswith('_'):
            (model/name).mkdir()
    for name in ('vae','unet'):(model/name/'model.safetensors').write_bytes(b'stub-only')
    (model/'unet/config.json').write_text('{"in_channels":9}')
    calls=[]
    class Pipeline:
        @classmethod
        def from_pretrained(cls,path,**kw):
            assert kw['local_files_only'] and kw['use_safetensors'];return cls()
        def to(self,device):assert device=='cuda';return self
        def set_progress_bar_config(self,**kw):pass
        def __call__(self,*args,**kw):
            image=args[0] if args else kw['image'];calls.append(kw)
            return SimpleNamespace(images=[image],frames=[[image,image]],nsfw_content_detected=[False])
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(StableDiffusionImg2ImgPipeline=Pipeline,StableDiffusionInpaintPipeline=Pipeline,StableVideoDiffusionPipeline=Pipeline))
    generator=LocalGenerator(model,task);result=generator(Image.new('RGB',(32,24),'gray'),7,2)
    assert result and calls[0]['generator'].initial_seed()==7
    assert ('mask_image' in calls[0])==(task=='inpaint')
    if task=='inpaint':assert set(np.asarray(calls[0]['mask_image']).ravel())=={0,255}
    assert generator.last_flags['content_filter_reported']==(task!='video')
    config['_class_name']='UnrecognizedRemotePipeline';(model/'model_index.json').write_text(json.dumps(config))
    with pytest.raises(RiposteError,match='ARCHITECTURE_UNSUPPORTED'):LocalGenerator(model,task)
