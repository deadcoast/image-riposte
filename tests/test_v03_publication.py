from riposte.organizer import plan as _sort_preview
import hashlib, io, json
from pathlib import Path
from zipfile import ZipFile
import numpy as np
import pytest
from PIL import Image
from riposte import publication as p
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog, state_relative
from riposte.sanitize import encode_clean, png_audit
from riposte.release_guard import ReleaseConfig
from riposte.quality import QualityLimits

class Oracle:
    device='cpu'
    identity={'kind':'SYNTHETIC_TEST_ORACLE','weights_sha256':'a'*64}
    def __call__(self,x):return x.square()+.15*x

@pytest.fixture
def prepared(root,make_image):
    for i,size in enumerate([(96,80),(64,48),(128,80)]):make_image(root/f'prior/sub/image-{i}.png',size=size,color=(30+i*15,90,150))
    organize(root,Policy(date_mode='modified'), plan_id=_sort_preview(root, Policy(date_mode='modified'))["plan_id"])
    return [r['id'] for r in catalog(root)]

@pytest.fixture
def loaded(monkeypatch):
    pytest.importorskip('torch')
    import riposte.models as models
    calls=[]
    def load(folder,device):
        calls.append(str(folder));return Oracle()
    monkeypatch.setattr(models,'LocalEncoder',load)
    return calls

@pytest.fixture
def recipe():return p.PublishRecipe((64,),ReleaseConfig(steps=3,restarts=1),QualityLimits())

@pytest.fixture
def batch(root,prepared,loaded,recipe):return p.start_publication(root,prepared,[Path('LOCAL_SYNTHETIC_FIXTURE')],recipe)

def item_dir(root,batch,item):return root/state_relative(root,f"publishing/{batch['id']}/items/{item['id']}")
def accept(root,batch,ids=None):return p.review_publication(root,batch['id'],ids or [x['id'] for x in batch['items']],'ACCEPTED',True,True)

@pytest.mark.parametrize('edges',[(),(1,),(64,64),(64,128,256,512),(True,),[64]])
def test_recipe_rejects_invalid_edges(edges):
    with pytest.raises(RiposteError):p.PublishRecipe(edges)

def test_recipe_round_trip_and_unknown_field(recipe):
    assert p.PublishRecipe.from_dict(json.loads(json.dumps(recipe.public())))==recipe
    with pytest.raises(RiposteError):p.PublishRecipe.from_dict({'unwanted':'private'})

def test_plan_readonly_no_upscale_duplicates(root,prepared):
    before=sorted(str(x.relative_to(root)) for x in root.rglob('*'))
    v=p.publication_plan(root,prepared,p.PublishRecipe((512,1024,2048)))
    assert v['outputs']==3 and v['duplicate_renders_avoided']==6 and not v['writes']
    assert before==sorted(str(x.relative_to(root)) for x in root.rglob('*'))

@pytest.mark.parametrize('selection',[[],['a'*32,'a'*32],['../../private']])
def test_bad_selection(root,prepared,selection):
    with pytest.raises(RiposteError):p.publication_plan(root,selection)

def test_batch_reuses_models_keeps_masters_no_lab_dependency(root,prepared,loaded,recipe):
    before={r['relative']:(root/r['relative']).read_bytes() for r in catalog(root)}
    b=p.start_publication(root,prepared,[Path('LOCAL_SYNTHETIC_FIXTURE')],recipe)
    assert len(loaded)==1 and b['counts']=={'PENDING':0,'READY_FOR_REVIEW':3,'BLOCKED':0,'ACCEPTED':0}
    assert b['master_changes']==0 and not (root/'.riposte/lab').exists()
    assert all((root/f).read_bytes()==data for f,data in before.items())
    assert 'LOCAL_SYNTHETIC_FIXTURE' not in '\n'.join(x.read_text() for x in (root/'.riposte/publishing').rglob('*.json'))

def test_each_actual_resolution_optimized_independently(root,prepared,loaded,monkeypatch):
    called=[]; original=p.protect_release
    def run(im,*a,**kw):called.append(im.size);return original(im,*a,**kw)
    monkeypatch.setattr(p,'protect_release',run)
    b=p.start_publication(root,[prepared[0]],[Path('model')],p.PublishRecipe((64,80,2048),ReleaseConfig(steps=2,restarts=1)))
    assert len(called)==3 and len(set(called))==3 and b['counts']['READY_FOR_REVIEW']==3

def test_missing_model_never_produces_noise_or_publish_record(root,prepared,recipe):
    with pytest.raises(RiposteError,match='NO_MODEL'):p.start_publication(root,prepared,[],recipe)
    assert not (root/'.riposte/publishing').exists()

def test_failure_is_per_item_and_error_is_code_only(root,prepared,loaded,recipe,monkeypatch):
    original=p.protect_release;counter=[]
    def run(*a,**kw):
        counter.append(1)
        if len(counter)==2:raise RuntimeError('PRIVATE_SOURCE_PATH_MUST_NOT_PERSIST')
        return original(*a,**kw)
    monkeypatch.setattr(p,'protect_release',run)
    b=p.start_publication(root,prepared,[Path('model')],recipe)
    assert b['counts']['READY_FOR_REVIEW']==2 and b['counts']['BLOCKED']==1
    assert b['items'][1]['code']=='PUBLICATION_ITEM_FAILED'
    assert not item_dir(root,b,b['items'][1]).exists()
    assert 'PRIVATE_SOURCE' not in json.dumps(b)

def test_cancel_resume_skips_committed_pixels_and_reuses_seed(root,prepared,loaded,recipe):
    def stop(update):
        if update.get('item')==2:raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='CANCELLED'):p.start_publication(root,prepared,[Path('model')],recipe,progress=stop)
    b=p.publication_status(root,p.publications(root)[0]['id'])
    assert b['status']=='INTERRUPTED' and b['counts']['READY_FOR_REVIEW']==1
    committed=(item_dir(root,b,b['items'][0])/'report.json').read_bytes()
    done=p.resume_publication(root,b['id'],[Path('same-model')])
    assert done['counts']['READY_FOR_REVIEW']==3 and len(loaded)==2
    assert committed==(item_dir(root,b,b['items'][0])/'report.json').read_bytes()
    assert not (root/'.riposte/operation.lock').exists()

def test_recovery_removes_only_uncommitted_clean_orphans(root,prepared,loaded,recipe):
    def stop(u):
        if u.get('item')==1:raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError):p.start_publication(root,prepared,[Path('model')],recipe,progress=stop)
    b=p.publication_status(root,p.publications(root)[0]['id']);folder=item_dir(root,b,b['items'][0]);folder.mkdir(parents=True)
    (folder/'clean.png').write_bytes(encode_clean(Image.new('RGB',(32,32),'red'),'2025-03-12'))
    done=p.resume_publication(root,b['id'],[Path('model')])
    assert done['counts']['READY_FOR_REVIEW']==3

def test_resume_requires_same_recorded_models(root,batch,monkeypatch):
    import riposte.models as models
    class Other(Oracle):identity={'kind':'SYNTHETIC_TEST_ORACLE','weights_sha256':'b'*64}
    monkeypatch.setattr(models,'LocalEncoder',lambda *a:Other())
    with pytest.raises(RiposteError,match='MODEL_MISMATCH'):p.resume_publication(root,batch['id'],[Path('model')])

@pytest.mark.parametrize('visual,ack',[(False,False),(True,False),(False,True)])
def test_review_requires_both_acknowledgements(root,batch,visual,ack):
    with pytest.raises(RiposteError,match='ACKNOWLEDGEMENT'):p.review_publication(root,batch['id'],[batch['items'][0]['id']],'ACCEPTED',visual,ack)

def test_package_only_explicitly_accepted_date_only_images(root,batch):
    with pytest.raises(RiposteError,match='NO_APPROVED'):p.publication_zip(root,batch['id'])
    ids=[batch['items'][0]['id'],batch['items'][2]['id']];r=accept(root,batch,ids)
    assert r['counts']['ACCEPTED']==2
    data=p.publication_zip(root,batch['id'])
    with ZipFile(io.BytesIO(data)) as z:
        assert len(z.namelist())==2 and not z.comment
        for info in z.infolist():
            assert info.filename.endswith('.png') and info.date_time[3:]==(0,0,0) and not info.extra and not info.comment
            assert info.filename.startswith('2025/March/SML/')
            audit=png_audit(z.read(info));assert audit['date']=='2025-03-12'
            assert audit['sha256'] in [t['artifact_sha256']['candidate'] for t in batch['items']]
    assert 'SYNTHETIC' not in data.decode('latin1')

def test_review_rejection_revokes_download(root,batch):
    accept(root,batch)
    p.review_publication(root,batch['id'],[x['id'] for x in batch['items']],'REJECTED')
    with pytest.raises(RiposteError,match='NO_APPROVED'):p.publication_zip(root,batch['id'])

def test_whole_review_validated_before_any_write(root,batch):
    selected=batch['items'][:2]
    candidate=item_dir(root,batch,selected[1])/'candidate.png';candidate.write_bytes(encode_clean(Image.new('RGB',(64,53),'black'),'2025-03-12'))
    with pytest.raises(RiposteError):accept(root,batch,[x['id'] for x in selected])
    assert not (root/'.riposte/publishing'/batch['id']/'reviews').exists()

@pytest.mark.parametrize('kind',['clean','candidate'])
def test_changed_artifacts_block_serving_and_pack(root,batch,kind):
    accept(root,batch)
    path=item_dir(root,batch,batch['items'][0])/f'{kind}.png'
    path.write_bytes(encode_clean(Image.new('RGB',(32,32),'black'),'2025-03-12'))
    with pytest.raises(RiposteError):p.publication_pixels(root,batch['id'],batch['items'][0]['id'])
    with pytest.raises(RiposteError):p.publication_zip(root,batch['id'])

def test_changed_report_requires_new_review(root,batch):
    accept(root,batch)
    path=item_dir(root,batch,batch['items'][0])/'report.json'
    report=json.loads(path.read_text());report['guard']['note']='TEST_CHANGE';path.write_text(json.dumps(report))
    assert p.publication_status(root,batch['id'])['items'][0]['review']=='STALE'
    with pytest.raises(RiposteError,match='REVIEW_STALE'):p.publication_zip(root,batch['id'])

def test_preview_modes_are_verified_clean_png(root,batch):
    for kind in ['clean','candidate','difference']:
        raw=p.publication_pixels(root,batch['id'],batch['items'][0]['id'],kind,True)
        assert png_audit(raw)['date']=='2025-03-12'
    with pytest.raises(RiposteError):p.publication_pixels(root,batch['id'],batch['items'][0]['id'],'../request')

def test_export_file_matches_download_snapshot(root,batch):
    accept(root,batch)
    data=p.publication_zip(root,batch['id']);r=p.export_publication(root,batch['id'])
    assert (root/r['relative']).read_bytes()==data and r['sha256']==hashlib.sha256(data).hexdigest()

def test_workshop_optional_exact_handoff_and_idempotency(root,batch):
    t=p.open_in_workshop(root,batch['id'],batch['items'][0]['id'])
    assert t['artifact_sha256']['candidate']==batch['items'][0]['artifact_sha256']['candidate']
    assert p.open_in_workshop(root,batch['id'],batch['items'][0]['id'])['id']==t['id']
    assert p.publication_status(root,batch['id'])['counts']['ACCEPTED']==0

def test_status_contains_no_source_names_or_model_paths(root,batch):
    text=json.dumps(batch)
    assert 'image-0' not in text and 'prior/sub' not in text and 'LOCAL_SYNTHETIC_FIXTURE' not in text
    assert batch['ai_protection']=='UNVERIFIED'
