"""Regression coverage for the audit; synthetic artwork, no model dependency."""
import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from riposte import __version__, publication as p
from riposte.errors import RiposteError
from riposte.organizer import organize
from riposte.policy import Policy, folder_for
from riposte.sanitize import decode_clean, encode_clean, png_audit
from riposte.server import create_app
from riposte.store import atomic_clean_write, atomic_json_write, catalog, record_image


def wait_job(app, identifier):
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        job = next(j for j in app.state.jobs.snapshot() if j['id'] == identifier)
        if job['state'] not in ('queued', 'running'):
            return job
        time.sleep(.01)
    pytest.fail('job did not finish')


@pytest.mark.parametrize('dated', [False, True])
def test_organization_retries_are_idempotent(root, dated):
    source = root / 'input.png'
    Image.new('RGB', (64, 48), (30, 90, 150)).save(source)
    if dated:
        time.sleep(.02)
        os.utime(source, (1725984000, 1725984000))
    for _ in range(3):
        assert organize(root, Policy(date_mode='modified'))['checkpoint'] == 'COMPLETE'
        assert len(catalog(root)) == 1
        assert not source.exists()


@pytest.mark.parametrize('change', ['replace', 'write_restore_mtime'])
def test_changed_source_is_retained_at_commit(root, monkeypatch, change):
    source = root / 'input.png'
    Image.new('RGB', (64, 48), (30, 90, 150)).save(source)
    original = record_image

    def commit(*args, **kwargs):
        row = original(*args, **kwargs)
        before = source.stat()
        time.sleep(.02)
        if change == 'replace':
            replacement = root / 'replacement.png'
            replacement.write_bytes(source.read_bytes())
            os.replace(replacement, source)
        else:
            data = bytearray(source.read_bytes())
            data[-1] ^= 1
            source.write_bytes(data)
        os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
        return row

    monkeypatch.setattr('riposte.organizer.record_image', commit)
    result = organize(root, Policy(date_mode='modified'))
    assert result['checkpoint'] == 'INCOMPLETE'
    assert result['blockers']['SOURCE_CHANGED_OUTPUT_RETAINED'] == 1
    assert source.exists()


def test_path_change_during_decode_is_rejected(root, monkeypatch):
    import riposte.sanitize as sanitize
    source = root / 'input.png'
    Image.new('RGB', (64, 48), (30, 90, 150)).save(source)
    original = sanitize.fresh_pixels

    def changed(image):
        pixels = original(image)
        stat = source.stat()
        os.utime(source, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
        return pixels

    monkeypatch.setattr(sanitize, 'fresh_pixels', changed)
    with pytest.raises(RiposteError, match='SOURCE_CHANGED'):
        decode_clean(source)


def test_homepage_uses_utf8_and_keeps_headers(root, monkeypatch):
    original = Path.read_text
    seen = []

    def read(path, *args, **kwargs):
        if path.name == 'index.html':
            seen.append(kwargs.get('encoding'))
            kwargs.setdefault('encoding', 'cp1252')
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, 'read_text', read)
    with TestClient(create_app(root, 'fixture')) as client:
        response = client.get('/')
        assert response.status_code == 200
        assert seen == ['utf-8']
        assert response.headers['cache-control'] == 'no-store'
        assert "frame-ancestors 'none'" in response.headers['content-security-policy']
        assert client.get('/api/state', headers={'x-riposte-token': 'fixture'}).json()['version'] == __version__


@pytest.mark.parametrize('result,expected', [
    ({'checkpoint': 'INCOMPLETE'}, 'incomplete'),
    ({'ready': False}, 'incomplete'),
    ({'mode': 'PUBLICATION_BATCH', 'counts': {'BLOCKED': 1}}, 'incomplete'),
    ({'mode': 'PUBLICATION_BATCH', 'counts': {'PENDING': 1}}, 'incomplete'),
    ({'mode': 'PUBLICATION_BATCH', 'counts': {'BLOCKED': 0, 'PENDING': 0}}, 'done'),
    ({'checkpoint': 'COMPLETE'}, 'done'),
])
def test_job_results_remain_visible(root, result, expected):
    app = create_app(root, 'fixture')
    with TestClient(app):
        started = app.state.jobs.start(lambda progress: result)
        job = wait_job(app, started['job_id'])
        assert job['state'] == expected
        assert job['result'] == result
        assert job['phase'] == ('Complete' if expected == 'done' else 'Needs attention')


@pytest.mark.parametrize('length', [32768, 32769, 40015])
@pytest.mark.parametrize('transfer', ['fixed', 'chunked', 'false_length'])
def test_request_limit_counts_body_bytes(root, length, transfer):
    body = b' ' * (length - 2) + b'{}'
    headers = {'x-riposte-token': 'fixture', 'content-type': 'application/json'}
    if transfer == 'false_length':
        headers['content-length'] = '2'
    with TestClient(create_app(root, 'fixture')) as client:
        response = client.post('/api/organize', headers=headers,
                               content=body if transfer == 'fixed' else iter([body[:100], body[100:]]))
        assert response.status_code == (200 if length <= 32768 else 413)


@pytest.mark.parametrize('headers,status,reads', [
    ([], 401, 0),
    ([(b'x-riposte-token', b'fixture'), (b'origin', b'https://invalid.example')], 403, 0),
    ([(b'x-riposte-token', b'fixture')], 413, 3),
])
def test_stream_stops_at_bound_and_authentication_precedes_consumption(root, headers, status, reads):
    app = create_app(root, 'fixture')
    received, sent = [], []

    async def receive():
        received.append(1)
        assert len(received) <= 3, 'oversized stream must not be drained'
        return {'type': 'http.request', 'body': b' ' * 16000, 'more_body': True}

    async def send(message):
        sent.append(message)

    scope = {'type': 'http', 'asgi': {'version': '3.0'}, 'http_version': '1.1',
             'method': 'POST', 'scheme': 'http', 'path': '/api/organize', 'raw_path': b'/api/organize',
             'query_string': b'', 'root_path': '', 'server': ('testserver', 80), 'client': ('127.0.0.1', 1),
             'headers': [(b'host', b'testserver'), (b'content-type', b'application/json'), *headers]}
    asyncio.run(app(scope, receive, send))
    assert next(m for m in sent if m['type'] == 'http.response.start')['status'] == status
    assert len(received) == reads


@pytest.fixture
def committed(root):
    """Real date-only PNGs and storage records; no substituted verification."""
    day = '2026-09-10'
    clean = Image.new('RGB', (64, 64), (110, 130, 150))
    candidate = clean.copy()
    candidate.putpixel((12, 12), (111, 130, 150))
    folder = folder_for(day, 64, 64)
    relative = (folder / 'SML01.png').as_posix()
    clean_data, candidate_data = encode_clean(clean, day), encode_clean(candidate, day)
    atomic_clean_write(root, relative, clean_data)
    row = record_image(root, relative, png_audit(clean_data), len(clean_data), 'modified')
    batch, item = uuid.uuid4().hex, uuid.uuid4().hex
    task = {'id': item, 'image_id': row['id'], 'date': day, 'max_edge': 64,
            'index': 0, 'source_clean_sha256': row['sha256']}
    prefix = f'.riposte/publishing/{batch}'
    atomic_json_write(root, prefix + '/request.json', {'id': batch, 'schema': 1, 'sequence': 1,
        'recipe': p.PublishRecipe((64,)).public(), 'tasks': [task], 'duplicate_renders_avoided': 0})
    atomic_json_write(root, prefix + '/outcome.json', {'status': 'FINISHED'})
    from riposte.metrics import transport_report
    from riposte.quality import quality_report
    report = {**task, 'batch_id': batch, 'relative': relative, 'width': 64, 'height': 64,
              'artifact_sha256': {'clean': hashlib.sha256(clean_data).hexdigest(),
                                 'candidate': hashlib.sha256(candidate_data).hexdigest()},
              'quality': quality_report(clean, candidate), 'transport': transport_report(clean, candidate),
              'guard': {'fixture': True}, 'ai_protection': 'UNVERIFIED'}
    for kind, data in [('clean', clean_data), ('candidate', candidate_data)]:
        atomic_clean_write(root, prefix + f'/items/{item}/{kind}.png', data)
    atomic_json_write(root, prefix + f'/items/{item}/report.json', report)
    return batch, item, root / prefix / 'items' / item


@pytest.mark.parametrize('kind', ['candidate.png', 'clean.png', 'report.json'])
@pytest.mark.parametrize('damage', ['change', 'missing'])
def test_changed_approval_can_be_revoked_without_serving(root, committed, kind, damage):
    batch, item, folder = committed
    assert p.review_publication(root, batch, [item], 'ACCEPTED', True, True)['counts']['ACCEPTED'] == 1
    assert p.publication_zip(root, batch)
    target = folder / kind
    if damage == 'missing':
        target.unlink()
    else:
        target.write_bytes(b'corrupted' if kind == 'report.json' else
                           encode_clean(Image.new('RGB', (64, 64), (112, 130, 150)), '2026-09-10'))
    status = p.publication_status(root, batch)
    assert status['counts']['ACCEPTED'] == 0
    assert status['items'][0]['status'] == 'BLOCKED'
    assert status['items'][0]['review'] == 'STALE'
    for operation in [lambda: p.publication_pixels(root, batch, item),
                      lambda: p.publication_zip(root, batch),
                      lambda: p.review_publication(root, batch, [item], 'ACCEPTED', True, True)]:
        with pytest.raises(RiposteError):
            operation()
    rejected = p.review_publication(root, batch, [item], 'REJECTED')
    assert rejected['counts']['ACCEPTED'] == 0
    assert rejected['items'][0]['review'] == 'REJECTED'
    with pytest.raises(RiposteError, match='NO_APPROVED'):
        p.publication_zip(root, batch)


@pytest.mark.parametrize('audit', [{'checkpoint': 'INCOMPLETE'}, {'checkpoint': 'COMPLETE'}, None])
def test_browser_completion_uses_actual_audit(audit):
    if not shutil.which('node'):
        pytest.skip('Node is required for isolated browser callback execution')
    source = Path(__file__).parents[1] / 'src/riposte/static/publish.js'
    script = r'''
const fs=require('fs'),vm=require('vm');
const source=fs.readFileSync(process.argv[1],'utf8');
const match=source.match(/async function completed\(result\)\{[\s\S]*?\n  \}/);
if(!match)throw Error('completed function not found');
const audit=JSON.parse(process.argv[2]);let calls=0,errors=0;
const context={current:'',batch:null,state:{audit:{checkpoint:'COMPLETE'}},
renderAuditBadge:()=>{},renderBatch:()=>{},setView:()=>{},error:()=>errors++,
api:async endpoint=>{if(endpoint!=='audit')throw Error(endpoint);calls++;if(audit===null)throw Error('offline');return audit;}};
vm.createContext(context);vm.runInContext(match[0],context);
(async()=>{await context.completed({id:'fixture',mode:'PUBLICATION_BATCH',counts:{BLOCKED:1}});
process.stdout.write(JSON.stringify({audit:context.state.audit,calls,errors}));})().catch(e=>{console.error(e);process.exitCode=1;});
'''
    result = subprocess.run(['node', '-e', script, str(source), json.dumps(audit)],
                            capture_output=True, text=True, timeout=10, check=True)
    observed = json.loads(result.stdout)
    assert observed == {'audit': audit, 'calls': 1, 'errors': int(audit is None)}
