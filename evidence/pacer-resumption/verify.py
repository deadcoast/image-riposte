"""Check the declared development snapshot and retained PAC-035 execution evidence.

This is not a release/clean-install/model qualification. Historical evidence is
read without invoking verifiers whose source snapshots belong to earlier stages.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile
import tomllib
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest():
    spec = importlib.util.spec_from_file_location('historical_manifest_scope', ROOT / 'evidence/milestone-reconciliation-2026-09-18/verify.py')
    basis = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(basis)
    basis.INPUTS += ('docs/PCUC.md', 'docs/DUPLICATES.md', 'docs/research/sorting/RIPOSTE-REVIEW.md')
    result = basis.manifest()
    result['generator'] = 'evidence/pacer-resumption/verify.py --manifest'
    result['milestone'] = 'PACER_RESUMED_RELEASE_PENDING'
    return result


def counts(name):
    suites = ET.parse(HERE / name).getroot().findall('testsuite')
    result = {k: sum(int(s.attrib[k]) for s in suites) for k in ('tests', 'failures', 'errors', 'skipped')}
    result['passed'] = result['tests'] - result['failures'] - result['errors'] - result['skipped']
    return result


def verify(packages=False):
    assert read(ROOT / 'RELEASE-MANIFEST.json') == manifest(), 'development manifest drift'
    sources = read(ROOT / 'typing/evidence/source-reviewed-browser-jobs.json')
    assert all(digest(ROOT / p) == sha for p, sha in sources.items())
    contracts = read(ROOT / 'typing/evidence/verification.json')
    assert len(contracts['results']) == 7 and all(contracts['results'].values())
    assert contracts['source_files'] == len(sources) == 73
    assert 'Found 823 errors in 36 files (checked 65 source files)' in (HERE / 'raw-source.txt').read_text(encoding='utf-8-sig')
    assert counts('suite.xml') == {'tests':1508, 'failures':0, 'errors':0, 'skipped':9, 'passed':1499}
    assert counts('native.xml')['passed'] == 3 and counts('native.xml')['failures'] == 0
    assert read(HERE / 'browser-live.json')['result'] == 'PASS'
    assert '10 failed' in (HERE / 'scans-before.txt').read_text(encoding='utf-8-sig')
    assert '72 passed' in (HERE / 'scans-expanded.txt').read_text(encoding='utf-8-sig')
    versions = tomllib.loads((ROOT / 'pyproject.toml').read_text())['project']['version']
    assert versions == '0.5.0'
    assert next(p['version'] for p in tomllib.loads((ROOT / 'uv.lock').read_text())['package'] if p['name']=='riposte-studio') == versions
    from riposte import __version__
    assert __version__ == versions
    if packages:
        dist = ROOT / '.tmp/pacer-resumption/dist'
        with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel, tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
            prefix = sdist.getnames()[0].split('/')[0]
            for name, sha in sources.items():
                assert hashlib.sha256(wheel.read(name.removeprefix('src/'))).hexdigest() == sha, name
                assert hashlib.sha256(sdist.extractfile(prefix+'/'+name).read()).hexdigest() == sha, name
            for name in ('README.md', 'docs/DUPLICATES.md', 'docs/UX-CONTRACT.md'):
                assert sdist.extractfile(prefix+'/'+name).read() == (ROOT/name).read_bytes(), name
    return {'result':'PASS', 'version':versions, 'source_files':len(sources), 'suite':counts('suite.xml'),
            'native_browser':counts('native.xml'), 'external_contracts':contracts['results'],
            'source_typing':'FAIL: 823 diagnostics; strict configuration unchanged',
            'packages_match':packages, 'live_browser':read(HERE/'browser-live.json'),
            'limits':['Full Python suite predates the final version-label-only HTML/JS edit; native browser and live-server checks cover that edit.',
                      'Existing Windows environment; no clean installation or minimum-Python/platform matrix.',
                      'Synthetic files and CPU/stub/tiny-random model checks do not establish independent human acceptance, classification accuracy or model efficacy.']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', action='store_true')
    parser.add_argument('--packages', action='store_true')
    args = parser.parse_args()
    if args.manifest:
        (ROOT/'RELEASE-MANIFEST.json').write_text(json.dumps(manifest(), indent=2)+'\n')
    else:
        result = verify(args.packages)
        (HERE/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
        print(json.dumps(result, indent=2))
