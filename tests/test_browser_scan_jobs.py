"""Browser scan lifecycle: real read-only endpoints and deterministic race seams."""
import threading
import time

import pytest
from fastapi.testclient import TestClient

from riposte.errors import RiposteError
from riposte.server import Jobs, create_app
from riposte.sort_history import undo_sort
from riposte.organizer import organize, plan
from riposte.policy import Policy


def settled(jobs, identifier):
    for _ in range(500):
        result = next(row for row in jobs.snapshot() if row['id'] == identifier)
        if result['state'] not in {'queued', 'running'}:
            return result
        time.sleep(.01)
    pytest.fail('worker did not reach a terminal state')


@pytest.mark.parametrize('endpoint,body', [
    ('organize', {'date_mode': 'modified'}),
    ('organize', {'date_mode': 'modified', 'categories': True}),
    ('categories', {'min_count': 1}),
    ('category-rules', {'categories': ['Hockey=hockey'], 'review': True}),
    ('undo-sort', {}),
])
def test_readonly_browser_scans_are_jobs(root, make_image, endpoint, body):
    path = make_image(root / 'hockey-photo.png')
    before = (path.read_bytes(), path.stat().st_mtime_ns)
    app = create_app(root, 'scan-test')
    with TestClient(app) as client:
        client.headers['X-Riposte-Token'] = 'scan-test'
        response = client.post('/api/' + endpoint, json=body)
        assert response.status_code == 200, response.text
        identifier = response.json()['job_id']
        row = settled(app.state.jobs, identifier)
        assert row['cancellable'] and row['read_only']
        assert row['state'] in {'done', 'incomplete'}, row
    assert (path.read_bytes(), path.stat().st_mtime_ns) == before
    assert sorted(p.name for p in root.iterdir()) == [path.name]


def test_cancel_at_last_readonly_boundary_discards_result():
    entered, release = threading.Event(), threading.Event()
    jobs = Jobs()
    def scan(progress):
        progress({'phase': 'Inspecting files', 'processed': 7, 'total': 9})
        entered.set()
        assert release.wait(5)
        return {'ready': True, 'plan_id': 'unapproved-result'}
    try:
        identifier = jobs.start(scan, read_only=True)['job_id']
        assert entered.wait(5)
        jobs.cancel(identifier)
        release.set()
        row = settled(jobs, identifier)
        assert row['state'] == 'cancelled' and 'result' not in row
    finally:
        release.set()
        jobs.close()


def test_progress_is_bounded_and_cannot_overwrite_job_identity():
    entered, release = threading.Event(), threading.Event()
    jobs = Jobs()
    def scan(progress):
        progress({'phase': 'Inspecting', 'processed': 7, 'total': 9})
        progress({'phase': 'Ranking', 'processed': -4, 'total': 'invalid',
                  'result': {'pretend': True}, 'state': 'done', 'id': 'forged',
                  'secret': 'private-path'})
        entered.set()
        assert release.wait(5)
        return {'ready': True}
    try:
        identifier = jobs.start(scan, read_only=True)['job_id']
        assert entered.wait(5)
        row = jobs.snapshot()[0]
        assert row['id'] == identifier and row['state'] == 'running'
        assert row['phase'] == 'Ranking'
        assert 'result' not in row and 'secret' not in row
        assert 'processed' not in row and 'total' not in row
    finally:
        release.set()
        jobs.close()


@pytest.mark.parametrize('read_only', [True, False])
def test_shutdown_cancels_scans_but_allows_commits_to_finish(read_only):
    entered, release = threading.Event(), threading.Event()
    jobs = Jobs()
    def work(progress):
        entered.set()
        assert release.wait(5)
        progress({'phase': 'Finishing'})
        return {'checkpoint': 'COMPLETE'}
    try:
        identifier = jobs.start(work, cancellable=read_only, read_only=read_only)['job_id']
        assert entered.wait(5)
        jobs.close()
        with pytest.raises(RiposteError, match='JOB_MANAGER_CLOSED'):
            jobs.start(work)
        release.set()
        row = settled(jobs, identifier)
        assert row['state'] == ('cancelled' if read_only else 'done')
    finally:
        release.set()
        jobs.close()


def test_undo_preview_cooperates_without_cancelling_commit(root, make_image):
    path = make_image(root / 'hockey.png')
    original = path.read_bytes()
    policy = Policy(date_mode='modified')
    preview = plan(root, policy)
    organize(root, policy, plan_id=preview['plan_id'])
    before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    def cancel(event):
        raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='JOB_CANCELLED'):
        undo_sort(root, progress=cancel)
    assert before == {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert undo_sort(root, apply=True, progress=cancel)['checkpoint'] == 'COMPLETE'
    assert path.read_bytes() == original
