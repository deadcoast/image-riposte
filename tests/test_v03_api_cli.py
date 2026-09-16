import io,json,time
from pathlib import Path
from zipfile import ZipFile
import pytest
pytest.importorskip("torch")
from fastapi.testclient import TestClient
from riposte.server import create_app
from riposte.cli import main
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog

@pytest.fixture
def fixture(root,make_image,monkeypatch):
    make_image(root/'source.png',size=(96,64));organize(root,Policy(date_mode='modified'))
    import riposte.models as models
    class Oracle:
        device='cpu';identity={'kind':'SYNTHETIC_TEST_ORACLE','weights_sha256':'a'*64}
        def __call__(self,x):return x.square()+.15*x
    monkeypatch.setattr(models,'LocalEncoder',lambda *args:Oracle())
    return catalog(root)[0]['id']

@pytest.fixture
def client(root):
    with TestClient(create_app(root,'v03-test')) as c:
        c.headers['X-Riposte-Token']='v03-test';yield c

def wait(c,key):
    for _ in range(400):
        j=next(x for x in c.get('/api/state').json()['jobs'] if x['id']==key)
        if j['state'] not in ['running','queued']:return j
        time.sleep(.01)
    pytest.fail('job did not finish')

def run_batch(client,fixture):
    r=client.post('/api/publish',json={'image_ids':[fixture],'vae_directories':['LOCAL_TEST'],'edges':[64],'steps':2,'restarts':1})
    assert r.status_code==200
    j=wait(client,r.json()['job_id']);assert j['state']=='done',j
    return j['result']

@pytest.mark.parametrize('route,method',[('publish','post'),('publication/'+'a'*32,'get'),('publication/'+'a'*32+'/pack','get'),('execute-model','post'),('publication/'+'a'*32+'/resume','post'),('publication/'+'a'*32+'/review','post')])
def test_primary_api_session_required(root,route,method):
    with TestClient(create_app(root,'secret')) as c:
        assert getattr(c,method)('/api/'+route).status_code==401

def test_plan_has_no_model_requirement_and_no_publication_files(root,fixture,client):
    r=client.post('/api/publish',json={'image_ids':[fixture],'edges':[512,1024],'plan_only':True})
    assert r.status_code==200 and r.json()['outputs']==1 and r.json()['duplicate_renders_avoided']==1
    assert not (root/'.riposte/publishing').exists()

def test_api_complete_primary_product_path(root,fixture,client):
    b=run_batch(client,fixture);bid=b['id'];item=b['items'][0]['id']
    assert client.get('/api/state').json()['publications'][0]['id']==bid
    assert client.get(f'/api/publication/{bid}/pack').status_code==400
    assert client.post(f'/api/publication/{bid}/review',json={'item_ids':[item]}).status_code==400
    r=client.post(f'/api/publication/{bid}/review',json={'item_ids':[item],'decision':'ACCEPTED','visual_accepted':True,'acknowledge_unverified':True})
    assert r.json()['counts']['ACCEPTED']==1
    data=client.get(f'/api/publication/{bid}/pack');assert data.status_code==200
    assert data.headers['content-type']=='application/zip' and 'RIPOSTE.zip' in data.headers['content-disposition']
    with ZipFile(io.BytesIO(data.content)) as z:
        assert len(z.namelist())==1
        raw=client.get(f'/api/publication/{bid}/image/{item}/candidate').content
        assert z.read(z.namelist()[0])==raw
    assert not (root/'.riposte/lab').exists()
    assert client.post(f'/api/publication/{bid}/workshop/{item}',json={}).json()['publication_batch_id']==bid

@pytest.mark.parametrize('view',['identity','jpeg95','jpeg85','jpeg70','resize75','crop90','blur06','resize75-jpeg85'])
def test_review_uses_actual_matched_transport(client,fixture,view):
    from riposte.sanitize import png_audit
    b=run_batch(client,fixture);item=b['items'][0]
    for kind in ['clean','candidate','difference']:
        response=client.get(f"/api/publication/{b['id']}/image/{item['id']}/{kind}?view={view}")
        assert response.status_code==200 and png_audit(response.content)['date']==item['date']

def test_invalid_bodies_and_error_codes_do_not_echo_paths(client,fixture):
    r=client.post('/api/publish',json={'image_ids':[fixture],'vae_directories':['MODEL_PRIVATE'],'evil':'PRIVATE_PATH'})
    assert r.status_code==422 and 'PRIVATE' not in r.text
    r=client.post('/api/publish',json={'image_ids':[fixture],'vae_directories':[''],'steps':2})
    assert r.status_code==400 and 'LOCAL_MODEL' in r.text

def test_actual_model_execution_api(client,fixture):
    r=client.post('/api/execute-model',json={'vae_directories':['SYNTHETIC_FIXTURE']})
    j=wait(client,r.json()['job_id'])
    assert j['state']=='done' and j['result']['models'][0]['nonzero_gradient']
    assert j['result']['evidence_level']=='EXECUTION_ONLY'

def test_cli_publication_plan_create_review_package(root,fixture,capsys):
    assert main(['publish',str(root),'--all','--edge','64','--plan'])==0
    assert json.loads(capsys.readouterr().out)['mode']=='PUBLICATION_PLAN'
    assert main(['publish',str(root),'--image',fixture,'--vae','SYNTHETIC_TEST','--edge','64','--steps','2','--restarts','1'])==0
    b=json.loads(capsys.readouterr().out)
    assert main(['review',str(root),b['id'],'--item',b['items'][0]['id'],'--visual-accepted','--acknowledge-unverified'])==0
    assert json.loads(capsys.readouterr().out)['counts']['ACCEPTED']==1
    assert main(['package',str(root),b['id']])==0
    receipt=json.loads(capsys.readouterr().out)
    assert (root/receipt['relative']).is_file()
    assert main(['publications',str(root),b['id']])==0
    assert json.loads(capsys.readouterr().out)['ai_protection']=='UNVERIFIED'

def test_doctor_execute_is_distinct_from_file_presence(fixture,capsys):
    assert main(['doctor','--vae','SYNTHETIC_TEST','--execute'])==0
    assert json.loads(capsys.readouterr().out)['mode']=='LOCAL_MODEL_EXECUTION'
