"""Control-flow tests using stub generators, not pretrained-model efficacy tests."""
from riposte.organizer import plan as _sort_preview
import sys
from types import SimpleNamespace
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.policy import Policy
from riposte.organizer import organize
from riposte.store import catalog
from riposte.lab import compare_external
from riposte.benchmark import run_benchmark
from riposte.sanitize import png_audit, encode_clean

@pytest.fixture
def trial(root,tmp_path,make_image):
    make_image(root/'input.png');organize(root,Policy(date_mode='modified'), plan_id=_sort_preview(root, Policy(date_mode='modified'))["plan_id"])
    candidate=make_image(tmp_path/'candidate.png',color=(31,91,151))
    return compare_external(root,catalog(root)[0]['id'],candidate)

@pytest.fixture
def stub_models(monkeypatch,tmp_path):
    torch=pytest.importorskip('torch')
    calls=[]
    class StubPipeline:
        @classmethod
        def from_pretrained(cls,*args,**kwargs):
            assert kwargs['local_files_only'] is True
            assert kwargs['use_safetensors'] is True
            calls.append(('load',kwargs));return cls()
        def to(self,device):
            assert device=='cuda';return self
        def set_progress_bar_config(self,**kwargs):pass
        def __call__(self,*args,**kwargs):
            image=args[0] if args else kwargs['image']
            calls.append(('generate',kwargs['generator'].initial_seed()))
            return SimpleNamespace(images=[image.copy()],frames=[[image.copy(),image.copy()]])
    monkeypatch.setitem(sys.modules,'diffusers',SimpleNamespace(
        StableDiffusionImg2ImgPipeline=StubPipeline,StableVideoDiffusionPipeline=StubPipeline))
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True)
    generator=torch.Generator
    monkeypatch.setattr(torch,'Generator',lambda device:generator('cpu'))
    model=tmp_path/'model';model.mkdir();(model/'model_index.json').write_text('{}')
    return model,calls

@pytest.mark.parametrize('task',['edit','video'])
def test_paired_runner_control_flow(root,trial,stub_models,task):
    model,calls=stub_models
    result=run_benchmark(root,trial['id'],model,task=task,seeds=(7,),transforms=('identity','jpeg85'),steps=1)
    assert result['evidence_level']=='PAIRED_GENERATIONS_UNSCORED'
    assert result['ai_protection']=='UNVERIFIED'
    assert len(result['pairs'])==2
    assert [seed for kind,seed in calls if kind=='generate']==[7,7,7,7]
    files=list((root/'.riposte/benchmarks'/result['id']).rglob('*.png'))
    assert len(files)==(4 if task=='edit' else 8)
    for path in files:assert png_audit(path.read_bytes())['date']==trial['date']

def test_runner_requires_cuda(root,trial,stub_models,monkeypatch):
    import torch
    monkeypatch.setattr(torch.cuda,'is_available',lambda:False)
    with pytest.raises(RiposteError,match='REQUIRES_CUDA'):
        run_benchmark(root,trial['id'],stub_models[0])

@pytest.mark.parametrize('kwargs',[{'seeds':()},{'seeds':(-1,)},{'steps':0},{'steps':101}])
def test_runner_invalid_parameters(root,trial,stub_models,kwargs):
    with pytest.raises(RiposteError,match='PARAMETERS_INVALID'):
        run_benchmark(root,trial['id'],stub_models[0],**kwargs)

def test_runner_rejects_changed_candidate(root,trial,stub_models):
    (root/f".riposte/lab/{trial['id']}/candidate.png").write_bytes(
        encode_clean(Image.new('RGB',(64,48),'red'),trial['date']))
    with pytest.raises(RiposteError,match='ARTIFACT_CHANGED'):
        run_benchmark(root,trial['id'],stub_models[0])

def test_runner_requires_clean_checkpoint(root,trial,stub_models):
    (root/'unprocessed.xmp').write_text('PRIVATE_FIXTURE_PAYLOAD')
    with pytest.raises(RiposteError,match='CHECKPOINT'):
        run_benchmark(root,trial['id'],stub_models[0])
