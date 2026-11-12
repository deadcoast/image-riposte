"""Private opt-in lookup: real sorting/provenance, paging, privacy and surfaces."""
import contextlib
import hashlib
import json
import sqlite3
import time

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from riposte.cli import app
from riposte.errors import RiposteError
from riposte.library_search import search_library
from riposte.organizer import organize, plan, undo_sort
from riposte.policy import Policy
from riposte.server import create_app
from riposte.sort_titles import title_records, save_title
from riposte.store import catalog, connect
from riposte.terminal.service import Request, execute, select_rows

POLICY = Policy(date_mode='modified')


def sorted_images(root, make_image, count=3):
    from riposte.category_rules import build_rules, load_rules, save_rules
    save_rules(root, build_rules(['Portrait=portrait']), expected_revision=load_rules(root).revision)
    for n in range(count):
        make_image(root / f'Private-Caf\u00e9-Moonlight-{n:03}.png')
    preview = plan(root, POLICY, categories=True, assignments=['Private-Caf\u00e9-Moonlight-000.png=portrait'])
    organize(root, POLICY, categories=True, assignments=['Private-Caf\u00e9-Moonlight-000.png=portrait'], plan_id=preview['plan_id'])
    return catalog(root)


def snapshot(root):
    return {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in root.rglob('*') if p.is_file()}


def test_real_sort_private_optin_and_unchanged_default_outputs(root, make_image):
    rows = sorted_images(root, make_image)
    before = snapshot(root)
    assert select_rows(root, search='moonlight') == []
    report = search_library(root, search='CAFE\u0301-MOONLIGHT', month='Mar', year='2025', size='SML')
    assert report['total'] == 3
    assert {r['id'] for r in report['rows']} == {r['id'] for r in rows}
    assert all(r['title_state'] == 'KNOWN' and r['provenance'] == 'MATCHED' for r in report['rows'])
    assert search_library(root, category='PORTRAIT')['total'] == 1
    assert search_library(root, category='port')['total'] == 0
    assert search_library(root, search='moonlight', category='portrait')['total'] == 1
    assert search_library(root, search='%')['total'] == 0
    assert search_library(root, search="' OR 1=1 --")['total'] == 0
    assert execute(Request('library-search', root, {'search': 'moonlight'})) == search_library(root, search='moonlight')
    assert not any('original_filename' in r or 'category' in r for r in catalog(root))
    for row in rows:
        assert b'Private-Caf' not in (root/row['relative']).read_bytes()
    assert snapshot(root) == before


@pytest.mark.parametrize('change,expected', [('missing','MISSING'),('hash','MISMATCHED'),('media','MISMATCHED'),('id','MISMATCHED'),('bad','INVALID'),('oversize','INVALID'),('null','MATCHED')])
def test_unknown_never_invents_titles_or_matches_untrusted_words(root, make_image, change, expected):
    sorted_images(root, make_image, 1)
    title = title_records(root)[0]
    if change == 'hash': title['sha256'] = 'f'*64
    if change == 'media': title['media'] = 'vid'
    if change == 'id': title['id'] = 'a'*32
    if change == 'null': title['original_filename'] = None
    with contextlib.closing(connect(root)) as db:
        if change == 'missing': db.execute('DELETE FROM sort_titles')
        else:
            data = '{broken' if change == 'bad' else 'x'*20000 if change == 'oversize' else json.dumps(title)
            db.execute('UPDATE sort_titles SET data=?', (data,))
        db.commit()
    before = snapshot(root)
    row = search_library(root, title_state='unknown')['rows'][0]
    assert row['provenance'] == expected and row['original_filename'] is None
    assert row['category'] == ('portrait' if change == 'null' else None)
    assert search_library(root, search='moonlight')['total'] == 0
    assert search_library(root, title_state='known')['total'] == 0
    assert snapshot(root) == before


def test_stable_bounded_paging_and_stale_restart(root, make_image):
    sorted_images(root, make_image, 7)
    first = search_library(root, limit=2)
    seen = first['rows'][:]
    offset = first['next_offset']
    while offset is not None:
        page = search_library(root, limit=2, offset=offset, expected_revision=first['revision'])
        assert len(page['rows']) <= 2
        seen.extend(page['rows']); offset = page['next_offset']
    assert len({r['id'] for r in seen}) == len(seen) == 7
    assert search_library(root, offset=999)['rows'] == []
    title = title_records(root)[0]; title['original_filename'] = 'later.png'; save_title(root, title)
    with pytest.raises(RiposteError, match='LIBRARY_SEARCH_STALE'):
        search_library(root, limit=2, offset=2, expected_revision=first['revision'])
    assert search_library(root, limit=2)['revision'] != first['revision']


@pytest.mark.parametrize('options', [{'limit':0},{'limit':501},{'limit':True},{'offset':-1},{'offset':True},{'search':'x'*201},{'category':'x'*97},{'title_state':'guessed'},{'year':'0000'},{'month':'13'},{'size':'small'},{'expected_revision':'bad'}])
def test_invalid_request_does_not_create_state(root, options):
    with pytest.raises(RiposteError): search_library(root, **options)
    assert not list(root.iterdir())


def test_empty_legacy_catalog_cancel_and_corruption(root, make_image):
    assert search_library(root)['total'] == 0 and not list(root.iterdir())
    sorted_images(root, make_image, 1)
    with contextlib.closing(connect(root)) as db:
        db.execute('DROP TABLE sort_titles'); db.commit()
    assert search_library(root)['rows'][0]['provenance'] == 'MISSING'
    before = snapshot(root)
    def stop(event): raise InterruptedError()
    with pytest.raises(InterruptedError): search_library(root, progress=stop)
    assert snapshot(root) == before
    (root/'.riposte/catalog.sqlite3').write_bytes(b'corrupt')
    with pytest.raises(RiposteError, match='LIBRARY_SEARCH_UNAVAILABLE'): search_library(root)


def test_application_root_and_linked_state_rejected(root):
    from riposte.store import application_directory
    with pytest.raises(RiposteError, match='IMAGE_FOLDER_OVERLAPS_APPLICATION'):
        search_library(application_directory())
    target = root.parent/'elsewhere'; target.mkdir()
    try: (root/'.riposte').symlink_to(target, target_is_directory=True)
    except OSError: pytest.skip('Symlink privilege unavailable')
    with pytest.raises(RiposteError): search_library(root)
    assert not list(target.iterdir())


def test_search_is_not_a_claim_of_current_image_bytes(root, make_image):
    from PIL import Image
    from riposte.sanitize import encode_clean
    row = sorted_images(root, make_image, 1)[0]
    (root/row['relative']).write_bytes(encode_clean(Image.new('RGB', (64,48), (240,5,10)), row['day']))
    assert search_library(root, search='moonlight')['total'] == 1
    with pytest.raises(RiposteError, match='CATALOG_FILE_CHANGED'):
        execute(Request('inspect', root, {'image_id':row['id']}))


def test_one_snapshot_no_repeated_catalog_reads(root, make_image, monkeypatch):
    sorted_images(root, make_image, 130)
    queries = []
    original = sqlite3.connect
    def traced(*args, **kwargs):
        db = original(*args, **kwargs); db.set_trace_callback(queries.append); return db
    monkeypatch.setattr('riposte.library_search.sqlite3.connect', traced)
    report = search_library(root, limit=1)
    assert report['total'] == 130 and len(report['rows']) == 1
    assert len([q for q in queries if 'FROM images' in q]) == 1
    assert any(q == 'BEGIN' for q in queries)


def test_cli_api_private_response_never_added_to_default_state(root, make_image):
    sorted_images(root, make_image)
    runner = CliRunner()
    value = runner.invoke(app, ['--json', 'library-search', str(root), '--search', 'moonlight', '--limit', '1'])
    assert value.exit_code == 0, value.output
    assert json.loads(value.output)['total'] == 3
    before = snapshot(root)
    with TestClient(create_app(root, 'private-test')) as client:
        assert client.post('/api/library-search', json={}).status_code == 401
        client.headers['X-Riposte-Token'] = 'private-test'
        assert 'Private-Caf' not in client.get('/api/state').text
        for body in ({'root':'elsewhere'},{'apply':True},{'limit':True},{'limit':501},{'title_state':'bad'}):
            assert client.post('/api/library-search', json=body).status_code == 422
        response = client.post('/api/library-search', json={'search':'moonlight','limit':1})
        assert response.status_code == 200 and response.json()['total'] == 3
        assert response.headers['cache-control'] == 'no-store'
        assert 'original_filename' not in client.get('/api/state').text
    assert snapshot(root) == before


def test_terminal_optin_filter_paging_selection_and_command(root, make_image):
    from riposte.terminal.controller import Controller
    from riposte.terminal.output import Presentation
    from riposte.terminal.keyboard import Key
    from riposte.terminal.actions import request_argv
    from riposte.terminal.render import render
    sorted_images(root, make_image)
    ctl = Controller(root, Presentation())
    ctl.library(); ctl.key(Key('char','s'))
    assert ctl.state.page.action == 'library-search'
    ctl.state.page.values.update(search='moonlight', limit=1)
    request = ctl.request_from_form()
    assert CliRunner().invoke(app, request_argv(request)[1:]).exit_code == 0
    def finish():
        for _ in range(200):
            ctl.pump()
            if ctl.state.operation is None: break
            time.sleep(.01)
        assert ctl.state.page.values['private_search']
    ctl.run_form(); finish()
    first = ctl.state.page.rows[0]['id']
    ctl.key(Key('enter')); assert first in ctl.state.selected
    ctl.key(Key('char',']')); finish()
    assert ctl.state.page.rows[0]['id'] != first and ctl.state.page.result['offset'] == 1
    ctl.state.width=72; ctl.state.height=24
    assert 'PRIVATE' in render(ctl.state, 72, 24).plain()
    assert not any('original_filename' in r for r in ctl.state.catalog)
    ctl.key(Key('char','/')); assert ctl.state.page.action == 'library-search'
    ctl.shutdown()


def test_undo_removes_current_search_provenance(root, make_image):
    sorted_images(root, make_image, 1)
    preview = undo_sort(root)
    undo_sort(root, apply=True, sort_id=preview['sort_id'])
    assert search_library(root)['total'] == 0


def test_library_search_browser_native(root,make_image):
    import os
    from pathlib import Path
    import shutil
    import socket
    import subprocess
    import threading
    import time
    import uvicorn
    from riposte.organizer import organize,plan
    from riposte.policy import Policy
    node=shutil.which('node')
    browser=next((p for p in [os.environ.get('RIPOSTE_TEST_BROWSER',''),shutil.which('chromium'),
        'C:/Program Files/Google/Chrome/Application/chrome.exe','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'] if p and Path(p).is_file()),None)
    if not node or not browser:pytest.skip('Local Node and Chromium required')
    sorted_images(root, make_image, 52)
    before=snapshot(root)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    server=uvicorn.Server(uvicorn.Config(create_app(root,'search-native'),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        assert server.started
        args=[node,str(Path(__file__).with_name('library_search_browser.cjs')),browser]
        if os.environ.get('RIPOSTE_SEARCH_SCREENSHOTS'):args.append(os.environ['RIPOSTE_SEARCH_SCREENSHOTS'])
        run=subprocess.run(args,env={**os.environ,'RIPOSTE_SORT_LIVE':f'http://127.0.0.1:{listener.getsockname()[1]}/#token=search-native'},
                           capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert run.returncode==0,run.stdout+run.stderr
        assert run.stdout.strip()=='PASS library_search_browser'
        assert snapshot(root)==before
        assert not (root/'.riposte/publishing').exists()
    finally:server.should_exit=True;thread.join(10);listener.close()
