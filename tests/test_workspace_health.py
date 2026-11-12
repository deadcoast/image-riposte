"""Storage observations and real entry points; never a deletion/undo certificate."""
import json
import os
from pathlib import Path
import time

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from riposte.cli import app
from riposte.errors import RiposteError
from riposte.health import inspect_health, operation_observation, filesystem_capabilities
from riposte.locking import LEASE_NAME
from riposte.organizer import plan, organize
from riposte.policy import Policy
from riposte.server import create_app
from riposte.store import state_dir, workspace_lock
from riposte.terminal.actions import request_argv
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.reports import overview
from riposte.terminal.service import Request, execute


def snapshot(root):
    return {p.relative_to(root).as_posix(): (b'' if p.name == LEASE_NAME else p.read_bytes(), p.stat().st_mtime_ns)
            for p in root.rglob('*') if p.is_file() and not p.is_symlink()}


def history(root, make_image):
    make_image(root / 'drawing.png')
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    return next((root / '.riposte/sort-history').glob('*/journal.json'))


def test_empty_never_initializes_workspace(root, monkeypatch):
    def fail(*a, **k): pytest.fail('read-only health attempted a write')
    for name in ('mkdir', 'unlink', 'rename', 'replace', 'write_text', 'write_bytes'):
        monkeypatch.setattr(Path, name, fail)
    result = inspect_health(root)
    assert result['writes'] is False and result['usage']['workspace_bytes'] == 0
    assert result['history']['directories'] == 0 and result['checkpoint'] == 'COMPLETE'
    assert result['estimate']['sufficient_space'] is None
    assert not list(root.iterdir())


def test_usage_float_private_and_backup_envelope(root):
    (root / 'a.jpg').write_bytes(b'a' * 11)
    (root / 'extensionless').write_bytes(b'b' * 17)
    for name in ('_float_', '__FLOAT__'):
        (root / name).mkdir(); (root / name / 'b.jpg').write_bytes(b'c' * 13)
    state_dir(root); (root / '.riposte/notes').write_bytes(b'd' * 19)
    before = snapshot(root); result = inspect_health(root)
    assert snapshot(root) == before
    assert result['usage']['workspace_bytes'] == sum(len(v[0]) for v in before.values())
    assert result['usage']['float_bytes'] == 26
    assert result['estimate']['backup_envelope_bytes'] == 11
    assert result['usage']['other_bytes'] == 28
    assert result['estimate']['required_free_bytes'] is None
    assert 'extensionless' in result['estimate']['basis']


def test_float_root_excluded_from_estimate(root):
    child = root / '__float__'; child.mkdir(); (child / 'test.mp4').write_bytes(b'123')
    result = inspect_health(child)
    assert result['estimate']['backup_envelope_bytes'] == 0 and result['usage']['float_bytes'] == 3


def test_actual_recovery_and_legacy_state_remain_identical(root, make_image):
    history(root, make_image)
    before = snapshot(root); result = inspect_health(root)
    assert snapshot(root) == before
    assert result['history']['statuses'] == {'APPLIED': 1}
    assert result['history']['restore_verified'] is False
    assert result['usage']['recovery_bytes'] > 0
    (root / '.riposte').rename(root / '.shroud')
    from riposte.store import LEGACY_SIGNATURE
    (root / '.shroud/WORKSPACE').write_text(LEGACY_SIGNATURE)
    before = snapshot(root)
    assert inspect_health(root)['history']['statuses'] == {'APPLIED': 1}
    assert snapshot(root) == before and not (root / '.riposte').exists()


@pytest.mark.parametrize('status', ['APPLYING', 'UNDOING', 'UNDONE', 'OTHER'])
def test_history_status_not_restore_qualification(root, make_image, status):
    path = history(root, make_image); data = json.loads(path.read_text()); data['status'] = status
    path.write_text(json.dumps(data)); before = snapshot(root)
    result = inspect_health(root)
    assert result['history']['statuses'] == {status if status != 'OTHER' else 'UNVERIFIED': 1}
    assert result['status'] == ('OBSERVED' if status == 'UNDONE' else 'ATTENTION')
    assert snapshot(root) == before


@pytest.mark.parametrize('corruption', ['invalid-json', 'oversize', 'missing', 'bad-id', 'bad-backup', 'missing-field', 'hardlink'])
def test_unverified_histories_retained(root, make_image, corruption):
    path = history(root, make_image)
    if corruption == 'invalid-json': path.write_bytes(b'{broken')
    elif corruption == 'oversize': path.write_bytes(b' ' * (4 * 1024 * 1024 + 1))
    elif corruption == 'missing': path.unlink()
    elif corruption == 'hardlink': os.link(path, path.with_name('alias'))
    else:
        data = json.loads(path.read_text())
        if corruption == 'bad-id': data['id'] = 'elsewhere'
        elif corruption == 'bad-backup': data['entries'][0]['backup'] = '../outside'
        else: del data['entries'][0]['removed']
        path.write_text(json.dumps(data))
    before = snapshot(root); result = inspect_health(root)
    assert result['history']['statuses'] == {'UNVERIFIED': 1}
    assert result['status'] == 'ATTENTION' and snapshot(root) == before


def test_marker_observation_does_not_claim_or_reclaim(root):
    with workspace_lock(root):
        marker = (root / '.riposte/operation.lock').read_bytes()
        before = snapshot(root)
        result = inspect_health(root)
        assert result['operation']['status'] == 'LEASE_MARKER_PRESENT'
        assert result['operation']['ownership'] == 'NOT_TESTED'
        assert snapshot(root) == before
    (root / '.riposte/operation.lock').write_bytes(marker)  # matching but abandoned marker
    before = snapshot(root)
    assert operation_observation(root)['status'] == 'LEASE_MARKER_PRESENT'
    assert inspect_health(root)['status'] == 'ATTENTION'
    assert snapshot(root) == before
    (root / '.riposte/operation.lock').write_bytes(b'')
    before = snapshot(root)
    assert inspect_health(root)['operation']['status'] == 'UNRECOGNIZED_MARKER'
    assert snapshot(root) == before


def test_limits_cancellation_and_capacity_failure(root, monkeypatch):
    for n in range(8): (root / f'{n}.jpg').write_bytes(b'xyz')
    before = snapshot(root)
    limited = inspect_health(root, max_entries=3)
    assert limited['checkpoint'] == 'INCOMPLETE' and limited['coverage']['entries'] == 3
    assert limited['usage']['workspace_bytes'] == 9
    assert limited['coverage']['issues'] == {'ENTRY_LIMIT': 1}
    def cancel(_): raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='JOB_CANCELLED'): inspect_health(root, progress=cancel)
    def denied(_): raise PermissionError()
    monkeypatch.setattr('riposte.health.shutil.disk_usage', denied)
    failed = inspect_health(root)
    assert failed['capacity']['free_bytes'] is None and failed['checkpoint'] == 'INCOMPLETE'
    assert snapshot(root) == before


@pytest.mark.parametrize('value', [0, -1, True, 200001, 1.5])
def test_invalid_limits(root, value):
    with pytest.raises(RiposteError, match='RESOURCE_LIMIT_INVALID'): inspect_health(root, max_entries=value)


def test_link_and_fifo_not_followed(root, tmp_path):
    outside = tmp_path / 'outside'; outside.mkdir(); (outside / 'secret').write_bytes(b'x' * 1000)
    try: (root / 'linked').symlink_to(outside, target_is_directory=True)
    except OSError: pytest.skip('Symbolic links unavailable')
    result = inspect_health(root)
    assert result['usage']['workspace_bytes'] == 0
    assert result['coverage']['issues']['LINK_OR_REPARSE_SKIPPED'] == 1
    if hasattr(os, 'mkfifo'):
        os.mkfifo(root / 'pipe')
        assert inspect_health(root)['coverage']['issues']['NONREGULAR_SKIPPED'] == 1


def test_known_unsupported_volume_is_advice_not_sort_guard(root, monkeypatch):
    report = filesystem_capabilities(root)
    assert report['write_test'] == 'NOT_RUN'
    monkeypatch.setattr('riposte.health.filesystem_capabilities', lambda _: {**report, 'hard_links':'NOT_ADVERTISED','read_only':True})
    result = inspect_health(root)
    assert result['status'] == 'ATTENTION'
    assert any('supported writable' in s for s in result['guidance'])
    assert not list(root.iterdir())


def test_cli_service_and_terminal_settings(root):
    request = Request('health', root, {'max_entries':100})
    run = CliRunner().invoke(app, ['--json', *request_argv(request)[1:]])
    assert run.exit_code == 0, run.output
    assert json.loads(run.stdout)['mode'] == 'WORKSPACE_HEALTH'
    report = execute(request)
    assert overview(report, 'health', 72).title == 'Storage & recovery'
    controller = Controller(root, Presentation(no_animation=True))
    try:
        controller.preferences()
        controller.state.page.cursor = next(i for i, row in enumerate(controller.state.page.rows) if row['key'] == 'health')
        controller.key(Key('enter'))
        for _ in range(100):
            controller.pump()
            if not controller.state.operation: break
            time.sleep(.01)
        assert controller.state.page.result['mode'] == 'WORKSPACE_HEALTH'
    finally: controller.shutdown()
    assert not list(root.iterdir())


def test_api_authenticated_background_job_and_rejected_mutation(root):
    app = create_app(root, 'health-test')
    with TestClient(app) as client:
        assert client.post('/api/health', json={}).status_code == 401
        client.headers['X-Riposte-Token'] = 'health-test'
        for body in ({'prune':True}, {'root':'elsewhere'}, {'max_entries':True}):
            assert client.post('/api/health', json=body).status_code == 422
        response = client.post('/api/health', json={}); assert response.status_code == 200
        job_id = response.json()['job_id']
        for _ in range(100):
            job = next(j for j in client.get('/api/state').json()['jobs'] if j['id'] == job_id)
            if job['state'] not in {'queued','running'}: break
            time.sleep(.01)
        assert job['state'] == 'done' and job['read_only'] and job['operation'] == 'health'
        assert job['result']['writes'] is False
    assert not list(root.iterdir())


def test_partial_access_time_and_history_directory_failures(root, monkeypatch):
    (root / 'unreadable').mkdir()
    original = os.scandir
    def scan(path):
        if Path(path).name == 'unreadable': raise PermissionError()
        return original(path)
    monkeypatch.setattr('riposte.health.os.scandir', scan)
    result = inspect_health(root)
    assert result['checkpoint'] == 'INCOMPLETE'
    assert result['coverage']['issues']['PATH_UNREADABLE_OR_CHANGED'] == 1
    state_dir(root); (root / '.riposte/sort-history').write_bytes(b'invalid')
    result = inspect_health(root)
    assert result['coverage']['issues']['HISTORY_DIRECTORY_INVALID'] == 1
    ticks = iter([0., 31.])
    monkeypatch.setattr('riposte.health.time.monotonic', lambda: next(ticks))
    assert inspect_health(root)['coverage']['issues']['TIME_LIMIT'] == 1


def test_mutation_during_scan_is_not_complete_snapshot(root):
    (root / 'one.jpg').write_bytes(b'x')
    def mutate(event):
        if event['processed'] == 1 and not (root / 'late').exists(): (root / 'late').mkdir()
    result = inspect_health(root, progress=mutate)
    assert result['checkpoint'] == 'INCOMPLETE'
    assert result['coverage']['issues']['DIRECTORY_CHANGED'] >= 1


def test_root_and_unsafe_lease_safeguards(root):
    from riposte.store import application_directory
    with pytest.raises(RiposteError, match='IMAGE_FOLDER_OVERLAPS_APPLICATION'):
        inspect_health(application_directory())
    (root / LEASE_NAME).write_bytes(b'unknown owner')
    before = snapshot(root)
    with pytest.raises(RiposteError, match='STATE_PATH_INVALID'): inspect_health(root)
    assert snapshot(root) == before


def test_health_browser_native(root,make_image):
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
    make_image(root/'drawing.png');policy=Policy(date_mode='modified')
    organize(root,policy,plan_id=plan(root,policy)['plan_id'])
    before=snapshot(root)
    listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
    server=uvicorn.Server(uvicorn.Config(create_app(root,'health-native'),log_level='error'))
    thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
    try:
        for _ in range(100):
            if server.started:break
            time.sleep(.02)
        assert server.started
        args=[node,str(Path(__file__).with_name('health_browser.cjs')),browser]
        if os.environ.get('RIPOSTE_HEALTH_SCREENSHOTS'):args.append(os.environ['RIPOSTE_HEALTH_SCREENSHOTS'])
        run=subprocess.run(args,env={**os.environ,'RIPOSTE_SORT_LIVE':f'http://127.0.0.1:{listener.getsockname()[1]}/#token=health-native'},
                           capture_output=True,text=True,encoding='utf-8',timeout=90)
        assert run.returncode==0,run.stdout+run.stderr
        assert run.stdout.strip()=='PASS health_browser'
        assert snapshot(root)==before
        assert not (root/'.riposte/publishing').exists()
    finally:server.should_exit=True;thread.join(10);listener.close()
