"""Check documented CLI syntax, links, archive preservation and unchanged application bytes.

Parsing does not execute documented writes or load models. Existing focused
runtime regressions are recorded separately. --capture retains pre-edit bytes.
"""
import argparse
from contextlib import redirect_stdout, redirect_stderr
import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile
from urllib.parse import unquote, urlsplit

from typer.main import get_command
from riposte.cli import app

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
CURRENT = ['README.md', 'docs/README.md', 'docs/CURRENT-CONTRACT.md', 'docs/CLI.md',
           'docs/THREAT-MODEL.md', 'docs/PUBLISHING.md', 'docs/PROJECT-STATUS.md',
           'docs/DEVELOPMENT-SPEC.md', 'docs/WAVE-04.md', 'docs/TERMINAL-DESIGN.spec.md']
WRAPPERS = {'docs/DEVELOPMENT-SPEC.md': '# Historical entry-point amendment / RIPOSTE 0.4',
            'docs/WAVE-04.md': '## Completed development',
            'docs/TERMINAL-DESIGN.spec.md': '## Mandate'}
ARCHIVES = ['docs/HISTORY-v02-README.md', 'docs/ENGINE-v02.md', 'docs/ENGINE-v03.md',
            'docs/WAVE-02-PLAN.md', 'docs/WAVE-03-HANDOFF.md', 'docs/REVISION-v05.md',
            'docs/PATCH-v05-MERGE.md', 'docs/VALIDATION.md', 'docs/01EXPANSION.md', 'docs/UI-DESIGN.md']

FOCUSED_COMMAND = '.venv/Scripts/python.exe -m pytest -q tests/test_workflows.py tests/test_sort_recovery.py tests/test_video_sort.py tests/test_float_sort.py tests/test_category_sort.py tests/test_category_rules.py tests/test_sort_preview_binding.py tests/test_workspace_lease.py tests/test_sanitize.py tests/test_v03_publication.py tests/test_publication_review_snapshots.py tests/test_duplicates.py --junitxml=evidence/documentation-contracts/focused.xml'

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def capture():
    assert not (HERE / 'before.zip').exists(), 'never replace the baseline'
    paths = sorted({*ROOT.glob('*.md'), *(ROOT / 'docs').rglob('*.md'), ROOT / 'MANIFEST.in', ROOT / 'typing/pacer_inventory.py'})
    with zipfile.ZipFile(HERE / 'before.zip', 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for p in paths: archive.write(p, p.relative_to(ROOT).as_posix())
    (HERE / 'source-before.json').write_bytes((ROOT / 'typing/evidence/source-reviewed-recovery-guidance.json').read_bytes())

def examples(path):
    code = False
    pending = ''
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
        if line.startswith('```'): code = not code; continue
        if not code: continue
        if pending or line == 'riposte' or line.startswith('riposte '):
            pending += line.strip()
            if pending.endswith('`') or pending.endswith('\\'):
                pending = pending[:-1] + ' '; continue
            yield number, shlex.split(pending, comments=True)
            pending = ''

def anchors(path):
    values = set()
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.startswith('#'):
            title = re.sub(r'^#+\s+', '', line).strip().lower()
            values.add(re.sub(r'[^\w\- ]', '', title).replace(' ', '-'))
    return values

def verify():
    issues = []; commands = []; links = 0; preserved = []
    group = get_command(app)
    for name in CURRENT:
        path = ROOT / name
        if not path.exists(): issues.append('Missing current document: ' + name); continue
        for line, argv in examples(path):
            try:
                with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()), group.make_context('riposte', argv[1:]) as ctx:
                    rest = [*ctx._protected_args, *ctx.args]
                    if rest:
                        cmd_name, command, tail = group.resolve_command(ctx, rest)
                        with command.make_context(cmd_name, tail, parent=ctx): pass
                commands.append({'document': name, 'line': line, 'argv': argv, 'result': 'PARSED'})
            except Exception as exc:
                if type(exc).__name__ == 'Exit' and getattr(exc, 'exit_code', None) == 0 and set(argv) & {'--help', '--version'}:
                    commands.append({'document': name, 'line': line, 'argv': argv, 'result': 'HELP_OR_VERSION'})
                else:
                    issues.append(f'{name}:{line}: {type(exc).__name__}: {exc}')
        for target in re.findall(r'\[[^\]\n]*\]\(([^)\n]+)\)', path.read_text(encoding='utf-8')):
            target = target.split(' "', 1)[0].strip('<>')
            parts = urlsplit(target)
            if parts.scheme or parts.netloc: continue
            linked = (path.parent / unquote(parts.path)).resolve() if parts.path else path
            links += 1
            if not linked.exists(): issues.append(f'{name}: missing link {target}')
            elif parts.fragment and linked.suffix == '.md' and unquote(parts.fragment) not in anchors(linked):
                issues.append(f'{name}: missing heading {target}')
    inventory = set(re.findall(r'^\| `([a-z][a-z-]*)\b', (ROOT / 'docs/CLI.md').read_text(encoding='utf-8'), re.M))
    if inventory != set(group.commands):
        issues.append('CLI inventory differs: missing=' + ','.join(sorted(set(group.commands)-inventory)) + '; obsolete=' + ','.join(sorted(inventory-set(group.commands))))
    with zipfile.ZipFile(HERE / 'before.zip') as baseline:
        for name in ARCHIVES:
            if baseline.read(name) != (ROOT / name).read_bytes(): issues.append('Archival file changed: ' + name)
            else: preserved.append(name)
        for name, marker in WRAPPERS.items():
            before = baseline.read(name); after = (ROOT / name).read_bytes(); needle = marker.encode()
            if before[before.index(needle):] != after[after.index(needle):]: issues.append('Historical payload changed: ' + name)
            else: preserved.append(name + ' from ' + marker)
    source = json.loads((HERE / 'source-before.json').read_text())
    for name, sha in source.items():
        if digest(ROOT / name) != sha: issues.append('Application changed: ' + name)
    threat = (ROOT / 'docs/THREAT-MODEL.md').read_text(encoding='utf-8')
    for stale in ('They are never intentionally copied to a persistent application backup', 'There is no contaminated-original rollback copy', 'hashes are calculated only after cleansing'):
        if stale in threat: issues.append('Current threat-model contradiction: ' + stale)
    if 'before manual removal' in (ROOT / 'docs/PUBLISHING.md').read_text(): issues.append('Current publishing guide recommends manual lock removal')
    if '2                         choose Image library' in (ROOT / 'docs/CLI.md').read_text(): issues.append('Linear example selects the wrong home action')
    report = {'result': 'FAIL' if issues else 'PASS', 'issues': issues, 'parsed_examples': commands,
              'command_inventory': sorted(group.commands), 'local_links_checked': links,
              'preserved_records': preserved, 'unchanged_application_files': len(source),
              'scope': 'Shipping Typer parser and local documentation links; examples are not executed as write/model operations.'}
    (HERE / 'documentation.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k not in {'parsed_examples', 'preserved_records'}}, indent=2))
    return not issues

def manifest():
    spec = importlib.util.spec_from_file_location('manifest_scope', ROOT / 'evidence/milestone-reconciliation-2026-09-18/verify.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    previous.INPUTS += ('docs/PCUC.md', 'docs/DUPLICATES.md', 'docs/research/sorting/RIPOSTE-REVIEW.md',
                        'docs/README.md', 'docs/CURRENT-CONTRACT.md', 'docs/PUBLISHING.md', 'docs/TERMINAL-DESIGN.spec.md')
    result = previous.manifest()
    result['generator'] = 'evidence/documentation-contracts/verify.py --manifest'
    result['milestone'] = 'PACER_RESUMED_RELEASE_PENDING'
    return result

def packages():
    assert verify(), 'documentation check failed'
    assert read(ROOT / 'RELEASE-MANIFEST.json') == manifest(), 'development manifest drift'
    source = read(HERE / 'source-before.json')
    actual = {p.relative_to(ROOT).as_posix() for p in (ROOT / 'src/riposte').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    assert actual == set(source), 'application file set changed'
    contracts = read(ROOT / 'typing/evidence/verification.json')
    assert len(contracts['results']) == 7 and all(contracts['results'].values())
    assert contracts['source_files'] == len(source) == 76
    suites = ET.parse(HERE / 'focused.xml').getroot().findall('testsuite')
    counts = {key: sum(int(s.attrib[key]) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    assert counts['tests'] > 0 and counts['failures'] == counts['errors'] == 0
    counts['passed'] = counts['tests'] - counts['skipped']
    modules = sorted({c.get('classname') for s in suites for c in s.findall('testcase')})
    expected = {'tests.' + Path(p).stem for p in shlex.split(FOCUSED_COMMAND) if p.startswith('tests/')}
    assert set(modules) == expected, 'missing expected regression module'
    dist = ROOT / '.tmp/documentation-contracts/dist'
    with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel, tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
        prefix = sdist.getnames()[0].split('/')[0]
        for name, sha in source.items():
            assert hashlib.sha256(wheel.read(name.removeprefix('src/'))).hexdigest() == sha, name
            assert hashlib.sha256(sdist.extractfile(prefix + '/' + name).read()).hexdigest() == sha, name
        for name in CURRENT:
            assert sdist.extractfile(prefix + '/' + name).read() == (ROOT / name).read_bytes(), name
    result = {'result': 'PASS', 'application_files_unchanged': len(source), 'focused': counts,
              'executed_modules': modules, 'contracts': contracts['results'],
              'package_documentation': CURRENT, 'packages_match': True,
              'documentation': read(HERE / 'documentation.json'),
              'strict_source_typing': 'Historical PAC-038 FAIL: 825 diagnostics; application bytes unchanged. Not rerun in documentation-only PAC-039.',
              'limits': ['Existing Windows dependencies and synthetic media; no new native UI, human, efficacy, clean-install or cross-platform qualification.',
                         'CLI examples parsed, not executed as mutations; archive bytes verified independently.',
                         'Earlier full-suite/native/model evidence retains its original scope and is not counted as executed here.']}
    (HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

def acceptance(pacer_source):
    sys.path.insert(0, str(pacer_source))
    from pacer_mcp.service import Service
    current = packages()
    assert read(ROOT / 'typing/evidence/pacer-inventory.json')['result'] == 'PASS'
    csv.field_size_limit(100000000)
    with (ROOT / 'organism.PACER.csv').open(encoding='utf-8-sig', newline='') as f: requirements = list(csv.DictReader(f))
    with (ROOT / 'overlord.PACER.csv').open(encoding='utf-8-sig', newline='') as f: assets = list(csv.DictReader(f))
    next_id = max(int(r['ID'].split('-')[1]) for r in assets) + 1
    service = Service(ROOT)
    operations, summaries = [], []
    for row in sorted(requirements, key=lambda r: r['ID']):
        observed = service.evaluate(row['ID'])
        if observed['freshness'] == 'CURRENT': continue
        candidates = [ROOT / 'evidence' / stage / (row['ID'] + suffix) for stage in ('recovery-guidance', 'guided-category-editing', 'pacer-resumption') for suffix in ('-final.json', '.json')]
        previous_path = next((p for p in candidates if p.exists()), None)
        previous = read(previous_path) if previous_path else None
        changed = sorted(p for p in observed['sources'] if previous is None or previous['sources'].get(p) != observed['sources'][p])
        if previous is not None:
            assert previous['meaning'] == observed['meaning'], 'requirement meaning changed: ' + row['ID']
            generated_package_metadata = {'src/riposte_studio.egg-info/PKG-INFO', 'src/riposte_studio.egg-info/SOURCES.txt'}
            assert all(p in generated_package_metadata or not p.startswith(('src/', 'tests/', 'typing/stubs/')) for p in changed), (row['ID'], changed)
        else:
            assert row['ID'] == 'OGM-026', 'missing historical review: ' + row['ID']
        specific = {
            'OGM-001': 'Inventory admits the current documentation/index/evidence owners; seven external stages pass against the unchanged 76-file application and 536 declared signatures. Inventory scope remains explicit.',
            'OGM-002': 'The source audit is not rerun or reclassified. PAC-038 retains 825 strict diagnostics in 36 of 66 files; current application bytes match that evidence. External tooling checks run separately.',
            'OGM-010': 'Fresh offline wheel and sdist match every application file; all ten current-entry documents match their sdist bytes. This does not qualify a clean installation.',
            'OGM-018': 'Current focused tests exercise optional category routing, original-title provenance, private exact recovery, float exclusions and frozen preview/consent behavior. Docs now reflect those boundaries.',
            'OGM-025': 'Runtime guidance catalog/consumers and their prior source-bound checks are unchanged. Current guides remove manual lock deletion and explain matching-marker recovery consistent with the executed lease regressions.',
            'OGM-026': 'Current entry guides distinguish PNG metadata from private original/title state, raw videos and explicit report exports. Exact supersession links replace obsolete deck/privacy contracts. All documented fenced commands parse against shipping Typer; inventory equals all 43 commands. Ten full archives and three historical bodies remain byte-identical. Current links resolve and wheel/sdist match source.',
        }
        review = ('PAC-039 documentation-only delta review. Every one of the 76 application files matches the preceding reviewed snapshot. Source/stub/launcher/runtime-test behavior is unchanged; changed direct inputs are enumerated below. Generated egg-info PKG-INFO and SOURCES.txt reflect the README and documentation inclusion change. Prior requirement-specific execution remains historical evidence with its original limitations. Fresh focused privacy/recovery regressions, seven external stages, parser/link/archive checks and package equality support the documentation change, not a new whole-product/platform/model qualification. ' + specific.get(row['ID'], 'No implementation change in this requirement; its earlier source-bound review remains applicable after documentation correction and dependency refresh.'))
        report = {'requirement': row['ID'], 'meaning': observed['meaning'], 'sources': observed['sources'], 'result': 'PASS',
                  'command': ['.venv/Scripts/python.exe evidence/documentation-contracts/verify.py --packages', FOCUSED_COMMAND,
                              'uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py'],
                  'review': review, 'changed_sources_since_previous_acceptance': changed,
                  'previous_review_artifact': previous_path.relative_to(ROOT).as_posix() if previous_path else None,
                  'previous_review_sha256': digest(previous_path) if previous_path else None,
                  'previous_scoped_review': previous.get('review') if previous else None,
                  'executed_modules': current['executed_modules'], 'scope_limits': current['limits']}
        path = 'evidence/documentation-contracts/' + row['ID'] + '.json'
        assert not (ROOT / path).exists(), 'never overwrite accepted evidence'
        (ROOT / path).write_text(json.dumps(report, indent=2) + '\n')
        artifact = f'OVR-{next_id:03d}'; next_id += 1
        operations.append({'op': 'add', 'register': 'overlord', 'row': {'ID': artifact, 'AssetType': 'FILE', 'Path': path, 'Purpose': 'PAC-039 documentation-delta acceptance for ' + row['ID'], 'PACRefs': 'PAC-039', 'Tags': '#acceptance #documentation-contracts'}})
        operations.append({'op': 'verify', 'id': row['ID'], 'artifact': artifact, 'evidence': 'PAC-039 source-bound documentation review and scoped execution: ' + path})
        summaries.append({'id': row['ID'], 'changed_sources': changed, 'review': review})
    (HERE / 'acceptance-operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    (HERE / 'acceptance-review.json').write_text(json.dumps(summaries, indent=2) + '\n')
    return {'requirements': len(summaries), 'operations': len(operations)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', action='store_true')
    parser.add_argument('--manifest', action='store_true')
    parser.add_argument('--packages', action='store_true')
    parser.add_argument('--pacer-source', type=Path)
    args = parser.parse_args()
    if args.capture: capture()
    elif args.manifest: (ROOT / 'RELEASE-MANIFEST.json').write_text(json.dumps(manifest(), indent=2) + '\n')
    elif args.pacer_source: print(json.dumps(acceptance(args.pacer_source), indent=2))
    elif args.packages: print(json.dumps(packages(), indent=2))
    else: raise SystemExit(0 if verify() else 1)
