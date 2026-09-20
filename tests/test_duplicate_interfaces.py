"""Real CLI, terminal, authenticated API and report review over temporary files."""
import csv
import io
import json
import time

from fastapi.testclient import TestClient
from PIL import Image
import pytest
from typer.testing import CliRunner

from riposte.cli import app
from riposte.duplicate_review import DuplicateReview
from riposte.duplicates import ScanOptions, scan_duplicates
from riposte.errors import RiposteError
from riposte.server import create_app
from riposte.terminal.actions import make_request, request_argv
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render, view_rows
from test_duplicates import artwork


def copies(root, count=3):
    artwork().save(root / 'original.png')
    content = (root / 'original.png').read_bytes()
    for number in range(count-1):
        (root / f'copy-{number:03}.png').write_bytes(content)
    return DuplicateReview(scan_duplicates(root))


def await_job(client, identifier):
    for _ in range(500):
        job = next(job for job in client.get('/api/state').json()['jobs'] if job['id'] == identifier)
        if job['state'] not in {'queued', 'running'}: return job
        time.sleep(.01)
    pytest.fail('Duplicate scan job timed out')


def test_review_searches_every_member_and_pages_large_groups(root):
    review = copies(root, 123)
    page = review.page(search='copy-121')
    assert page['total'] == 1 and page['rows'][0]['member_count'] == 123
    assert 'search_text' not in page['rows'][0]
    detail = review.detail(page['rows'][0]['id'])
    assert len(detail['left']['members']) == 50
    more = review.group(detail['left']['id'], offset=100)
    assert len(more['members']) == 23 and more['offset'] == 100
    assert review.page(label='MAYBE DUPLICATE')['total'] == 0
    assert review.page(media='video')['total'] == 0
    assert review.page(min_confidence=100)['total'] == 1
    assert review.page(offset=999)['offset'] == 0


@pytest.mark.parametrize('kwargs', [{'label': 'bad'}, {'min_confidence': float('nan')}, {'min_confidence': True},
    {'limit': 201}, {'offset': -1}, {'order': 'wrong'}, {'search': 'x'*501}, {'media': 'bad'}])
def test_review_rejects_invalid_filters(root, kwargs):
    with pytest.raises(RiposteError, match='DUPLICATE_FILTER_INVALID'):
        DuplicateReview(scan_duplicates(root)).page(**kwargs)


def test_exports_complete_evidence_without_overwrite_and_csv_formula_execution(root, tmp_path):
    (root / '=formula.txt').write_bytes(b'content')
    (root / 'copy.txt').write_bytes(b'content')
    review = DuplicateReview(scan_duplicates(root))
    destination = tmp_path / 'report.json'
    review.export(destination)
    value = json.loads(destination.read_text(encoding='utf-8'))
    assert len(value['sources']) == 2 and len(value['findings']) == 1
    with pytest.raises(RiposteError, match='DUPLICATE_REPORT_EXISTS'): review.export(destination)
    rows = list(csv.DictReader(io.StringIO(review.export_bytes('csv').decode('utf-8-sig'))))
    assert rows[0]['left_path'] == "'=formula.txt"
    with pytest.raises(RiposteError, match='DUPLICATE_EXPORT_FORMAT_INVALID'): review.export(tmp_path / 'bad.exe')
    assert not (tmp_path / 'bad.exe').exists()
    assert sorted(path.name for path in root.iterdir()) == ['=formula.txt', 'copy.txt']


def test_preview_is_fresh_pixels_and_rejects_changed_or_unknown_source(root):
    review = copies(root)
    identifier = review.rows[0]['left_source']
    with Image.open(io.BytesIO(review.preview(identifier))) as image:
        assert image.size == (320, 240) and not image.info
    with pytest.raises(RiposteError, match='DUPLICATE_PREVIEW_UNAVAILABLE'): review.preview('../original.png')
    (root / review.sources[identifier]['relative']).write_bytes(b'replaced')
    with pytest.raises(RiposteError, match='DUPLICATE_SOURCE_CHANGED'): review.preview(identifier)


def test_cli_flags_export_and_terminal_command_roundtrip(root, tmp_path):
    copies(root)
    request = make_request('duplicates', root, {'visual': False, 'videos': False, 'include_float': False,
                            'max_files': 100, 'max_visual': 20, 'max_pairs': 50, 'duplicate_report': tmp_path / 'scan.json'})
    argv = request_argv(request)
    result = CliRunner().invoke(app, ['--json', *argv[1:]])
    assert result.exit_code == 0, result.output
    report = json.loads(result.stdout)
    assert report['counts']['DUPLICATE'] == 1
    assert report['options']['visual'] is False and report['options']['include_float'] is False
    assert (tmp_path / 'scan.json').is_file()
    assert not (root / '.riposte').exists()


def test_terminal_entry_filter_evidence_export_and_single_press_navigation(root, tmp_path):
    copies(root)
    controller = Controller(None, Presentation(no_animation=True))
    controller.key(Key('char', 'd'))
    assert controller.state.page.action == 'duplicates' and controller.state.editor.target == 'duplicate-path'
    controller.key(Key('paste', '"'+str(root)+'"')); controller.key(Key('enter'))
    assert controller.state.root == root
    controller.key(Key('char', 'r'));controller.state.operation.join();controller.pump()
    assert controller.state.page.name == 'duplicates'
    for width, height in [(72,24),(100,34),(132,46)]:
        screen = render(controller.state,width,height,0).plain()
        assert 'DUPLICATE' in screen and all(len(line)<=width for line in screen.splitlines())
    controller.key(Key('char','3'));assert not view_rows(controller.state)
    controller.key(Key('char','2'));assert len(view_rows(controller.state))==1
    controller.key(Key('char','/'));controller.key(Key('paste','copy-001'));controller.key(Key('enter'))
    assert len(view_rows(controller.state))==1
    controller.key(Key('enter'));assert controller.state.page.result['mode']=='DUPLICATE_FINDING'
    controller.key(Key('escape'));controller.key(Key('char','e'))
    controller.key(Key('paste',str(tmp_path/'terminal.json')));controller.key(Key('enter'))
    assert (tmp_path/'terminal.json').exists() and controller.state.editor is None
    controller.key(Key('char','g'));assert controller.state.editor.target=='duplicate-path'
    assert not (root/'.riposte').exists()


def test_api_authenticated_paginated_review_preview_export_and_stale_source(root):
    copies(root)
    with TestClient(create_app(root, 'dup-test')) as client:
        assert client.post('/api/duplicates',json={}).status_code == 401
        client.headers['X-Riposte-Token']='dup-test'
        assert client.post('/api/duplicates',json={'max_files':0}).status_code == 422
        response=client.post('/api/duplicates',json={})
        assert response.status_code==200,response.text
        job=await_job(client,response.json()['job_id'])
        assert job['state']=='done',job
        summary=job['result'];prefix='/api/duplicates/'+summary['scan_id']
        assert 'sources' not in summary and 'findings' not in summary
        page=client.get(prefix+'/findings?search=copy-001').json()
        row=page['rows'][0];detail=client.get(prefix+'/findings/'+row['id']).json()
        assert detail['left']['count']==3
        assert client.get(prefix+'/groups/'+detail['left']['id']).json()['count']==3
        preview=client.get(prefix+'/preview/'+row['left_source'])
        assert preview.status_code==200 and preview.headers['content-type']=='image/png'
        exported=client.get(prefix+'/export?format=json')
        assert len(exported.json()['sources'])==3 and 'attachment' in exported.headers['content-disposition']
        assert client.get(prefix+'/findings?label=BAD').status_code==400
        (root/row['left_path']).write_bytes(b'changed')
        assert client.get(prefix+'/preview/'+row['left_source']).json()['code']=='DUPLICATE_SOURCE_CHANGED'
        client.headers.pop('X-Riposte-Token')
        assert client.get(prefix+'/export').status_code==401
    assert not (root/'.riposte').exists()


def test_api_partial_scan_retains_results_and_returns_incomplete(root):
    copies(root)
    (root/'bad.png').write_bytes(b'not an image')
    with TestClient(create_app(root,'dup')) as client:
        client.headers['X-Riposte-Token']='dup'
        job=await_job(client,client.post('/api/duplicates',json={}).json()['job_id'])
        assert job['state']=='incomplete'
        assert job['result']['counts']['DUPLICATE']==1 and job['result']['issues']['counts']
    controller=Controller(root,Presentation(no_animation=True));controller.begin_action('duplicates');controller.run_form()
    controller.state.operation.join();controller.pump()
    assert controller.state.page.name=='duplicates' and controller.state.page.result['checkpoint']=='INCOMPLETE'
    assert len(view_rows(controller.state))>=1


def test_standalone_scan_ignores_foreign_private_state_and_hardlinks(root):
    import os
    for name in ('.riposte','.shroud'):
        (root/name).mkdir();(root/name/'WORKSPACE').write_bytes(b'foreign state')
    (root/'first.txt').write_bytes(b'equal')
    os.link(root/'first.txt',root/'linked.txt')
    result=CliRunner().invoke(app,['--json','duplicates',str(root)])
    assert result.exit_code==0,result.output
    report=json.loads(result.stdout)
    assert report['counts']['DUPLICATE']==1 and report['counts']['private_directories_excluded']==2
    assert all(source['hardlinks']==2 for source in report['sources'])
    controller=Controller(None,Presentation(no_animation=True));controller.begin_action('duplicates')
    controller.key(Key('paste',str(root)));controller.key(Key('enter'));controller.run_form()
    controller.state.operation.join();controller.pump()
    assert controller.state.page.name=='duplicates'


def test_api_retains_two_most_recent_scans_including_repeated_identity(root):
    copies(root)
    with TestClient(create_app(root,'dup')) as client:
        client.headers['X-Riposte-Token']='dup'
        def scan(options):
            return await_job(client,client.post('/api/duplicates',json=options).json()['job_id'])['result']['scan_id']
        first=scan({});second=scan({'visual':False})
        assert scan({})==first
        third=scan({'videos':False})
        assert client.get('/api/duplicates/'+first).status_code==200
        assert client.get('/api/duplicates/'+third).status_code==200
        assert client.get('/api/duplicates/'+second).json()['code']=='DUPLICATE_SCAN_EXPIRED'


def test_duplicate_browser_native():
    import os
    from pathlib import Path
    import shutil
    import subprocess
    node=shutil.which('node')
    browser=next((p for p in [os.environ.get('RIPOSTE_TEST_BROWSER',''),shutil.which('chromium'),
        'C:/Program Files/Google/Chrome/Application/chrome.exe',
        'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'] if p and Path(p).is_file()),None)
    if not node or not browser: pytest.skip('Local Node and Chromium required')
    run=subprocess.run([node,str(Path(__file__).with_name('duplicate_browser.cjs')),browser],
                       capture_output=True,text=True,encoding='utf-8',timeout=40)
    assert run.returncode==0,run.stdout+run.stderr
    assert run.stdout.strip()=='PASS duplicate_browser'
