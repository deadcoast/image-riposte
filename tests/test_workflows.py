"""Independent workflows with real codecs/storage/CPU optimization.

The encoder is a synthetic differentiable oracle, not a pretrained model or
evidence of protection efficacy. All artwork is generated in pytest directories.
"""
from riposte.organizer import plan as _sort_preview
import io
import json
from pathlib import Path
from zipfile import ZipFile

import pytest
from PIL import Image

from riposte import cli, publication as p
from riposte.errors import RiposteError
from riposte.intake import input_files, inspect_inputs
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.quality import QualityLimits
from riposte.release_guard import ReleaseConfig
from riposte.sanitize import png_audit
from riposte.store import catalog, state_relative
from riposte.terminal.actions import request_argv
from riposte.terminal.app import linear_session
from riposte.terminal.controller import Controller
from riposte.terminal.keyboard import Key
from riposte.terminal.output import Presentation
from riposte.terminal.render import render
from riposte.terminal.service import Request, execute
from riposte.terminal.state import HOME


def snapshot(root):
    return {f.relative_to(root).as_posix(): f.read_bytes() for f in root.rglob('*') if f.is_file()}


@pytest.fixture
def recipe():
    return p.PublishRecipe((64,), ReleaseConfig(steps=2, restarts=1), QualityLimits())


@pytest.fixture
def models(monkeypatch):
    pytest.importorskip('torch')
    import riposte.models as adapters
    class Oracle:
        device = 'cpu'
        identity = {'kind': 'SYNTHETIC_WORKFLOW_ORACLE', 'weights_sha256': 'a' * 64}
        def __call__(self, x):
            return x.square() + .15 * x
    calls = []
    def load(*args):
        calls.append(args)
        return Oracle()
    monkeypatch.setattr(adapters, 'LocalEncoder', load)
    return calls


def values(**extra):
    return {'vae_dirs': [Path('SYNTHETIC_LOCAL_MODEL')], 'steps': 2, 'restarts': 1, 'edges': [64], **extra}


def reviewed_combined(root, options):
    preview = execute(Request('sort-riposte-plan', root, options))
    return Request('sort-riposte', root, {**options, 'plan_id': preview['plan_id']})


def settled(controller):
    assert controller.state.operation is not None
    assert controller.state.operation.done.wait(10)
    controller.pump()
    return controller.state.page


def test_raw_recursive_preview_is_readonly_and_deduplicates(root, tmp_path, make_image, recipe):
    sources = tmp_path / 'sources'
    a = make_image(sources / 'private name.png')
    make_image(sources / 'nested' / 'second.jpg')
    (sources / 'notes.txt').write_text('PRIVATE_NOTES')
    (sources / 'tags.xmp').write_text('PRIVATE_METADATA')
    before = snapshot(tmp_path)
    result = p.publication_plan(root, [], recipe, input_paths=[a, sources, sources / 'nested'], date_mode='modified')
    assert result['images'] == result['outputs'] == 2
    assert result['ignored_files'] == 2 and result['originals_preserved']
    assert snapshot(tmp_path) == before
    assert 'private name' not in json.dumps(result)


def test_unrelated_additions_do_not_block_selected_catalog(root, make_image, recipe):
    make_image(root / 'first.png')
    organize(root, Policy(date_mode='modified'), plan_id=_sort_preview(root, Policy(date_mode='modified'))["plan_id"])
    row = catalog(root)[0]
    make_image(root / 'addition.png')
    (root / 'notes.txt').write_text('unrelated')
    before = snapshot(root)
    assert p.publication_plan(root, [row['id']], recipe)['images'] == 1
    assert snapshot(root) == before
    (root / row['relative']).write_bytes(b'changed')
    with pytest.raises(RiposteError):
        p.publication_plan(root, [row['id']], recipe)


def test_standalone_batch_preserves_inputs_and_exports_exact_bytes(root, tmp_path, make_image, recipe, models):
    source = make_image(tmp_path / 'raw' / 'PRIVATE.png', size=(96, 80))
    before = source.read_bytes()
    batch = p.start_publication(root, [], [Path('MODEL')], recipe, input_paths=[source], date_mode='modified')
    assert source.read_bytes() == before and not catalog(root)
    assert batch['source_mode'] == 'snapshot' and len(models) == 1
    assert batch['counts']['READY_FOR_REVIEW'] == 1
    item = batch['items'][0]['id']
    exact = p.publication_pixels(root, batch['id'], item)
    assert png_audit(exact)['date'] == '2025-03-12'
    assert b'PRIVATE_FIXTURE_PAYLOAD' not in exact
    (root / 'another.txt').write_text('unrelated')
    p.review_publication(root, batch['id'], [item], visual_accepted=True, acknowledge_unverified=True)
    with ZipFile(io.BytesIO(p.publication_zip(root, batch['id']))) as archive:
        assert len(archive.namelist()) == 1
        assert archive.read(archive.namelist()[0]) == exact
    request = (root / state_relative(root, f"publishing/{batch['id']}/request.json")).read_text()
    assert 'PRIVATE' not in request and str(source) not in request


def test_snapshot_resume_is_independent_of_original_location(root, tmp_path, make_image, recipe, models):
    source = make_image(tmp_path / 'input.png', size=(96, 80))
    batch = p.start_publication(root, [], [Path('MODEL')], recipe, input_paths=[source])
    exact = p.publication_pixels(root, batch['id'], batch['items'][0]['id'])
    source.unlink()
    make_image(root / 'unorganized.png')
    resumed = p.resume_publication(root, batch['id'], [Path('MODEL')])
    assert resumed['counts']['READY_FOR_REVIEW'] == 1
    assert p.publication_pixels(root, batch['id'], batch['items'][0]['id']) == exact


def test_changed_snapshot_cannot_be_reviewed_or_resumed(root, make_image, recipe, models):
    source = make_image(root / 'input.png', size=(96, 80))
    batch = p.start_publication(root, [], [Path('MODEL')], recipe, input_paths=[source])
    item = batch['items'][0]
    path = root / state_relative(root, f"publishing/{batch['id']}/inputs/{item['image_id']}.png")
    path.write_bytes(path.read_bytes() + b'changed')
    assert p.publication_status(root, batch['id'])['counts']['BLOCKED'] == 1
    with pytest.raises(RiposteError):
        p.resume_publication(root, batch['id'], [Path('MODEL')])


def test_changed_input_after_inspection_requires_new_plan(root, make_image):
    source = make_image(root / 'input.png')
    sources, _ = inspect_inputs([source])
    make_image(source, color=(2, 3, 4))
    with pytest.raises(RiposteError, match='INPUT_CHANGED_REPLAN'):
        sources[0].snapshot(Policy())


def test_selected_directories_skip_application_state(root, make_image):
    make_image(root / 'raw.png')
    from riposte.store import state_dir
    state = state_dir(root)
    make_image(state / 'preview.png')
    files, _ = input_files([root])
    assert files == [root / 'raw.png']
    with pytest.raises(RiposteError, match='INPUT_APPLICATION_STATE_REJECTED'):
        input_files([state / 'preview.png'])


@pytest.mark.parametrize('args', [
    ['--input', 'image.png', '--all'], ['--input', 'image.png', '--image', 'a' * 32],
    ['--input', 'image.png', '--year', '2025'],
])
def test_raw_selection_conflicts_are_explicit(root, args, capsys):
    assert cli.main(['--json', 'riposte', str(root), *args, '--plan']) == 2
    assert json.loads(capsys.readouterr().err)['error'] == 'INPUT_SELECTION_CONFLICT'


def test_sort_alias_and_incremental_sort_never_run_protection(root, make_image, capsys, monkeypatch):
    monkeypatch.setattr(p, '_models', lambda *a, **kw: pytest.fail('sort loaded a model'))
    make_image(root / 'first.png')
    assert cli.main(['--json', 'sort', str(root), '--apply', '--date-mode', 'modified', '--plan-id', _sort_preview(root, Policy(date_mode='modified'))['plan_id']]) == 0
    capsys.readouterr()
    row = catalog(root)[0]
    before = (root / row['relative']).read_bytes()
    make_image(root / 'second.png')
    assert cli.main(['--json', 'sort', str(root), '--apply', '--date-mode', 'modified', '--plan-id', _sort_preview(root, Policy(date_mode='modified'))['plan_id']]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['counts'] == {'migrated': 1, 'already_clean': 1}
    assert (root / row['relative']).read_bytes() == before
    assert not (root / '.riposte/publishing').exists()


def test_combined_default_is_preview_and_missing_model_cannot_sort(root, make_image, capsys):
    make_image(root / 'input.png')
    before = snapshot(root)
    assert cli.main(['--json', 'sort-riposte', str(root), '--all']) == 0
    report = json.loads(capsys.readouterr().out)
    assert report['mode'] == 'SORT_RIPOSTE_PLAN' and not report['writes']
    assert snapshot(root) == before
    assert cli.main(['--json', 'sort-riposte', str(root), '--all', '--apply', '--plan-id', report['plan_id']]) == 2
    assert json.loads(capsys.readouterr().err)['error'] == 'NO_MODEL_NO_PROTECTION'
    assert snapshot(root) == before


def test_combined_success_loads_models_once(root, make_image, models):
    source = make_image(root / 'input.png', size=(96, 80))
    result = execute(reviewed_combined(root, values(all_images=True, date_mode='modified')))
    assert not source.exists() and len(catalog(root)) == 1
    assert result['workflow'] == 'SORT_RIPOSTE'
    assert result['sorting']['checkpoint'] == 'COMPLETE'
    assert result['counts']['READY_FOR_REVIEW'] == 1 and len(models) == 1


def test_combined_blockers_do_not_start_models_or_modify_sources(root, make_image, models):
    make_image(root / 'input.png')
    (root / 'notes.txt').write_text('keep')
    before = snapshot(root)
    result = execute(reviewed_combined(root, values(all_images=True)))
    assert result['protection'] == 'NOT_STARTED'
    assert snapshot(root) == before and not models


def test_combined_incomplete_sort_stops_protection(root, make_image, models, monkeypatch):
    import riposte.organizer as organizer
    make_image(root / 'input.png')
    real = organizer.record_image
    def concurrent_addition(*args, **kwargs):
        row = real(*args, **kwargs)
        (root / 'late.txt').write_text('arrived during sort')
        return row
    monkeypatch.setattr(organizer, 'record_image', concurrent_addition)
    result = execute(reviewed_combined(root, values(all_images=True)))
    assert result['checkpoint'] == 'INCOMPLETE' and result['protection'] == 'NOT_STARTED'
    assert not (root / '.riposte/publishing').exists()


@pytest.mark.parametrize('dimensions', [(79, 24), (100, 34), (132, 46)])
def test_three_workflow_forms_render_and_preview_commands_do_not_apply(root, make_image, dimensions):
    make_image(root / 'input.png')
    assert {'Riposte Sorter', 'Full Sort Workshop', 'RIPOSTE', 'Sort + RIPOSTE'} <= {entry[1] for entry in HOME}
    controller = Controller(root, Presentation())
    for key in ('organize', 'riposte', 'sort-riposte'):
        controller.action(key)
        text = render(controller.state, *dimensions, 0).plain()
        assert len(text.splitlines()) == dimensions[1]
        assert all(len(line) == dimensions[0] for line in text.splitlines())
        controller.key(Key('f4'))
        assert '--apply' not in request_argv(controller.state.page.request)
        controller.back()
    controller.shutdown()


def test_interactive_standalone_and_combined_consent(root, make_image, models):
    source = make_image(root / 'input.png', size=(96, 80))
    controller = Controller(root, Presentation())
    controller.action('riposte')
    controller.state.page.values.update(vae1='MODEL', steps=2, restarts=1, edges=(64,))
    controller.key(Key('char', 'p'))
    assert settled(controller).result['images'] == 1 and source.exists()
    controller.key(Key('enter'))
    assert settled(controller).name == 'batch' and source.exists() and not catalog(root)
    controller.action('sort-riposte')
    controller.state.page.values.update(vae1='MODEL', steps=2, restarts=1, edges=(64,))
    controller.key(Key('char', 'r'))
    assert settled(controller).result['mode'] == 'SORT_RIPOSTE_PLAN'
    controller.key(Key('enter'))
    assert controller.state.page.confirm_word == 'REPLACE' and source.exists()
    controller.key(Key('paste', 'WRONG')); controller.key(Key('enter'))
    assert controller.state.operation is None and source.exists()
    controller.key(Key('clear')); controller.key(Key('paste', 'REPLACE')); controller.key(Key('enter'))
    assert settled(controller).name == 'batch' and not source.exists()
    controller.shutdown()


def test_linear_user_can_preview_file_without_catalog_or_commands(root, make_image, monkeypatch):
    monkeypatch.setattr('riposte.store.application_directory', lambda: root.parent / 'application')
    source = make_image(root / 'input.png')
    before = snapshot(root)
    controller = Controller(root, Presentation(plain=True))
    transcript = io.StringIO()
    linear_session(controller, io.StringIO('2\ns\nenter\nenter\np\nq\n'), transcript)
    assert 'PUBLISHING PLAN' in transcript.getvalue()
    assert controller.state.page.result['images'] == 1 and source.exists()
    assert snapshot(root) == before
    controller.shutdown()


def test_interrupted_standalone_resumes_pending_item_from_snapshots(root, tmp_path, make_image, recipe, models):
    sources = [make_image(tmp_path / f'raw{n}.png', size=(96, 80)) for n in range(2)]
    def stop_after_first(event):
        if event.get('phase') == 'Preparing publishing image' and event['item'] == 2:
            raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='JOB_CANCELLED'):
        p.start_publication(root, [], [Path('MODEL')], recipe, input_paths=sources, progress=stop_after_first)
    batch = p.publication_status(root, p.publications(root)[0]['id'])
    assert batch['status'] == 'INTERRUPTED' and batch['counts']['READY_FOR_REVIEW'] == 1
    committed = next(item for item in batch['items'] if item['status'] == 'READY_FOR_REVIEW')
    exact = p.publication_pixels(root, batch['id'], committed['id'])
    for source in sources:
        source.unlink()
    resumed = p.resume_publication(root, batch['id'], [Path('MODEL')])
    assert resumed['counts']['READY_FOR_REVIEW'] == 2
    assert p.publication_pixels(root, batch['id'], committed['id']) == exact


def test_cancelled_snapshot_intake_discards_only_uncommitted_state(root, make_image, recipe, models):
    sources = [make_image(root / f'raw{n}.png') for n in range(2)]
    originals = [source.read_bytes() for source in sources]
    saves = 0
    def stop_second_snapshot(event):
        nonlocal saves
        if event.get('phase') == 'Saving clean input snapshot':
            saves += 1
            if saves == 2:
                raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='JOB_CANCELLED'):
        p.start_publication(root, [], [Path('MODEL')], recipe, input_paths=sources, progress=stop_second_snapshot)
    assert [source.read_bytes() for source in sources] == originals
    assert not p.publications(root) and not list((root / '.riposte/publishing').iterdir())


def test_cli_standalone_and_combined_use_real_publication_service(root, make_image, models, capsys):
    source = make_image(root / 'raw.png', size=(96, 80))
    args = ['--vae', 'MODEL', '--steps', '2', '--restarts', '1', '--edge', '64']
    assert cli.main(['--json', 'riposte', str(root), '--input', str(source), *args]) == 0
    assert json.loads(capsys.readouterr().out)['source_mode'] == 'snapshot' and source.exists()
    assert cli.main(['--json', 'sort-riposte', str(root), '--all', *args]) == 0
    combined = json.loads(capsys.readouterr().out)
    assert cli.main(['--json', 'sort-riposte', str(root), '--all', '--apply', '--plan-id', combined['plan_id'], *args]) == 0
    assert json.loads(capsys.readouterr().out)['sorting']['checkpoint'] == 'COMPLETE'
    assert not source.exists() and len(catalog(root)) == 1


def test_combined_invalid_selection_cannot_replace_sources(root, make_image, models):
    source = make_image(root / 'raw.png')
    before = snapshot(root)
    with pytest.raises(RiposteError):
        execute(Request('sort-riposte', root, values(image_ids=['a' * 32])))
    assert snapshot(root) == before and source.exists() and not models


def test_combined_protection_failure_retains_sort_and_can_retry(root, make_image, models, monkeypatch):
    source = make_image(root / 'raw.png', size=(96, 80))
    original = p.start_publication
    def fail(*args, **kwargs):
        raise RiposteError('WORKSPACE_LOCKED')
    monkeypatch.setattr(p, 'start_publication', fail)
    result = execute(reviewed_combined(root, values(all_images=True)))
    assert result['sorting']['checkpoint'] == 'COMPLETE' and result['protection'] == 'STOPPED'
    assert result['code'] == 'WORKSPACE_LOCKED' and not source.exists()
    monkeypatch.setattr(p, 'start_publication', original)
    retry = execute(Request('riposte', root, values(all_images=True)))
    assert retry['counts']['READY_FOR_REVIEW'] == 1


@pytest.mark.parametrize('kind,code', [('empty', 'NO_INPUT_IMAGES'), ('missing', 'INPUT_NOT_FOUND'), ('corrupt', 'INPUT_DECODE_FAILED')])
def test_invalid_inputs_are_readonly(root, kind, code):
    target = root if kind == 'empty' else root / 'input.png'
    if kind == 'corrupt':
        target.write_bytes(b'not an image')
    before = snapshot(root)
    with pytest.raises(RiposteError, match=code):
        input_files([target])
    assert snapshot(root) == before
