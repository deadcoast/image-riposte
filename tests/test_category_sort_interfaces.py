import json
import time

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from riposte.category_rules import load_rules
from riposte.cli import app
from riposte.server import create_app
from riposte.store import catalog
from riposte.terminal.actions import make_request, request_argv
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.service import Request, execute
from riposte.terminal.state import Presentation
from riposte.terminal.render import render


def job(client, endpoint, body):
    response = client.post('/api/' + endpoint, json=body)
    assert response.status_code == 200, response.text
    identifier = response.json()['job_id']
    for _ in range(500):
        value = next(j for j in client.get('/api/state').json()['jobs'] if j['id'] == identifier)
        if value['state'] not in {'queued', 'running'}: return value
        time.sleep(.01)
    pytest.fail('job did not finish')


def test_cli_exact_plan_requires_token_and_applies(root, make_image):
    make_image(root / 'hockey-player.png')
    runner = CliRunner()
    saved = runner.invoke(app, ['--json', 'category-rules', str(root), '--category', 'Hockey=hockey', '--save', '--expected-revision', 'missing'])
    assert saved.exit_code == 0, saved.output
    args = ['--json', 'sort', str(root), '--date-mode', 'modified', '--categories']
    preview = runner.invoke(app, args)
    assert preview.exit_code == 0, preview.output
    p = json.loads(preview.stdout)
    refused = runner.invoke(app, [*args, '--apply'])
    assert refused.exit_code != 0 and not catalog(root)
    result = runner.invoke(app, [*args, '--apply', '--plan-id', p['plan_id']])
    assert result.exit_code == 0, result.output
    assert '/hockey/' in catalog(root)[0]['relative']
    assert runner.invoke(app, ['--json', 'undo-sort', str(root), '--apply']).exit_code == 0
    assert (root / 'hockey-player.png').exists()


def test_terminal_rule_save_and_preview_bound_confirmation(root, make_image):
    make_image(root / 'hockey.png')
    controller = Controller(root, Presentation(no_animation=True))
    controller.action('organize')
    controller.key(Key('char', 's'))
    assert controller.state.page.action == 'category-rules'
    controller.state.page.values['category_specs'] = 'Hockey=hockey'
    controller.run_form(); controller.state.operation.join(); controller.pump()
    assert controller.state.page.result['status'] == 'DRAFT'
    controller.key(Key('char', 's'))
    page = controller.state.page
    assert page.name == 'confirm' and page.confirm_word == 'SAVE'
    assert page.confirm_request.values['expected_revision'] == 'missing'
    assert '--save' in request_argv(page.confirm_request)
    execute(page.confirm_request)
    assert load_rules(root).rules
    controller.action('organize')
    controller.state.page.values.update(categories=True, date_mode='modified')
    controller.run_form(); controller.state.operation.join(); controller.pump()
    result = controller.state.page.result
    assert result['ready']
    for width, height in ((79, 24), (100, 34), (132, 46)):
        frame = render(controller.state, width, height, 0).plain()
        assert all(len(line) <= width for line in frame.splitlines())
    controller.key(Key('enter'))
    request = controller.state.page.confirm_request
    assert request.values['plan_id'] == result['plan_id']
    assert execute(request)['checkpoint'] == 'COMPLETE'


def test_terminal_manual_assignment_json_and_command_roundtrip(root, make_image):
    make_image(root / 'SML01.png')
    request = make_request('organize', root, {'categories': True, 'date_mode': 'modified', 'assignments': '["SML01.png=uncategorized"]'})
    expected = execute(request)
    actual = CliRunner().invoke(app, ['--json', *request_argv(request)[1:]])
    assert actual.exit_code == 0, actual.output
    assert json.loads(actual.stdout) == expected
    assert expected['files'][0]['original_filename'] is None


def test_api_rules_discovery_sort_and_undo(root, make_image):
    source = make_image(root / 'hockey.png')
    original = source.read_bytes()
    with TestClient(create_app(root, 'category-test')) as client:
        for endpoint in ('categories', 'category-rules', 'organize', 'undo-sort'):
            assert client.post('/api/' + endpoint, json={}).status_code == 401
        client.headers['X-Riposte-Token'] = 'category-test'
        discovery = client.post('/api/categories', json={'min_count': 1})
        assert discovery.status_code == 200 and discovery.json()['candidates'][0]['term'] == 'hockey'
        draft = client.post('/api/category-rules', json={'categories': ['Hockey=hockey']}).json()
        assert draft['status'] == 'DRAFT' and not (root / '.riposte').exists()
        saved = client.post('/api/category-rules', json={'categories': ['Hockey=hockey'], 'save': True, 'expected_revision': draft['revision']})
        assert saved.status_code == 200 and saved.json()['status'] == 'SAVED'
        options = {'categories': True, 'date_mode': 'modified'}
        preview = job(client, 'organize', options)['result']
        assert client.post('/api/organize', json={**options, 'apply': True, 'plan_id': preview['plan_id']}).status_code == 400
        assert job(client, 'organize', {**options, 'apply': True, 'acknowledge_source_removal': True})['code'] == 'CATEGORY_PREVIEW_REQUIRED'
        applied = job(client, 'organize', {**options, 'apply': True, 'acknowledge_source_removal': True, 'plan_id': preview['plan_id']})
        assert applied['state'] == 'done', applied
        public = client.get('/api/state').json()['images']
        assert 'original_filename' not in public[0]
        undo = job(client, 'undo-sort', {})['result']
        assert undo['ready']
        assert client.post('/api/undo-sort', json={'apply': True, 'sort_id': undo['sort_id']}).status_code == 400
        restored = job(client, 'undo-sort', {'apply': True, 'sort_id': undo['sort_id'], 'acknowledge_restore': True})
        assert restored['state'] == 'done', restored
    assert source.read_bytes() == original and not catalog(root)


def test_combined_propagates_exact_category_consent_before_protection(root, make_image, monkeypatch):
    import riposte.publication as publication
    make_image(root / 'hockey.png')
    values = {'all_images': True, 'categories': True, 'date_mode': 'modified'}
    p = execute(Request('sort-riposte-plan', root, values))
    monkeypatch.setattr(publication, '_models', lambda *args: [])
    calls = []
    monkeypatch.setattr(publication, 'start_publication', lambda *args, **kwargs: calls.append(args) or {'mode': 'PUBLICATION_BATCH'})
    result = execute(Request('sort-riposte', root, {**values, 'plan_id': p['sorting']['plan_id']}))
    assert result['sorting']['checkpoint'] == 'COMPLETE' and len(calls) == 1


def test_category_browser_native():
    import os
    from pathlib import Path
    import shutil
    import subprocess
    node = shutil.which('node')
    browser = next((p for p in [os.environ.get('RIPOSTE_TEST_BROWSER', ''), shutil.which('chromium'),
                   'C:/Program Files/Google/Chrome/Application/chrome.exe',
                   'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe'] if p and Path(p).is_file()), None)
    if not node or not browser: pytest.skip('Local Node and Chromium required')
    run = subprocess.run([node, str(Path(__file__).with_name('category_sort_browser.cjs')), browser],
                         capture_output=True, text=True, encoding='utf-8', timeout=40)
    assert run.returncode == 0, run.stdout + run.stderr
    assert run.stdout.strip() == 'PASS category_sort_browser'
