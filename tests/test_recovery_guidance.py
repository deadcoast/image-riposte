"""Shared recovery semantics, safe boundaries and readable small-terminal errors."""
import json
from pathlib import Path
import subprocess
import time

import pytest

from riposte.errors import RiposteError
from riposte.terminal.output import Presentation, error
from riposte.recovery import CATALOG, guidance


def test_error_constructor_never_keeps_private_exception_text():
    problem = RiposteError('C:\\private\\artwork.png: decoder failed\nsecret')
    assert problem.code == str(problem) == 'OPERATION_FAILED'


def test_unknown_human_error_has_safe_next_action(capsys):
    error('FUTURE_FAILURE', Presentation(plain=True))
    rendered = capsys.readouterr().err
    assert 'FUTURE_FAILURE' in rendered
    assert 'Next action:' in rendered
    assert 'automatically' in rendered


def test_machine_error_stays_code_only(capsys):
    error('SORT_HISTORY_INVALID', Presentation(json_output=True))
    assert json.loads(capsys.readouterr().err) == {'error': 'SORT_HISTORY_INVALID'}


@pytest.mark.parametrize('code,expected', [
    ('WORKSPACE_LOCKED', 'Do not delete lock files'),
    ('SORT_HISTORY_INVALID', 'do not delete or reset the history'),
    ('SORT_RECOVERY_REQUIRED', 'Undo last sort'),
    ('UNDO_SOURCE_OCCUPIED', 'Move that file somewhere safe'),
    ('UNDO_OUTPUT_CHANGED', 'Do not overwrite your only edited copy'),
    ('UNDO_ASSIGNMENTS_CHANGED', 'do not reset assignment records'),
    ('CATEGORY_RULES_CHANGED', 'Copy any draft edits'),
    ('CATEGORY_REVISION_REQUIRED', 'do not invent a revision'),
    ('CATEGORY_ASSIGNMENT_INVALID', 'optional'),
    ('SORT_PREVIEW_CHANGED', 'refreshed plan'),
])
def test_actionable_safety_boundaries(code, expected):
    assert expected in guidance(code).action


@pytest.mark.parametrize('code', ['AMBIGUOUS', 'ORIGINAL_TITLE_UNAVAILABLE', 'UNMATCHED'])
def test_optional_category_information_never_requires_assignment(code):
    item = guidance(code, 'sort')
    assert item.level == 'info'
    assert 'No correction is required to sort' in item.action
    assert 'Year/Month' in item.action


def test_unknown_failure_uses_operation_and_preserves_only_safe_code():
    assert 'fresh sort preview' in guidance('FUTURE_FAILURE', 'apply').action
    assert 'Copy any edits' in guidance('FUTURE_FAILURE', 'category-rules-save').action
    assert 'Undo last sort' in guidance('FUTURE_FAILURE', 'undo-sort').action
    assert 'no files' in guidance('FUTURE_FAILURE', 'duplicates/scan/findings').action
    assert guidance('C:\\private\\file.png', 'apply').code == 'OPERATION_FAILED'


def test_full_recovery_remains_readable_at_72_by_24(root):
    from riposte.terminal.controller import Controller
    from riposte.terminal.keyboard import Key
    from riposte.terminal.render import render, scroll_limit
    from riposte.terminal.service import Request
    from riposte.terminal.state import Page
    controller = Controller(root, Presentation())
    try:
        controller.show(Page('result', 'STOPPED', code='WORKSPACE_LOCKED', request=Request('apply', root)))
        controller.state.width, controller.state.height = 72, 24
        assert scroll_limit(controller.state) > 0
        frames = []
        for _ in range(scroll_limit(controller.state)+1):
            frames.append(render(controller.state, 72, 24, 0).plain())
            controller.key(Key('down'))
        text = '\n'.join(frames)
        assert 'WORKSPACE_LOCKED' in text
        assert 'Do not delete lock files.' in ' '.join(text.split())
        assert not list(root.iterdir()), 'guidance and scrolling must not write'
        controller.key(Key('enter'))
        assert controller.state.operation is None, 'Return must never retry a write'
    finally:
        controller.shutdown()


def test_actual_api_and_job_errors_sanitize_private_text(root, monkeypatch):
    from fastapi.testclient import TestClient
    from riposte import server
    def fail(*args, **kwargs):
        raise RiposteError('C:\\private\\artwork.png: secret decoder message')
    monkeypatch.setattr(server, 'audit_workspace', fail)
    app = server.create_app(root, 'recovery-test')
    with TestClient(app) as client:
        client.headers['X-Riposte-Token'] = 'recovery-test'
        response = client.get('/api/audit')
        assert response.status_code == 400
        assert response.json() == {'code': 'OPERATION_FAILED'}
        jobs = app.state.jobs
        started = jobs.start(fail, read_only=True, operation='sort')
        for _ in range(500):
            row = next(j for j in jobs.snapshot() if j['id'] == started['job_id'])
            if row['state'] == 'error': break
            time.sleep(.01)
        assert row['code'] == 'OPERATION_FAILED' and row['operation'] == 'sort'
        assert 'private' not in json.dumps(row)
        assert client.get('/static/recovery-catalog.json').json() == CATALOG


def test_javascript_catalog_parity_and_unavailable_bundle_fallback():
    from dataclasses import asdict
    vectors = [{'code': code, 'operation': op} for code in [*CATALOG['entries'], 'UNKNOWN_FAILURE', 'C:\\private', 'ABC\n', None] for op in ['', 'apply', 'category-rules-save', 'undo-sort', 'duplicates/scan/report', 'publish']]
    script = Path(__file__).with_name('recovery_guidance.cjs')
    result = subprocess.run(['node', str(script)], input=json.dumps(vectors), capture_output=True, text=True, check=True)
    observed = json.loads(result.stdout)
    assert observed['normal'] == [asdict(guidance(v['code'], v['operation'])) for v in vectors]
    assert observed['fallback']['code'] == 'WORKSPACE_LOCKED'
    assert 'Guidance is unavailable' in observed['fallback']['action']
    assert 'automatically' in observed['fallback']['action']
