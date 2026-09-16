import json
import numpy as np
import pytest
from PIL import Image
from riposte.errors import RiposteError
from riposte.qualification import evaluate_pair,qualify_trial,evaluations
from riposte.views import TRAIN_VIEWS
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog
from riposte.lab import compare_external,trial_pixels
from riposte.sanitize import png_audit,encode_clean

torch=pytest.importorskip('torch');torch.set_num_threads(1)
class Oracle:
    device='cpu';identity={'kind':'SYNTHETIC_TEST_ORACLE','weights_sha256':'a'*64}
    def __call__(self,x):return torch.nn.functional.avg_pool2d(x,2)

def pair():
    a=np.random.default_rng(5).integers(30,200,(24,32,3),dtype=np.uint8)
    return Image.fromarray(a),Image.fromarray(a+3)

@pytest.mark.parametrize('known',[True,False])
def test_evidence_scope_controls_and_holdout_protocol(known):
    a,b=pair();r=evaluate_pair(a,b,[Oracle()], [Oracle.identity],
        optimization_views=list(TRAIN_VIEWS) if known else None,optimization_masks=['whole','center','left'] if known else None)
    assert len(r['rows'])==24 and r['ai_protection']=='UNVERIFIED'
    assert r['models'][0]['relation_to_optimization']=='SAME_OPTIMIZATION_WEIGHTS'
    assert r['summary']['heldout_transform_cells']==(15 if known else 0)
    assert r['control']['per_channel_magnitude_matched']
    assert not any(row['mask_scope']=='HELD_OUT_MASK_FAMILY' for row in r['rows']) if not known else True
    if not known:assert r['status']=='PROTOCOL_UNKNOWN_SCOPED_COMPARISON'
    json.dumps(r,allow_nan=False)

def test_zero_delta_not_misreported_as_advantage():
    a,_=pair();r=evaluate_pair(a,a,[Oracle()],optimization_views=list(TRAIN_VIEWS),optimization_masks=['whole'])
    assert r['summary']['cells_above_all_controls']==0
    assert r['status']=='NO_HELDOUT_PROXY_ADVANTAGE'
    assert all(row['ratio_to_strongest_control'] is None for row in r['rows'])

@pytest.mark.parametrize('training,expected',[([], 'RELATION_NOT_ESTABLISHED'),([{'weights_sha256':'b'*64}],'DIFFERENT_WEIGHTS_ARCHITECTURE_NOT_ESTABLISHED')])
def test_different_weights_not_falsely_heldout_architecture(training,expected):
    r=evaluate_pair(*pair(),[Oracle()],training)
    assert r['models'][0]['relation_to_optimization']==expected

@pytest.mark.parametrize('seeds',[(1,),(1,1),(1,-1),(1,2**32)])
def test_invalid_control_seeds(seeds):
    with pytest.raises(RiposteError,match='SEEDS'):evaluate_pair(*pair(),[Oracle()],control_seeds=seeds)

def test_missing_encoder_rejected():
    with pytest.raises(RiposteError,match='NO_MODEL'):evaluate_pair(*pair(),[])

def test_nonfinite_encoder_rejected():
    class Bad(Oracle):
        def __call__(self,x):return x*float('nan')
    with pytest.raises(RiposteError,match='NONFINITE'):evaluate_pair(*pair(),[Bad()])

@pytest.fixture
def trial(root,tmp_path,make_image):
    make_image(root/'a.png',size=(32,24));organize(root,Policy(date_mode='modified'))
    other=make_image(tmp_path/'other.png',size=(32,24),color=(32,92,152))
    return compare_external(root,catalog(root)[0]['id'],other)

def test_qualification_committed_sequenced_date_only(root,trial,monkeypatch,tmp_path):
    import riposte.models as models
    monkeypatch.setattr(models,'LocalEncoder',lambda *a,**k:Oracle())
    a=qualify_trial(root,trial['id'],[tmp_path]);b=qualify_trial(root,trial['id'],[tmp_path])
    assert [r['sequence'] for r in evaluations(root,trial['id'])]==[1,2]
    assert not a['optimization_protocol']['views_known']
    assert a['candidate_sha256']==trial['artifact_sha256']['candidate']
    files=list((root/'.riposte/lab'/trial['id']/'evaluations').rglob('*.png'));assert len(files)==6
    assert all(png_audit(p.read_bytes())['date']==trial['date'] for p in files)
    assert str(tmp_path) not in json.dumps(a)

def test_qualify_artifact_changed_is_blocked(root,trial,tmp_path,monkeypatch):
    path=root/f".riposte/lab/{trial['id']}/candidate.png"
    path.write_bytes(encode_clean(Image.new('RGB',(32,24),'red'),trial['date']))
    with pytest.raises(RiposteError,match='ARTIFACT_CHANGED'):qualify_trial(root,trial['id'],[tmp_path])
    with pytest.raises(RiposteError,match='ARTIFACT_CHANGED'):trial_pixels(root,trial['id'],'clean','jpeg85')

def test_cancel_does_not_commit_evaluation(root,trial,monkeypatch,tmp_path):
    import riposte.models as models
    monkeypatch.setattr(models,'LocalEncoder',lambda *a,**k:Oracle())
    def progress(update):raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='CANCELLED'):qualify_trial(root,trial['id'],[tmp_path],progress=progress)
    assert not evaluations(root,trial['id'])

def test_report_failure_removes_control_artifacts(root,trial,monkeypatch,tmp_path):
    import riposte.models as models
    import riposte.store as store
    monkeypatch.setattr(models,'LocalEncoder',lambda *a,**k:Oracle())
    def fail(*args,**kwargs):raise OSError('FAIL')
    monkeypatch.setattr(store,'atomic_json_write',fail)
    with pytest.raises(OSError):qualify_trial(root,trial['id'],[tmp_path])
    assert not list((root/'.riposte/lab'/trial['id']).rglob('control-*.png'))
