"""Verify the PAC-037 development snapshot; retain older evidence as historical."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent

def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def manifest():
    spec = importlib.util.spec_from_file_location('previous_scope', ROOT / 'evidence/pacer-resumption/verify.py')
    previous = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(previous)
    result = previous.manifest()
    result['generator'] = 'evidence/guided-category-editing/verify.py --manifest'
    return result

def counts(name):
    suites = ET.parse(HERE / name).getroot().findall('testsuite')
    result = {key: sum(int(s.attrib[key]) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    result['passed'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    return result

def verify():
    assert read(ROOT / 'RELEASE-MANIFEST.json') == manifest(), 'development manifest drift'
    source = read(ROOT / 'typing/evidence/source-reviewed-guided-categories.json')
    assert all(digest(ROOT / p) == sha for p, sha in source.items())
    before = read(HERE / 'source-before.json')
    changed = {p for p in source.keys() | before.keys() if source.get(p) != before.get(p)}
    assert changed == {'src/riposte/static/' + p for p in ('category-sort.js', 'index.html', 'style.css')}
    contracts = read(ROOT / 'typing/evidence/verification.json')
    assert len(contracts['results']) == 7 and all(contracts['results'].values())
    assert contracts['source_files'] == len(source) == 73
    assert counts('suite.xml') == {'tests': 1508, 'failures': 0, 'errors': 0, 'skipped': 9, 'passed': 1499}
    assert counts('native.xml') == {'tests': 3, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 3}
    assert read(HERE / 'browser-live.json')['result'] == 'PASS'
    assert 'Found 823 errors in 36 files (checked 65 source files)' in (HERE / 'raw-source.txt').read_text(encoding='utf-8-sig')
    dist = ROOT / '.tmp/guided-category-editing/dist'
    with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel, tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
        prefix = sdist.getnames()[0].split('/')[0]
        for path, sha in source.items():
            assert hashlib.sha256(wheel.read(path.removeprefix('src/'))).hexdigest() == sha, path
            assert hashlib.sha256(sdist.extractfile(prefix + '/' + path).read()).hexdigest() == sha, path
        for path in ('README.md', 'docs/UX-CONTRACT.md', 'docs/DESIGN.md', 'docs/PROJECT-STATUS.md'):
            assert sdist.extractfile(prefix + '/' + path).read() == (ROOT / path).read_bytes(), path
    result = {'result': 'PASS', 'application_files': len(source), 'changed_application_files': sorted(changed),
              'suite': counts('suite.xml'), 'native': counts('native.xml'), 'contracts': contracts['results'],
              'live': read(HERE / 'browser-live.json'), 'packages_match': True,
              'strict_source_typing': 'FAIL: 823 diagnostics in 36 files; unchanged Python source and strict settings',
              'limits': ['Existing Windows environments, not clean installation or other hosts.',
                         'Synthetic media; no independent human or assistive-technology acceptance, classification accuracy or protection efficacy.',
                         'Generic UI static audit has 81 findings, reviewed separately; not a global UI pass.']}
    (HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

def prepare_acceptance(pacer_source):
    sys.path.insert(0, str(pacer_source))
    from pacer_mcp.service import Service
    result = verify()
    inventory = read(ROOT / 'typing/evidence/pacer-inventory.json')
    assert inventory['result'] == 'PASS', inventory['issues']
    decisions = read(ROOT / 'evidence/pacer-resumption/decisions.json')
    cases = list(ET.parse(HERE / 'suite.xml').getroot().iter('testcase'))
    csv.field_size_limit(max(csv.field_size_limit(), (ROOT / 'organism.PACER.csv').stat().st_size))
    with (ROOT / 'organism.PACER.csv').open(encoding='utf-8-sig', newline='') as f:
        requirements = list(csv.DictReader(f))
    with (ROOT / 'overlord.PACER.csv').open(encoding='utf-8-sig', newline='') as f:
        assets = list(csv.DictReader(f))
    ids = {r['Path']: r['ID'] for r in assets if r['AssetType'] == 'FILE'}
    next_id = max(int(r['ID'].split('-')[1]) for r in assets) + 1
    service = Service(ROOT)
    operations, summaries = [], []
    for row in requirements:
        observed = service.evaluate(row['ID'])
        if observed['freshness'] == 'CURRENT': continue
        previous_path = ROOT / 'evidence/pacer-resumption' / (row['ID'] + '.json')
        previous = read(previous_path) if previous_path.exists() else None
        changed_sources = sorted(p for p in observed['sources'] if previous is None or previous['sources'].get(p) != observed['sources'][p])
        # No Python runtime or contract declaration changed; the delta is reviewed above.
        assert not any(p.startswith('src/') and p.endswith('.py') for p in changed_sources) if previous else True
        prior_review = decisions.get(row['ID'], {}).get('review', '')
        review = 'PAC-037 source delta reviewed: Python runtime and contract declarations unchanged; changed browser controls use existing requests, saved-rule revisions and exact-preview consent. Current full module regressions and all three native browser tests pass. Changed documentation describes bounded results. Earlier launcher, historical merge/identification and model evidence retain their original dates and qualification limits.'
        if row['ID'] == 'OGM-001':
            review = 'Expanded input inventory passes with six guided-editor evidence/snapshot owners admitted. Current external contracts pass all seven stages at 531 signatures, 62 leaf modules and 73 application files; source/symbol/stub graph remains complete at its declared scope.'
        elif row['ID'] == 'OGM-002':
            review = 'The strict source audit was rerun and still fails at 823 diagnostics in 36 files. Seven external contract stages pass separately. No ignore, exclude, Python-runtime change or diagnostic suppression was introduced.'
        elif row['ID'] == 'OGM-010':
            review = 'Fresh wheel/sdist application files match all 73 reviewed source files. Current README and design/UX/status docs match the source distribution; MANIFEST now includes the previously omitted status guide. Launcher source is unchanged and retains prior execution evidence; this is not clean installation.'
        if row['ID'] == 'OGM-024':
            review = 'Structured browser rows and per-file selectors demonstrated with native validation/focus/state tests and actual authenticated save, stable rename, concurrent-rule conflict, optional categories, exact preview, explicit apply, undo and float preservation. CLI/terminal syntax and all Python runtime signatures remain unchanged.'
        elif row['ID'] == 'OGM-023':
            review = 'Current deterministic cancellation/completion/shutdown regressions pass. The browser retains job IDs, phase/cancel controls and generation checks; guided editor tests reject stale review/preview replies. Prior 960-file live cancellation evidence remains historical; the current 58-file live workflow verifies real save/conflict/preview/apply/undo integration.'
        coverage = {}
        modules = decisions.get(row['ID'], {}).get('tests', ['test_category_sort_interfaces', 'test_category_rules', 'test_browser_scan_jobs'])
        for module in modules:
            selected = [c for c in cases if c.get('classname') == 'tests.' + module]
            assert selected and not any(c.find('failure') is not None or c.find('error') is not None for c in selected), module
            coverage[module] = {'passed': sum(c.find('skipped') is None for c in selected), 'skipped': sum(c.find('skipped') is not None for c in selected)}
        report = {'requirement': row['ID'], 'meaning': observed['meaning'], 'sources': observed['sources'], 'result': 'PASS',
                  'command': ['.venv/Scripts/python.exe evidence/guided-category-editing/verify.py',
                              '.venv/Scripts/python.exe -m pytest -q -k "not browser_native and not native_browser and not browser_review_in_real_chromium"',
                              '.venv/Scripts/python.exe -m pytest -q -k "browser_native or native_browser or browser_review_in_real_chromium"',
                              '.venv/Scripts/python.exe evidence/guided-category-editing/live_browser.py',
                              'uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py'],
                  'review': review, 'prior_scope_review': prior_review, 'changed_sources_since_acceptance': changed_sources, 'test_modules': coverage,
                  'previous_artifact': str(previous_path.relative_to(ROOT)) if previous else None,
                  'previous_artifact_sha256': digest(previous_path) if previous else None,
                  'verification': result}
        path = 'evidence/guided-category-editing/' + row['ID'] + '.json'
        (ROOT / path).write_text(json.dumps(report, indent=2) + '\n')
        artifact = ids.get(path)
        if not artifact:
            artifact = f'OVR-{next_id}'; next_id += 1
            operations.append({'op': 'add', 'register': 'overlord', 'row': {'ID': artifact, 'AssetType': 'FILE', 'Path': path,
                'Purpose': 'PAC-037 reviewed source-bound evidence for ' + row['ID'] + '; previous acceptance preserved', 'Tags': '#acceptance #guided-categories'}})
        operations.append({'op': 'verify', 'id': row['ID'], 'artifact': artifact, 'evidence': 'PAC-037 scoped review and executed regression evidence: ' + path})
        summaries.append({'id': row['ID'], 'changed_sources': changed_sources, 'review': review})
    (HERE / 'acceptance-operations.json').write_text(json.dumps(operations, indent=2) + '\n')
    (HERE / 'acceptance-review.json').write_text(json.dumps(summaries, indent=2) + '\n')
    return {'requirements': len(summaries), 'operations': len(operations)}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='store_true')
    parser.add_argument('--pacer-source', type=Path)
    args = parser.parse_args()
    if args.manifest:
        (ROOT / 'RELEASE-MANIFEST.json').write_text(json.dumps(manifest(), indent=2) + '\n')
    else:
        print(json.dumps(prepare_acceptance(args.pacer_source) if args.pacer_source else verify(), indent=2))
