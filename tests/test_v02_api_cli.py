from riposte.organizer import plan as _sort_preview
import json
import threading
import time
import pytest
from fastapi.testclient import TestClient
from riposte.errors import RiposteError
from riposte.server import create_app,Jobs
from riposte.cli import main
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog,LEGACY_SIGNATURE
from riposte.lab import compare_external

@pytest.fixture
def trial(root,tmp_path,make_image):
    make_image(root/'a.png');organize(root,Policy(date_mode='modified'), plan_id=_sort_preview(root, Policy(date_mode='modified'))["plan_id"])
    return compare_external(root,catalog(root)[0]['id'],make_image(tmp_path/'candidate.png',color=(31,91,151)))

@pytest.fixture
def client(root):
    with TestClient(create_app(root,'test-session')) as client:
        client.headers['X-Riposte-Token']='test-session'
        yield client

@pytest.mark.parametrize('route',['runtime','preflight','generations/'+'a'*32,'evaluations/'+'a'*32])
def test_new_api_requires_token(root,route):
    with TestClient(create_app(root,'test-session')) as c:
        r=c.post('/api/'+route,json={}) if route=='preflight' else c.get('/api/'+route)
        assert r.status_code==401

def test_runtime_preflight_no_workspace_creation(root,client):
    r=client.get('/api/runtime');assert r.status_code==200 and r.json()['model_loading']=='EXPLICIT_LOCAL_ONLY'
    r=client.post('/api/preflight',json={});assert r.status_code==200 and 'runtime' in r.json()
    assert not list(root.iterdir())

def test_api_safe_model_error_and_unknown_fields(client):
    path='/never-a-real-model/DO_NOT_RETURN_PRIVATE_PATH'
    r=client.post('/api/preflight',json={'vae_directory':path});assert r.status_code==400
    assert 'DO_NOT_RETURN' not in r.text
    r=client.post('/api/qualify',json={'trial_id':'a'*32,'vae_directory':'model','unexpected':'PRIVATE'})
    assert r.status_code==422 and 'PRIVATE' not in r.text

def test_real_trial_view_routes_validate_clean_pair(client,trial):
    from riposte.sanitize import png_audit
    for view in ['identity','jpeg70','jpeg60','offset-crop85','resize50-jpeg80']:
        r=client.get(f"/api/trial/{trial['id']}/candidate?view={view}")
        assert r.status_code==200 and png_audit(r.content)['date']==trial['date']
    assert client.get(f"/api/trial/{trial['id']}/candidate?view=unknown").status_code==400
    assert client.get(f"/api/evaluations/{trial['id']}").json()=={'evaluations':[]}
    assert client.get(f"/api/generations/{trial['id']}").json()=={'runs':[]}

def test_jobs_cancel_at_checkpoint_and_no_raw_exception():
    jobs=Jobs();started=threading.Event();proceed=threading.Event()
    def work(progress):
        started.set();proceed.wait(2);progress({'phase':'checkpoint'});return {'result':'not-reached'}
    identifier=jobs.start(work)['job_id'];assert started.wait(2)
    assert jobs.cancel(identifier)['status']=='CANCEL_REQUESTED';proceed.set()
    jobs.pool.shutdown(wait=True)
    assert jobs.snapshot()[0]['state']=='cancelled' and 'result' not in jobs.snapshot()[0]

def test_destructive_jobs_cannot_cancel_and_busy_no_second_job():
    jobs=Jobs();started=threading.Event();proceed=threading.Event()
    def work(progress):started.set();proceed.wait(2);return {'result':'done'}
    key=jobs.start(work,cancellable=False)['job_id'];assert started.wait(2)
    with pytest.raises(RiposteError,match='UNSUPPORTED'):jobs.cancel(key)
    with pytest.raises(RiposteError,match='ALREADY_RUNNING'):jobs.start(work)
    proceed.set();jobs.pool.shutdown(wait=True);assert jobs.snapshot()[0]['state']=='done'

def test_job_error_codes_do_not_expose_paths():
    jobs=Jobs()
    def work(progress):raise RuntimeError('/PRIVATE_DATA')
    jobs.start(work);jobs.pool.shutdown(wait=True)
    assert jobs.snapshot()[0]['code']=='OPERATION_FAILED' and 'PRIVATE_DATA' not in json.dumps(jobs.snapshot())

def test_namespace_upgrade_api(root,trial,client):
    (root/'.riposte').rename(root/'.shroud');(root/'.shroud/WORKSPACE').write_text(LEGACY_SIGNATURE)
    assert client.get('/api/state').json()['legacy_workspace']
    assert client.post('/api/upgrade-workspace',json={}).json()['artwork_rewritten']==0
    assert not client.get('/api/state').json()['legacy_workspace']

def test_doctor_and_upgrade_cli_are_read_only(root,capsys):
    assert main(['doctor'])==0
    assert json.loads(capsys.readouterr().out)['runtime']['cpu']
    assert main(['upgrade',str(root)])==0
    assert json.loads(capsys.readouterr().out)['status']=='ALREADY_CURRENT'
    assert not list(root.iterdir())

def test_cli_new_guard_and_qualification_arguments(root,monkeypatch,capsys):
    import riposte.lab as lab
    import riposte.qualification as qualification
    received=[]
    def capture(*a,**k):received.append(k);return {'ok':True}
    monkeypatch.setattr(lab,'create_candidate',capture)
    assert main(['guard',str(root),'a'*32,'--vae','model','--engine','coupled','--pipeline','pipeline','--device','cpu','--no-preserve-white'])==0
    assert received[0]['engine']=='coupled' and not received[0]['preserve_white']
    monkeypatch.setattr(qualification,'qualify_trial',capture)
    assert main(['qualify',str(root),'a'*32,'--vae','model','--device','cpu'])==0
    assert received[-1]['device']=='cpu'

def test_cli_challenge_controls_options(root,monkeypatch,capsys):
    import riposte.generation as generation
    received=[]
    def capture(*a,**k):received.append(k);return {'ok':True}
    monkeypatch.setattr(generation,'controlled_generation',capture)
    assert main(['challenge',str(root),'a'*32,'--model','model','--task','video','--seed','21','--view','jpeg70','--steps','2'])==0
    assert received[0]['seeds']==(21,) and received[0]['views']==('jpeg70',)
