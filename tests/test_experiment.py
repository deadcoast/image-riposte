"""Operational protocol/review regressions; generators here are test doubles."""
import itertools
import json
from zipfile import ZipFile

import pytest

from riposte.errors import RiposteError
from riposte.experiment import ENDPOINTS, ROLES, _analyze, experiment_status, record_review, review_packet
from riposte.generation import controlled_generation
from riposte.lab import compare_external
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.sanitize import png_audit
from riposte.store import catalog


@pytest.fixture
def prepared(root, tmp_path, make_image, monkeypatch):
    make_image(root / 'a.png', size=(32, 24))
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    candidate = make_image(tmp_path / 'candidate.png', size=(32, 24), color=(33, 93, 153))
    trial = compare_external(root, catalog(root)[0]['id'], candidate)
    class Generator:
        identity = {'kind': 'SYNTHETIC_TEST_GENERATOR'}
        def __init__(self, folder, task):
            self.task = task
        def __call__(self, image, seed, steps):
            receipts = list((root / '.riposte/experiments').glob('*/protocol.json'))
            assert receipts, 'Protocol must exist before the first generation call'
            sealed = json.loads(receipts[-1].read_text())
            assert sealed['protocol']['endpoints'] == ENDPOINTS
            return [image.copy()] * (2 if self.task == 'video' else 1)
    monkeypatch.setattr('riposte.generation.LocalGenerator', Generator)
    return trial


def generate(root, tmp_path, prepared, **kwargs):
    return controlled_generation(root, prepared['id'], tmp_path, seeds=(7,), views=('identity',), steps=1, **kwargs)


def filled(root, tmp_path, run, success=True):
    sealed = experiment_status(root, run['id'])
    ratings = {sample: dict.fromkeys(ENDPOINTS, success)
               for group in sealed['protocol']['groups'] for sample in group['samples'].values()}
    path = tmp_path / 'ratings.json'
    path.write_text(json.dumps({'protocol_sha256': sealed['sha256'], 'ratings': ratings}))
    return sealed, ratings, path


@pytest.mark.parametrize('task', ['edit', 'inpaint', 'video'])
def test_protocol_precedes_generation_and_packet_hides_conditions(root, tmp_path, prepared, task):
    run = generate(root, tmp_path, prepared, task=task)
    sealed = experiment_status(root, run['id'])
    assert sealed['outcome']['status'] == 'COMPLETE'
    assert run['experiment_sha256'] == sealed['sha256']
    assert sealed['protocol']['conditioning'] == run['conditioning']
    assert sealed['protocol']['model_family_holdout'].startswith('UNKNOWN')
    packet = review_packet(root, run['id'])
    with ZipFile(root / packet['relative']) as archive:
        assert len(archive.namelist()) == (13 if task == 'video' else 8)
        assert not any(role in name for name in archive.namelist() for role in ROLES)
        ratings = json.loads(archive.read('ratings.json'))
        assert len(ratings['ratings']) == 5 and all(v is None for row in ratings['ratings'].values() for v in row.values())
        instructions = json.loads(archive.read('instructions.json'))
        assert set(instructions) == {'task', 'conditioning', 'endpoints', 'instructions'}
        for name in archive.namelist():
            assert archive.getinfo(name).date_time == (1980, 1, 1, 0, 0, 0)
            if name.endswith('.png'):
                assert png_audit(archive.read(name))['date'] == prepared['date']
    assert str(tmp_path) not in json.dumps(sealed)
    with pytest.raises(RiposteError, match='DESTINATION_EXISTS'):
        review_packet(root, run['id'])


def test_review_appends_exact_arithmetic_and_retains_incomplete_ratings(root, tmp_path, prepared):
    run = generate(root, tmp_path, prepared)
    sealed, ratings, path = filled(root, tmp_path, run)
    samples = sealed['protocol']['groups'][0]['samples']
    ratings[samples['candidate']]['usable'] = False
    ratings[samples['control_3']]['source_preserved'] = False
    path.write_text(json.dumps({'protocol_sha256': sealed['sha256'], 'ratings': ratings}))
    first = record_review(root, run['id'], path)
    assert first['analysis']['contrast'] == {'numerator': 2, 'denominator': 3, 'value': 2/3}
    ratings[samples['control_3']]['usable'] = None
    path.write_text(json.dumps({'protocol_sha256': sealed['sha256'], 'ratings': ratings}))
    second = record_review(root, run['id'], path)
    assert second['analysis']['status'] == 'INCOMPLETE' and second['analysis']['contrast'] is None
    assert first['id'] != second['id']
    reviews = experiment_status(root, run['id'])['reviews']
    assert {r['id'] for r in reviews} == {first['id'], second['id']}
    assert all(r['analysis']['ai_protection'] == 'UNVERIFIED' for r in reviews)


@pytest.mark.parametrize('failure', ['cancel', 'error', 'interrupt'])
def test_failed_generation_remains_discoverable_without_partial_frames(root, tmp_path, prepared, monkeypatch, failure):
    calls = 0
    def fail(self, image, seed, steps):
        nonlocal calls
        calls += 1
        if calls == 2:
            if failure == 'interrupt':
                raise KeyboardInterrupt()
            raise RiposteError('JOB_CANCELLED') if failure == 'cancel' else RuntimeError(str(tmp_path))
        return [image.copy()]
    monkeypatch.setattr('riposte.generation.LocalGenerator.__call__', fail)
    with pytest.raises((RiposteError, RuntimeError, KeyboardInterrupt)):
        generate(root, tmp_path, prepared)
    entries = experiment_status(root)['experiments']
    assert len(entries) == 1
    assert entries[0]['status'] == ('FAILED' if failure == 'error' else 'CANCELLED')
    sealed = experiment_status(root, entries[0]['id'])
    assert str(tmp_path) not in json.dumps(sealed)
    assert not list((root / '.riposte/generations').rglob('*.png'))
    with pytest.raises(RiposteError, match='NOT_COMPLETE'):
        review_packet(root, entries[0]['id'])


@pytest.mark.parametrize('target', ['protocol', 'report', 'frame', 'review', 'trial'])
def test_drift_rejects_review_or_readback(root, tmp_path, prepared, target):
    run = generate(root, tmp_path, prepared)
    sealed, ratings, path = filled(root, tmp_path, run)
    review = record_review(root, run['id'], path)
    prefix = root / '.riposte'
    paths = {'protocol': prefix / f"experiments/{run['id']}/protocol.json",
             'report': prefix / f"generations/{run['id']}/report.json",
             'frame': prefix / f"generations/{run['id']}/{next(iter(run['artifacts']))}",
             'review': prefix / f"experiments/{run['id']}/reviews/{review['id']}.json",
             'trial': prefix / f"lab/{prepared['id']}/report.json"}
    dest = paths[target]
    if target == 'frame':
        dest.write_bytes(dest.read_bytes() + b'changed')
    else:
        value = json.loads(dest.read_text())
        if target == 'protocol':
            value['protocol']['steps'] = 2
        else:
            value['changed'] = True
        dest.write_text(json.dumps(value))
    with pytest.raises(RiposteError):
        experiment_status(root, run['id'])
    if target != 'review':
        with pytest.raises(RiposteError):
            record_review(root, run['id'], path)


@pytest.mark.parametrize('corruption', ['missing', 'extra', 'integer', 'string', 'wrong_protocol', 'extra_field'])
def test_invalid_ratings_do_not_create_review(root, tmp_path, prepared, corruption):
    run = generate(root, tmp_path, prepared)
    sealed, ratings, path = filled(root, tmp_path, run)
    value = json.loads(path.read_text())
    sample = next(iter(ratings))
    if corruption == 'missing':
        del value['ratings'][sample]
    elif corruption == 'extra':
        value['ratings']['unknown'] = dict.fromkeys(ENDPOINTS, True)
    elif corruption in ('integer', 'string'):
        value['ratings'][sample]['usable'] = 1 if corruption == 'integer' else 'true'
    elif corruption == 'wrong_protocol':
        value['protocol_sha256'] = '0' * 64
    else:
        value['private_path'] = str(tmp_path)
    path.write_text(json.dumps(value))
    with pytest.raises(RiposteError, match='RATINGS_INVALID'):
        record_review(root, run['id'], path)
    assert experiment_status(root, run['id'])['reviews'] == []


def test_binary_contrast_exhaustively_matches_paired_difference():
    samples = dict(zip(ROLES, ROLES))
    protocol = {'groups': [{'samples': samples}]}
    flags = {role: {'content_filter_flags': None} for role in ROLES}
    report = {'groups': [{'pipeline_flags': flags}]}
    for successes in itertools.product((False, True), repeat=5):
        ratings = {role: dict.fromkeys(ENDPOINTS, value) for role, value in zip(ROLES, successes)}
        result = _analyze(protocol, report, ratings)
        if not successes[0]:
            assert result['contrast'] is None and result['clean_failed_groups'] == 1
        else:
            expected = sum(int(successes[i]) - int(successes[1]) for i in (2, 3, 4))
            assert result['contrast']['numerator'] == expected
            assert -1 <= result['contrast']['value'] <= 1
        for role in ROLES:
            flags[role]['content_filter_flags'] = [True]
            filtered = _analyze(protocol, report, ratings)
            assert filtered['status'] == 'INCONCLUSIVE' and filtered['contrast'] is None
            flags[role]['content_filter_flags'] = None


def test_incomplete_other_group_cannot_be_cherry_picked():
    first = dict(zip(ROLES, ROLES))
    second = {role: role + '2' for role in ROLES}
    protocol = {'groups': [{'samples': first}, {'samples': second}]}
    flags = {role: {'content_filter_flags': None} for role in ROLES}
    report = {'groups': [{'pipeline_flags': flags}] * 2}
    ratings = {sample: dict.fromkeys(ENDPOINTS, True) for sample in [*first.values(), *second.values()]}
    ratings[second['candidate']]['usable'] = None
    result = _analyze(protocol, report, ratings)
    assert result['eligible_groups'] == 1 and result['status'] == 'INCOMPLETE' and result['contrast'] is None


def test_cli_service_roundtrip_and_application_root_guard(root, tmp_path, prepared):
    from pathlib import Path
    from typer.testing import CliRunner
    from riposte.cli import app
    from riposte.terminal.service import Request, execute
    import riposte.experiment as module
    runner = CliRunner()
    run = generate(root, tmp_path, prepared)
    listed = runner.invoke(app, ['--json', 'experiment', str(root)])
    assert listed.exit_code == 0, listed.output
    assert json.loads(listed.stdout)['experiments'][0]['id'] == run['id']
    packet = runner.invoke(app, ['--json', 'experiment-packet', str(root), run['id']])
    assert packet.exit_code == 0, packet.output
    _, _, path = filled(root, tmp_path, run)
    review = runner.invoke(app, ['--json', 'experiment-review', str(root), run['id'], '--ratings', str(path)])
    assert review.exit_code == 0, review.output
    assert json.loads(review.stdout)['analysis']['contrast']['value'] == 0
    status = execute(Request('experiment', root, {'run_id': run['id']}))
    assert len(status['reviews']) == 1
    for name in ('experiment', 'experiment-packet', 'experiment-review'):
        with pytest.raises(RiposteError, match='APPLICATION'):
            execute(Request(name, Path(module.__file__).parent, {'run_id': run['id'], 'ratings': path}))


def test_interrupted_receipt_is_open_and_legacy_run_not_relabelled(root, tmp_path, prepared, monkeypatch):
    import riposte.generation as generation
    from riposte.qualification import _verified_pair
    trial, pair = _verified_pair(root, prepared['id'])
    class Generator:
        identity = {'kind': 'SYNTHETIC_LEGACY_TEST'}
        def __call__(self, image, seed, steps):
            return [image.copy()]
    legacy = generation._execute(root, trial, pair, Generator(), 'edit', (7,), ('identity',), 1, None)
    assert 'experiment_sha256' not in legacy
    assert not experiment_status(root)['experiments']
    monkeypatch.setattr(generation, 'finish_experiment', lambda *args: None)
    run = generate(root, tmp_path, prepared)
    status = experiment_status(root, run['id'])
    assert status['outcome']['status'] == 'OPEN'
    with pytest.raises(RiposteError):
        review_packet(root, run['id'])


@pytest.mark.parametrize('kind', ['duplicate', 'oversized', 'packet_failure', 'outcome_drift', 'path_escape'])
def test_commit_and_input_boundaries(root, tmp_path, prepared, monkeypatch, kind):
    run = generate(root, tmp_path, prepared)
    sealed, ratings, path = filled(root, tmp_path, run)
    if kind in ('duplicate', 'oversized'):
        if kind == 'duplicate':
            path.write_text(path.read_text().replace('"usable": true', '"usable": false, "usable": true', 1))
        else:
            path.write_bytes(b' ' * 1_048_577)
        with pytest.raises(RiposteError):
            record_review(root, run['id'], path)
        assert not experiment_status(root, run['id'])['reviews']
    elif kind == 'packet_failure':
        def broken(*args, **kwargs):
            raise OSError('synthetic disk failure')
        monkeypatch.setattr(ZipFile, 'writestr', broken)
        with pytest.raises(OSError):
            review_packet(root, run['id'])
        folder = root / f".riposte/experiments/{run['id']}"
        assert {p.name for p in folder.iterdir()} == {'protocol.json', 'outcome.json'}
    elif kind == 'outcome_drift':
        outcome = root / f".riposte/experiments/{run['id']}/outcome.json"
        value = json.loads(outcome.read_text())
        value['protocol_sha256'] = '0' * 64
        outcome.write_text(json.dumps(value))
        with pytest.raises(RiposteError, match='PROTOCOL_CHANGED'):
            experiment_status(root, run['id'])
    else:
        for identifier in ('../escape', '/', 'a' * 33):
            with pytest.raises(RiposteError, match='NOT_FOUND'):
                review_packet(root, identifier)
