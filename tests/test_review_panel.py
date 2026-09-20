"""Real local review plumbing, synthetic generation, and finite-panel mathematics."""
import importlib.util
import itertools
import json
from fractions import Fraction
from zipfile import ZipFile

import pytest
from typer.testing import CliRunner

from riposte.cli import app
from riposte.errors import RiposteError
from riposte.experiment import ENDPOINTS, experiment_status
from riposte.sanitize import png_audit
from riposte.terminal.service import Request, execute
from test_experiment import prepared, generate


def test_panel_workflow_is_available():
    assert importlib.util.find_spec('riposte.review_panel') is not None


def test_exact_agreement_is_available():
    assert importlib.util.find_spec('riposte.agreement') is not None


def test_panel_cli_is_available():
    result = CliRunner().invoke(app, ['panel-create', '--help'])
    assert result.exit_code == 0, result.output


def ratio(value):
    return Fraction(value['numerator'], value['denominator'])


def test_agreement_bounds_are_attainable_over_every_small_completion():
    from riposte.agreement import binary_agreement
    for reviewers in range(2, 6):
        for row in itertools.product((False, True, None), repeat=reviewers):
            result = binary_agreement([row])
            unknown = [i for i, v in enumerate(row) if v is None]
            possibilities = []
            for completion in itertools.product((False, True), repeat=len(unknown)):
                filled = list(row)
                for i, v in zip(unknown, completion):
                    filled[i] = v
                possibilities.append(Fraction(sum(a == b for a, b in itertools.combinations(filled, 2)), reviewers*(reviewers-1)//2))
            assert ratio(result['bounds']['lower']) == min(possibilities)
            assert ratio(result['bounds']['upper']) == max(possibilities)
            assert (result['agreement'] is None) == bool(unknown)
            if not unknown:
                assert ratio(result['agreement']) == possibilities[0]


def test_cohen_counts_prevalence_degeneracy_and_missingness():
    from riposte.agreement import binary_agreement
    result = binary_agreement([(True, True)]*3 + [(False, True)] + [(False, False)]*2)
    pair = result['pairs'][0]
    assert pair['counts'] == {'yes_yes': 3, 'yes_no': 0, 'no_yes': 1, 'no_no': 2, 'missing': 0}
    assert ratio(pair['observed_agreement']) == Fraction(5, 6)
    assert ratio(pair['chance_agreement']) == Fraction(1, 2)
    assert ratio(pair['kappa']) == Fraction(2, 3)
    assert pair['status'] == 'DESCRIPTIVE'
    degenerate = binary_agreement([(True, True)]*5)['pairs'][0]
    assert degenerate['kappa'] is None and degenerate['status'] == 'UNDEFINED_CONSTANT_MARGINALS'
    missing = binary_agreement([(True, True), (None, False)])
    assert missing['pairs'][0]['kappa'] is None
    assert missing['pairs'][0]['counts']['missing'] == 1
    assert missing['planned_pairs'] == 2 and missing['agreement'] is None
    assert ratio(binary_agreement([(None, None, None)])['bounds']['lower']) == Fraction(1, 3)


@pytest.mark.parametrize('rows', [[], [(True,)], [(True, False), (False,)], [(1, False)], [('true', None)]])
def test_agreement_rejects_invalid_matrix(rows):
    from riposte.agreement import binary_agreement
    with pytest.raises(ValueError):
        binary_agreement(rows)


def packet_ratings(root, panel, reviewer):
    from riposte.review_panel import panel_packet
    receipt = panel_packet(root, panel['protocol']['id'], reviewer)
    with ZipFile(root/receipt['relative']) as archive:
        return receipt, json.loads(archive.read('ratings.json'))


@pytest.mark.parametrize('task', ['edit', 'inpaint', 'video'])
def test_task_rubric_packets_and_separate_responses(root, tmp_path, prepared, task):
    from riposte.review_panel import create_panel, panel_status, record_panel_review
    run = generate(root, tmp_path, prepared, task=task)
    panel = create_panel(root, [run['id']], reviewers=3)
    protocol = panel['protocol']; identifier = protocol['id']
    assert protocol['task'] == task and protocol['rubric']['task'] == task
    assert protocol['rubric']['validation'] == 'UNVALIDATED_CANDIDATE'
    assert panel['analysis']['status'] == 'INCOMPLETE'
    assert len(protocol['items']) == 5 and len(protocol['reviewers']) == 3
    original_samples = set().union(*(g['samples'].values() for g in experiment_status(root, run['id'])['protocol']['groups']))
    alias_sets = []
    for index, reviewer in enumerate(protocol['reviewers']):
        receipt, ratings = packet_ratings(root, panel, reviewer)
        aliases = set(ratings['ratings']); alias_sets.append(aliases)
        assert not aliases & original_samples
        assert ratings['panel_sha256'] == panel['sha256']
        with ZipFile(root/receipt['relative']) as archive:
            instructions = json.loads(archive.read('instructions.json'))
            assert instructions['rubric'] == protocol['rubric']
            for alias in aliases:
                assert f'items/{alias}/reference.png' in archive.namelist()
                assert f'items/{alias}/F000.png' in archive.namelist()
                assert (f'items/{alias}/F001.png' in archive.namelist()) == (task == 'video')
            for name in archive.namelist():
                assert archive.getinfo(name).date_time == (1980, 1, 1, 0, 0, 0)
                if name.endswith('.png'):
                    assert png_audit(archive.read(name))['date'] == prepared['date']
            assert all(word not in archive.read('instructions.json').decode() for word in ('control_1', 'candidate_sha256', str(tmp_path)))
        ratings['ratings'] = {alias: dict.fromkeys(ENDPOINTS, index != 2) for alias in aliases}
        submitted = tmp_path/f'{reviewer}.json'; submitted.write_text(json.dumps(ratings))
        response = record_panel_review(root, identifier, submitted)
        assert response['reviewer_id'] == reviewer
        with pytest.raises(RiposteError, match='PANEL_REVIEW_EXISTS'):
            record_panel_review(root, identifier, submitted)
    assert all(not a & b for a,b in itertools.combinations(alias_sets, 2))
    status = panel_status(root, identifier)
    assert status['analysis']['status'] == 'DESCRIPTIVE'
    assert all(ratio(result['agreement']) == Fraction(1, 3) for result in status['analysis']['endpoints'].values())
    assert status['analysis']['disagreement_items'] == list(protocol['items'])
    assert status['analysis']['ai_protection'] == 'UNVERIFIED'
    assert experiment_status(root, run['id'])['reviews'] == []


def test_null_response_is_retained_and_slot_cannot_be_replaced(root, tmp_path, prepared):
    from riposte.review_panel import create_panel, panel_status, record_panel_review
    run = generate(root, tmp_path, prepared)
    panel = create_panel(root, [run['id']]); pid = panel['protocol']['id']
    reviewer = next(iter(panel['protocol']['reviewers']))
    _, ratings = packet_ratings(root, panel, reviewer)
    path = tmp_path/'ratings.json'; path.write_text(json.dumps(ratings))
    record_panel_review(root, pid, path)
    status = panel_status(root, pid)
    assert status['analysis']['submitted_reviewers'] == 1
    assert status['analysis']['status'] == 'INCOMPLETE'
    assert status['analysis']['endpoints']['usable']['missing_decisions'] == 10
    assert len(panel_status(root)['panels']) == 1


@pytest.mark.parametrize('corruption', ['integer', 'sample', 'panel', 'reviewer', 'extra', 'duplicate', 'oversized'])
def test_bad_submissions_leave_no_response(root, tmp_path, prepared, corruption):
    from riposte.review_panel import create_panel, panel_status, record_panel_review
    run = generate(root, tmp_path, prepared)
    panel = create_panel(root, [run['id']]); pid = panel['protocol']['id']
    reviewer = next(iter(panel['protocol']['reviewers']))
    _, ratings = packet_ratings(root, panel, reviewer)
    if corruption == 'integer':
        ratings['ratings'][next(iter(ratings['ratings']))]['usable'] = 1
    elif corruption == 'sample':
        ratings['ratings']['unknown'] = ratings['ratings'].pop(next(iter(ratings['ratings'])))
    elif corruption == 'panel':
        ratings['panel_sha256'] = '0'*64
    elif corruption == 'reviewer':
        ratings['reviewer_id'] = '0'*32
    elif corruption == 'extra':
        ratings['secret'] = str(tmp_path)
    text = json.dumps(ratings)
    if corruption == 'duplicate':
        text = text[:-1]+', "panel_sha256": "duplicate"}'
    elif corruption == 'oversized':
        text = ' ' * 1_048_577
    path = tmp_path/'ratings.json'; path.write_text(text)
    with pytest.raises(RiposteError):
        record_panel_review(root, pid, path)
    assert panel_status(root, pid)['analysis']['submitted_reviewers'] == 0


@pytest.mark.parametrize('target', ['protocol', 'frame', 'packet', 'response', 'report'])
def test_panel_rechecks_exact_inputs_and_outputs(root, tmp_path, prepared, target):
    from riposte.review_panel import create_panel, panel_status, record_panel_review
    run = generate(root, tmp_path, prepared)
    panel = create_panel(root, [run['id']]); pid = panel['protocol']['id']
    reviewer = next(iter(panel['protocol']['reviewers']))
    receipt, ratings = packet_ratings(root, panel, reviewer)
    path = tmp_path/'ratings.json'; path.write_text(json.dumps(ratings))
    record_panel_review(root, pid, path)
    prefix = root/'.riposte/review-panels'/pid
    targets = {'protocol': prefix/'protocol.json', 'packet': root/receipt['relative'],
               'response': prefix/'responses'/f'{reviewer}.json',
               'report': root/'.riposte/generations'/run['id']/'report.json',
               'frame': root/'.riposte/generations'/run['id']/next(iter(run['artifacts']))}
    targets[target].write_bytes(targets[target].read_bytes()+b'changed')
    with pytest.raises(RiposteError):
        panel_status(root, pid)


def test_custom_rubric_is_frozen_and_bad_selection_does_not_commit(root, tmp_path, prepared):
    from riposte.review_panel import create_panel, default_rubric
    run = generate(root, tmp_path, prepared)
    for reviewers in (1, 9, True):
        with pytest.raises(RiposteError, match='PANEL_SELECTION_INVALID'):
            create_panel(root, [run['id']], reviewers)
    with pytest.raises(RiposteError, match='PANEL_SELECTION_INVALID'):
        create_panel(root, [run['id'], run['id']])
    rubric = default_rubric('video')
    path = tmp_path/'rubric.json'; path.write_text(json.dumps(rubric))
    with pytest.raises(RiposteError, match='PANEL_RUBRIC_INVALID'):
        create_panel(root, [run['id']], rubric_path=path)
    assert not (root/'.riposte/review-panels').exists()
    rubric = default_rubric('edit'); rubric['name'] = 'Local calibration rule'
    path.write_text(json.dumps(rubric))
    panel = create_panel(root, [run['id']], rubric_path=path)
    path.write_text('changed external file')
    assert panel['protocol']['rubric']['name'] == 'Local calibration rule'


def test_cli_and_service_use_same_panel_boundaries(root, tmp_path, prepared):
    run = generate(root, tmp_path, prepared)
    runner = CliRunner()
    result = runner.invoke(app, ['--json','panel-create',str(root),'--run',run['id'],'--reviewers','2'])
    assert result.exit_code == 0, result.output
    panel = json.loads(result.stdout); pid = panel['protocol']['id']
    reviewer = next(iter(panel['protocol']['reviewers']))
    packet = execute(Request('panel-packet', root, {'panel_id': pid, 'reviewer_id': reviewer}))
    with ZipFile(root/packet['relative']) as archive:
        ratings = json.loads(archive.read('ratings.json'))
    path = tmp_path/'rating.json'; path.write_text(json.dumps(ratings))
    result = runner.invoke(app,['--json','panel-review',str(root),pid,'--ratings',str(path)])
    assert result.exit_code == 0, result.output
    status = execute(Request('panel',root,{'panel_id':pid}))
    assert status['analysis']['submitted_reviewers'] == 1


def test_multiple_runs_are_joined_once_and_mixed_tasks_rejected(root, tmp_path, prepared, monkeypatch):
    import riposte.review_panel as module
    first = generate(root, tmp_path, prepared)
    second = generate(root, tmp_path, prepared)
    panel = module.create_panel(root, [first['id'], second['id']])
    assert len(panel['protocol']['items']) == 10
    assert panel['analysis']['distinct_trials'] == 1
    calls = []
    original = module._bound_run
    def counted(root, identifier):
        calls.append(identifier)
        return original(root, identifier)
    monkeypatch.setattr(module, '_bound_run', counted)
    reviewer = next(iter(panel['protocol']['reviewers']))
    module.panel_packet(root, panel['protocol']['id'], reviewer)
    assert calls == [first['id'], second['id']]
    video = generate(root, tmp_path, prepared, task='video')
    with pytest.raises(RiposteError, match='PANEL_TASK_MISMATCH'):
        module.create_panel(root, [first['id'], video['id']])
    assert len(module.panel_status(root)['panels']) == 1


def test_packet_is_required_and_orphan_packet_fails_closed(root, tmp_path, prepared):
    from riposte.review_panel import create_panel, panel_packet, panel_status, record_panel_review
    run = generate(root, tmp_path, prepared)
    panel = create_panel(root, [run['id']]); pid = panel['protocol']['id']
    reviewer, assignment = next(iter(panel['protocol']['reviewers'].items()))
    ratings = {'panel_sha256': panel['sha256'], 'reviewer_id': reviewer,
               'ratings': {alias: dict.fromkeys(ENDPOINTS) for alias in assignment}}
    path = tmp_path/'ratings.json'; path.write_text(json.dumps(ratings))
    with pytest.raises(RiposteError, match='PANEL_PACKET_REQUIRED'):
        record_panel_review(root, pid, path)
    receipt = panel_packet(root, pid, reviewer)
    with pytest.raises(RiposteError, match='DESTINATION_EXISTS'):
        panel_packet(root, pid, reviewer)
    (root/receipt['relative']).with_suffix('.json').unlink()
    with pytest.raises(RiposteError, match='PANEL_PACKET_INCOMPLETE'):
        panel_status(root, pid)


def test_packet_export_failure_keeps_committed_panel_and_cleans_temp(root, tmp_path, prepared, monkeypatch):
    import riposte.review_panel as module
    run = generate(root, tmp_path, prepared)
    panel = module.create_panel(root, [run['id']]); pid = panel['protocol']['id']
    reviewer = next(iter(panel['protocol']['reviewers']))
    def fail(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(module, '_frame', fail)
    with pytest.raises(KeyboardInterrupt):
        module.panel_packet(root, pid, reviewer)
    folder = root/'.riposte/review-panels'/pid
    assert (folder/'protocol.json').is_file()
    assert not list(folder.rglob('*.tmp')) and not list(folder.rglob('*.zip'))
    assert module.panel_status(root, pid)['analysis']['submitted_reviewers'] == 0


def test_panel_commands_keep_shared_application_root_guards():
    from pathlib import Path
    import riposte.review_panel as module
    for command in ('panel', 'panel-create', 'panel-packet', 'panel-review'):
        with pytest.raises(RiposteError, match='APPLICATION'):
            execute(Request(command, Path(module.__file__).parent))
