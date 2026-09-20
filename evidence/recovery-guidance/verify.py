"""Verify retained PAC-038 evidence and prepare scoped guarded acceptance reports."""
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
    result['generator'] = 'evidence/recovery-guidance/verify.py --manifest'
    return result

def counts(name):
    suites = ET.parse(HERE / name).getroot().findall('testsuite')
    result = {key: sum(int(s.attrib[key]) for s in suites) for key in ('tests', 'failures', 'errors', 'skipped')}
    result['passed'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    return result

def verify():
    assert read(ROOT / 'RELEASE-MANIFEST.json') == manifest(), 'development manifest drift'
    source = read(ROOT / 'typing/evidence/source-reviewed-recovery-guidance.json')
    assert all(digest(ROOT / p) == sha for p, sha in source.items())
    before = read(HERE / 'source-before.json')
    changed = sorted(p for p in source.keys() | before.keys() if source.get(p) != before.get(p))
    review = read(HERE / 'contract-review.json')
    assert changed == review['owners'] and len(changed) == 17
    contracts = read(ROOT / 'typing/evidence/verification.json')
    assert len(contracts['results']) == 7 and all(contracts['results'].values())
    assert contracts['source_files'] == len(source) == 76
    assert counts('suite.xml') == {'tests': 1528, 'failures': 0, 'errors': 0, 'skipped': 9, 'passed': 1519}
    assert counts('native.xml') == {'tests': 3, 'failures': 0, 'errors': 0, 'skipped': 0, 'passed': 3}
    assert read(HERE / 'browser-live.json')['result'] == 'PASS'
    assert 'Found 825 errors in 36 files (checked 66 source files)' in (HERE / 'raw-source.txt').read_text(encoding='utf-8-sig')
    assert read(HERE / 'ui-static.json')['summary']['total'] == 82
    dist = ROOT / '.tmp/recovery-guidance/dist'
    with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel, tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
        prefix = sdist.getnames()[0].split('/')[0]
        for path, sha in source.items():
            assert hashlib.sha256(wheel.read(path.removeprefix('src/'))).hexdigest() == sha, path
            assert hashlib.sha256(sdist.extractfile(prefix + '/' + path).read()).hexdigest() == sha, path
        for path in ('README.md', 'docs/UX-CONTRACT.md', 'docs/DESIGN.md', 'docs/PROJECT-STATUS.md'):
            assert sdist.extractfile(prefix + '/' + path).read() == (ROOT / path).read_bytes(), path
    result = {'result': 'PASS', 'application_files': len(source), 'changed_application_files': changed,
              'suite': counts('suite.xml'), 'native': counts('native.xml'), 'contracts': contracts['results'],
              'live': read(HERE / 'browser-live.json'), 'packages_match': True,
              'strict_source_typing': 'FAIL: 825 diagnostics in 36 files; strict settings unchanged',
              'limits': ['Existing Windows environments, not clean installation or other hosts.',
                         'Synthetic media; no independent human or assistive-technology acceptance, classification accuracy or protection efficacy.',
                         'Generic UI static audit has 82 findings with separate dispositions; not a global UI pass.']}
    (HERE / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result

def prepare_acceptance(pacer_source):
    sys.path.insert(0, str(pacer_source))
    from pacer_mcp.service import Service
    verify()
    inventory = read(ROOT / 'typing/evidence/pacer-inventory.json')
    assert inventory['result'] == 'PASS', inventory['issues']
    decisions = read(ROOT / 'evidence/pacer-resumption/decisions.json')
    cases = list(ET.parse(HERE / 'suite.xml').getroot().iter('testcase'))
    csv.field_size_limit(max(csv.field_size_limit(), (ROOT / 'organism.PACER.csv').stat().st_size))
    with (ROOT / 'organism.PACER.csv').open(encoding='utf-8-sig', newline='') as f: requirements = list(csv.DictReader(f))
    with (ROOT / 'overlord.PACER.csv').open(encoding='utf-8-sig', newline='') as f: assets = list(csv.DictReader(f))
    next_id = max(int(r['ID'].split('-')[1]) for r in assets) + 1
    service = Service(ROOT)
    operations, summaries = [], []
    for row in requirements:
        observed = service.evaluate(row['ID'])
        if observed['freshness'] == 'CURRENT': continue
        candidates = [ROOT / 'evidence' / stage / (row['ID'] + '.json') for stage in ('guided-category-editing', 'pacer-resumption')]
        previous = next((read(p) for p in candidates if p.exists()), None)
        changed_sources = sorted(p for p in observed['sources'] if previous is None or previous['sources'].get(p) != observed['sources'][p])
        review = 'PAC-038 source review: error codes are sanitized at construction; job metadata adds only an allowlisted operation family. The other runtime changes are recovery presentation. Engine math, matching, source replacement, lease ownership and history integrity implementations are unchanged. Current relevant regressions pass. Historical platform/model/human evidence retains its original scope and is not claimed as newly executed.'
        specific = {
            'OGM-001': 'Expanded inventory and source-derived recovery declarations cover 76 files, 536 signatures and 63 leaf modules. Seven external stages pass; graph scope remains explicit.',
            'OGM-002': 'Strict source audit rerun: FAIL at 825 diagnostics in 36 files. Two new diagnostics are calls to existing untyped report helpers. External contracts pass separately; settings, ignores and dynamic declarations are unchanged.',
            'OGM-008': 'All publication review state/race regressions and native Chromium pixel-decode/consent checks pass with the shared recovery client loaded. Immediate request dispatch, current image receipts and explicit acknowledgements remain enforced.',
            'OGM-010': 'Fresh wheel and source distribution match all 76 reviewed application files, including the JSON catalog and both consumers. Current user guides match the sdist. Existing launcher source remains unchanged; this is not clean installation.',
            'OGM-018': 'Current API/controller and actual local browser workflow exercise saved-rule conflict, optional categories, exact-preview consent, sort and undo; float files stay unchanged. New informational guidance does not modify planner readiness or matching.',
            'OGM-023': 'Current job cancellation/completion/shutdown regressions pass. Metadata adds only an allowlisted operation family for error presentation; progress and single-job/commit/cancellation guards remain intact. Earlier scaling/cancellation recordings retain their historical scope.',
            'OGM-024': 'Native category editor tests and real-server workflow retain row validation, stable rename, protected reload and draft preservation after a real revision conflict. Current sort/undo restores 58 files; both float folders stay untouched.',
            'OGM-025': 'One packaged catalog drives terminal and browser guidance. All-code/all-family parity, unknown-code/private-text tests, direct API and worker sanitization, 72x24 scroll/no-retry tests, native persistent-modal/blocker guidance and actual rules-conflict/consent rejection pass. Category ambiguity and unknown titles remain informational. Packaged bytes match and no guidance deletes locks or changes operation safeguards.',
        }
        review += ' ' + specific.get(row['ID'], '')
        modules = decisions.get(row['ID'], {}).get('tests', ['test_category_sort_interfaces', 'test_category_rules', 'test_browser_scan_jobs'])
        modules = list(dict.fromkeys([*modules, 'test_recovery_guidance']))
        coverage = {}
        for module in modules:
            selected = [c for c in cases if c.get('classname') == 'tests.' + module]
            assert selected and not any(c.find('failure') is not None or c.find('error') is not None for c in selected), module
            coverage[module] = {'passed': sum(c.find('skipped') is None for c in selected), 'skipped': sum(c.find('skipped') is not None for c in selected)}
        report = {'requirement': row['ID'], 'meaning': observed['meaning'], 'sources': observed['sources'], 'result': 'PASS',
                  'command': ['.venv/Scripts/python.exe evidence/recovery-guidance/verify.py',
                              '.venv/Scripts/python.exe -m pytest -q -k "not browser_native and not native_browser and not browser_review_in_real_chromium" --junitxml=evidence/recovery-guidance/suite.xml',
                              '.venv/Scripts/python.exe -m pytest -q -k "browser_native or native_browser or browser_review_in_real_chromium" -o cache_dir=.tmp/recovery-guidance/native-cache --junitxml=evidence/recovery-guidance/native.xml',
                              '.venv/Scripts/python.exe evidence/recovery-guidance/live_browser.py',
                              'uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py'],
                  'review': review, 'executed_module_coverage': coverage,
                  'previous_review': decisions.get(row['ID'], {}).get('review', ''), 'scope_limits': read(HERE / 'verification.json')['limits']}
        path = 'evidence/recovery-guidance/' + row['ID'] + '.json'
        (ROOT / path).write_text(json.dumps(report, indent=2) + '\n')
        artifact = f'OVR-{next_id:03d}'; next_id += 1
        operations.append({'op': 'add', 'register': 'overlord', 'row': {'ID': artifact, 'AssetType': 'FILE', 'Path': path, 'Purpose': 'PAC-038 scoped acceptance for ' + row['ID'], 'PACRefs': 'PAC-038', 'Notes': 'Current scoped acceptance; previous evidence preserved', 'Tags': '#acceptance #recovery-guidance'}})
        operations.append({'op': 'verify', 'id': row['ID'], 'artifact': artifact, 'evidence': 'PAC-038 scoped review and executed regression evidence: ' + path})
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
