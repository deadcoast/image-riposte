from riposte.organizer import plan as _sort_preview
import time
import pytest
from fastapi.testclient import TestClient
from riposte.server import create_app
from riposte.policy import Policy
from riposte.organizer import organize
from riposte.store import catalog

@pytest.fixture
def client(root):
    app=create_app(root,token='test-token')
    with TestClient(app) as client:
        yield client
    app.state.jobs.pool.shutdown(wait=True)
HEADERS={'X-Riposte-Token':'test-token'}
def test_ui_is_self_contained(client):
    r=client.get('/');assert r.status_code==200;assert 'RIPOSTE' in r.text;assert r.headers['cache-control']=='no-store';assert "frame-ancestors 'none'" in r.headers['content-security-policy']
def test_session_required(client):assert client.get('/api/state').status_code==401
def test_state_has_no_absolute_paths(client):
    r=client.get('/api/state',headers=HEADERS);assert r.status_code==200;assert r.json()['images']==[];assert '/tmp/' not in r.text
def test_host_rejected(client):assert client.get('/api/state',headers={**HEADERS,'Host':'evil.example'}).status_code==403
def test_origin_rejected(client):assert client.post('/api/organize',json={},headers={**HEADERS,'Origin':'https://evil.example'}).status_code==403
def test_bad_token_rejected(client):assert client.get('/api/state',headers={'X-Riposte-Token':'bad'}).status_code==401
def test_destructive_ack_required(client):
    r=client.post('/api/organize',json={'apply':True},headers=HEADERS);assert r.status_code==400;assert 'ACKNOWLEDGE' in r.text
def test_validation_never_echoes_input(client):
    r=client.post('/api/guard',json={'vae_directory':'PRIVATE_SOURCE_NAME','steps':'PRIVATE_FIXTURE_PAYLOAD'},headers=HEADERS)
    assert r.status_code==422;assert 'PRIVATE' not in r.text
def test_image_bytes_are_clean(client,root,make_image):
    make_image(root/'source.png');organize(root,Policy(date_mode='modified'), plan_id=_sort_preview(root, Policy(date_mode='modified'))["plan_id"]);row=catalog(root)[0]
    r=client.get('/api/image/'+row['id']+'?thumb=true',headers=HEADERS);assert r.status_code==200;assert b'PRIVATE_FIXTURE_PAYLOAD' not in r.content
    from riposte.sanitize import png_audit
    png_audit(r.content)
def test_real_api_plan_job(client,root,make_image):
    make_image(root/'source.png');r=client.post('/api/organize',json={},headers=HEADERS);assert r.status_code==200
    for _ in range(100):
        state=client.get('/api/state',headers=HEADERS).json()
        if state['jobs'][0]['state']=='done':break
        time.sleep(.01)
    assert state['jobs'][0]['result']['mode']=='READ_ONLY';assert not (root/'.riposte').exists()
def test_nonexistent_id_is_safe(client):
    r=client.get('/api/image/invalid',headers=HEADERS);assert r.status_code==400;assert r.json()['code']=='IMAGE_NOT_FOUND'
