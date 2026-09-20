"""Production cohort flow with synthetic generators; no real-model efficacy claim."""
from fractions import Fraction
import itertools
import json
import random

import pytest
from typer.testing import CliRunner

from riposte.cli import app
from riposte.errors import RiposteError
from riposte.experiment import ENDPOINTS, experiment_status, record_review, review_packet
from riposte.lab import compare_external
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.store import catalog


@pytest.fixture
def population(root, tmp_path, make_image, monkeypatch):
    for index in range(3):
        make_image(root / f'{index}.png', size=(32, 24), color=(30 + index * 30, 90, 150))
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    trials = [compare_external(root, row['id'], root / row['relative']) for row in catalog(root)]
    calls = {'loads': 0, 'generations': 0}
    class Generator:
        identity = {'kind': 'SYNTHETIC_COHORT_TEST'}
        def __init__(self, folder, task):
            calls['loads'] += 1
        def __call__(self, image, seed, steps):
            calls['generations'] += 1
            receipts = list((root / '.riposte/cohorts').glob('*/protocol.json'))
            assert receipts, 'Full cohort must be committed before any member output'
            stored = json.loads(receipts[-1].read_text())['protocol']
            assert len(stored['population']) == 3 and stored['analysis']['primary_review'] == 'FIRST_COMPLETE_REVIEW_BY_APPEND_SEQUENCE'
            return [image.copy()]
    monkeypatch.setattr('riposte.generation.LocalGenerator', Generator)
    return trials, calls


def generate(root, tmp_path, population, sample_size=3, **kwargs):
    from riposte.cohort import cohort_challenge
    return cohort_challenge(root, [trial['id'] for trial in population[0]], tmp_path, sample_size,
                            seeds=(7,), views=('identity',), steps=1, **kwargs)


def rate(root, tmp_path, run_id, candidate=True, control=True, clean=True):
    status = experiment_status(root, run_id)
    ratings = {sample: dict.fromkeys(ENDPOINTS, candidate if role == 'candidate' else clean if role == 'clean' else control)
               for group in status['protocol']['groups'] for role, sample in group['samples'].items()}
    path = tmp_path / 'ratings.json'
    path.write_text(json.dumps({'protocol_sha256': status['sha256'], 'ratings': ratings}))
    return record_review(root, run_id, path)


def test_new_commands_available():
    for command in ('cohort', 'cohort-challenge'):
        result = CliRunner().invoke(app, [command, '--help'])
        assert result.exit_code == 0, result.output


def test_draw_precedes_outputs_and_reuses_one_model(root, tmp_path, population, monkeypatch):
    import riposte.cohort as cohort
    monkeypatch.setattr(cohort.secrets, 'randbits', lambda n: 17)
    def no_repeated_run_scan(*args):
        raise AssertionError('Cohorts must not scan all generation runs separately for each member')
    monkeypatch.setattr('riposte.generation.generation_runs', no_repeated_run_scan)
    before_random = random.getstate()
    result = generate(root, tmp_path, population, sample_size=2)
    assert random.getstate() == before_random
    protocol = result['protocol']
    assert population[1] == {'loads': 1, 'generations': 10}
    expected = random.Random(17).sample(sorted(t['id'] for t in population[0]), 2)
    assert [m['trial_id'] for m in protocol['members']] == expected
    assert len({m['run_id'] for m in protocol['members']}) == 2
    assert result['outcome']['status'] == 'COMPLETE'
    assert result['summary']['mean'] is None and result['summary']['unscored_artworks'] == 2
    assert result['summary']['bounds']['lower']['value'] == -1
    assert result['summary']['bounds']['upper']['value'] == 1
    assert str(tmp_path) not in json.dumps(result)
    for member in result['members']:
        packet = review_packet(root, member['run_id'])
        assert packet['samples'] == 5


def test_primary_review_order_and_missing_outcome_denominator(root, tmp_path, population):
    from riposte.cohort import cohort_status
    result = generate(root, tmp_path, population)
    runs = [m['run_id'] for m in result['members']]
    rate(root, tmp_path, runs[0], candidate=None)
    first = rate(root, tmp_path, runs[0], candidate=False)
    assert first['sequence'] == 2
    rate(root, tmp_path, runs[0], candidate=True, control=False)
    partial = cohort_status(root, result['protocol']['id'])
    assert partial['members'][0]['primary_review_id'] == first['id']
    assert partial['summary']['mean'] is None
    assert partial['summary']['bounds']['lower']['value'] == -1/3
    assert partial['summary']['bounds']['upper']['value'] == 1
    rate(root, tmp_path, runs[1], candidate=True, control=False)
    rate(root, tmp_path, runs[2], clean=False)
    final = cohort_status(root, result['protocol']['id'])
    assert final['summary']['mean']['value'] == 0
    assert final['summary']['scored_artworks'] == 3
    assert final['summary']['ai_protection'] == 'UNVERIFIED'


@pytest.mark.parametrize('kind', ['failure', 'cancel'])
def test_partial_cohort_keeps_unattempted_members_in_bounds(root, tmp_path, population, monkeypatch, kind):
    from riposte.cohort import cohort_status
    original = __import__('riposte.generation', fromlist=['LocalGenerator']).LocalGenerator.__call__
    def fail(self, image, seed, steps):
        if population[1]['generations'] == 6:
            raise RiposteError('JOB_CANCELLED') if kind == 'cancel' else RuntimeError('synthetic failure')
        return original(self, image, seed, steps)
    monkeypatch.setattr('riposte.generation.LocalGenerator.__call__', fail)
    with pytest.raises((RiposteError, RuntimeError)):
        generate(root, tmp_path, population)
    identifier = cohort_status(root)['cohorts'][0]['id']
    result = cohort_status(root, identifier)
    assert [m['status'] for m in result['members']] == ['COMPLETE', 'CANCELLED' if kind == 'cancel' else 'FAILED', 'UNATTEMPTED']
    assert result['summary']['selected_artworks'] == 3 and result['summary']['unscored_artworks'] == 3
    failed = result['members'][1]['run_id']
    assert not list((root / f'.riposte/generations/{failed}').rglob('*.png'))
    rate(root, tmp_path, result['members'][0]['run_id'], candidate=False)
    assert cohort_status(root, identifier)['summary']['bounds']['lower']['value'] == -1/3


@pytest.mark.parametrize('sample_size', [0, 4, True])
def test_invalid_sample_size_cannot_load_or_generate(root, tmp_path, population, sample_size):
    with pytest.raises(RiposteError, match='PARAMETERS_INVALID'):
        generate(root, tmp_path, population, sample_size=sample_size)
    assert population[1] == {'loads': 0, 'generations': 0}


def test_duplicate_artworks_and_existing_outcomes_cannot_enter_pool(root, tmp_path, population):
    from riposte.cohort import cohort_challenge
    first = population[0][0]
    duplicate = compare_external(root, first['image_id'], root / f".riposte/lab/{first['id']}/candidate.png")
    with pytest.raises(RiposteError, match='DUPLICATE_CLEAN_RASTER'):
        cohort_challenge(root, [first['id'], duplicate['id']], tmp_path, 2)
    with pytest.raises(RiposteError, match='PARAMETERS_INVALID'):
        cohort_challenge(root, [first['id'], first['id']], tmp_path, 1)
    assert population[1]['loads'] == 0
    generate(root, tmp_path, population)
    with pytest.raises(RiposteError, match='ALREADY_GENERATED'):
        generate(root, tmp_path, population)
    assert population[1]['loads'] == 1
    with pytest.raises(RiposteError, match='ALREADY_GENERATED'):
        cohort_challenge(root, [duplicate['id']], tmp_path, 1)


def test_same_source_at_different_resolutions_is_one_sampling_unit(root, tmp_path, make_image, monkeypatch):
    from riposte.cohort import cohort_challenge
    source = make_image(root / 'large.png', size=(128, 96))
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    row = catalog(root)[0]
    first = compare_external(root, row['id'], root / row['relative'])
    smaller = make_image(tmp_path / 'smaller.png', size=(64, 48))
    variant = compare_external(root, first['image_id'], smaller, max_edge=64)
    def no_model(*args):
        raise AssertionError('Sampling duplicates must fail before model loading')
    monkeypatch.setattr('riposte.generation.LocalGenerator', no_model)
    with pytest.raises(RiposteError, match='DUPLICATE_SOURCE_IMAGE'):
        cohort_challenge(root, [first['id'], variant['id']], tmp_path, 2)


@pytest.mark.parametrize('target', ['cohort', 'member', 'review_gap', 'frame'])
def test_drift_is_invalid_not_a_dropped_member(root, tmp_path, population, target):
    from riposte.cohort import cohort_status
    result = generate(root, tmp_path, population)
    identifier = result['protocol']['id']
    run = result['members'][0]['run_id']
    first = rate(root, tmp_path, run)
    second = rate(root, tmp_path, run)
    if target == 'review_gap':
        (root / f".riposte/experiments/{run}/reviews/{first['id']}.json").unlink()
    elif target == 'frame':
        path = next((root / f'.riposte/generations/{run}').rglob('*.png'))
        path.write_bytes(path.read_bytes() + b'changed')
    else:
        path = root / (f'.riposte/cohorts/{identifier}/protocol.json' if target == 'cohort' else f'.riposte/experiments/{run}/protocol.json')
        data = json.loads(path.read_text())
        data['protocol']['steps'] = 77
        path.write_text(json.dumps(data))
    with pytest.raises(RiposteError):
        cohort_status(root, identifier)


def test_finite_sample_bounds_exhaustively_enclose_all_completions():
    from riposte.cohort import bounded_mean
    grid = (Fraction(-1), Fraction(-1, 3), Fraction(0), Fraction(2, 3), Fraction(1), None)
    for values in itertools.product(grid, repeat=3):
        result = bounded_mean(values)
        missing = sum(value is None for value in values)
        completed = []
        for replacements in itertools.product((Fraction(-1), Fraction(1)), repeat=missing):
            remaining = iter(replacements)
            completed.append(sum((next(remaining) if value is None else value for value in values), Fraction(0)) / len(values))
        bounds = result['bounds']
        assert Fraction(bounds['lower']['numerator'], bounds['lower']['denominator']) == min(completed)
        assert Fraction(bounds['upper']['numerator'], bounds['upper']['denominator']) == max(completed)
        assert bounds['upper']['value'] - bounds['lower']['value'] == pytest.approx(2 * missing / 3)
    for invalid in ([], [Fraction(2)]):
        with pytest.raises(RiposteError):
            bounded_mean(invalid)


def test_cancel_during_pool_preparation_has_no_committed_cohort(root, tmp_path, population):
    def cancel(event):
        if event.get('phase') == 'Verifying cohort sampling pool' and event.get('processed') == 1:
            raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='CANCELLED'):
        generate(root, tmp_path, population, progress=cancel)
    assert population[1] == {'loads': 0, 'generations': 0}
    assert not (root / '.riposte/cohorts').exists()


def test_clean_failure_is_zero_under_fixed_planned_group_denominator(root, tmp_path, population):
    from riposte.cohort import cohort_challenge, cohort_status
    result = cohort_challenge(root, [t['id'] for t in population[0]], tmp_path, 1,
                              seeds=(7, 19), views=('identity',), steps=1)
    run = result['members'][0]['run_id']
    status = experiment_status(root, run)
    ratings = {sample: dict.fromkeys(ENDPOINTS, role != 'candidate')
               for group in status['protocol']['groups'] for role, sample in group['samples'].items()}
    second_clean = status['protocol']['groups'][1]['samples']['clean']
    ratings[second_clean]['usable'] = False
    path = tmp_path / 'ratings.json'
    path.write_text(json.dumps({'protocol_sha256': status['sha256'], 'ratings': ratings}))
    review = record_review(root, run, path)
    assert review['analysis']['contrast']['value'] == 1
    cohort = cohort_status(root, result['protocol']['id'])
    assert cohort['summary']['mean']['value'] == .5
    assert cohort['members'][0]['analysis']['clean_failed_groups'] == 1


def test_legacy_review_receipts_keep_scope_and_new_appends_are_ordered(root, tmp_path, population):
    from riposte.experiment import _digest
    result = generate(root, tmp_path, population, sample_size=1)
    run = result['members'][0]['run_id']
    first = rate(root, tmp_path, run)
    legacy = {key: value for key, value in first.items() if key not in {'sequence', 'sha256'}}
    legacy['sha256'] = _digest(legacy)
    path = root / f".riposte/experiments/{run}/reviews/{first['id']}.json"
    path.write_text(json.dumps(legacy))
    assert experiment_status(root, run)['reviews'][0] == legacy
    assert rate(root, tmp_path, run)['sequence'] == 2
    from riposte.cohort import cohort_status
    with pytest.raises(RiposteError, match='ORDER_UNKNOWN'):
        cohort_status(root, result['protocol']['id'])


def test_reported_filtering_has_no_positive_credit(root, tmp_path, population, monkeypatch):
    import riposte.generation as generation
    from riposte.cohort import cohort_status
    original = generation.LocalGenerator.__call__
    def flagged(self, image, seed, steps):
        frames = original(self, image, seed, steps)
        self.last_flags = {'content_filter_reported': True, 'content_filter_flags': [population[1]['generations'] % 5 == 2]}
        return frames
    monkeypatch.setattr(generation.LocalGenerator, '__call__', flagged)
    result = generate(root, tmp_path, population, sample_size=1)
    rate(root, tmp_path, result['members'][0]['run_id'], candidate=False)
    reviewed = cohort_status(root, result['protocol']['id'])
    assert reviewed['summary']['mean']['value'] == 0
    assert reviewed['members'][0]['analysis']['filtered_groups'] == 1
    assert reviewed['members'][0]['analysis']['eligible_groups'] == 0


def test_cli_executes_real_cohort_service_and_root_guards(root, tmp_path, population):
    from pathlib import Path
    from riposte.terminal.service import Request, execute
    import riposte.cohort as module
    args = ['--json', 'cohort-challenge', str(root), '--model', str(tmp_path), '--sample-size', '2', '--seed', '7', '--view', 'identity', '--steps', '1']
    for trial in population[0]:
        args.extend(['--trial', trial['id']])
    result = CliRunner().invoke(app, args)
    assert result.exit_code == 0, result.output
    identifier = json.loads(result.stdout)['protocol']['id']
    inspected = CliRunner().invoke(app, ['--json', 'cohort', str(root), identifier])
    assert inspected.exit_code == 0, inspected.output
    assert json.loads(inspected.stdout)['summary']['selected_artworks'] == 2
    for command in ('cohort', 'cohort-challenge'):
        with pytest.raises(RiposteError, match='APPLICATION'):
            execute(Request(command, Path(module.__file__).parent))
