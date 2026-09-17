"""Index retained execution evidence; does not execute or invent test results."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    result_path = OUT / 'windows-py313.json'
    text = result_path.read_text(encoding='utf-8')
    if not text.startswith('{'):
        (OUT / 'windows-py313-console.txt').write_text(text, encoding='utf-8')
        result_path.write_text(text[text.index('{'):], encoding='utf-8')
    suites = {}
    for path in sorted(OUT.glob('*.xml')):
        suite = ET.parse(path).getroot().find('testsuite')
        counts = {k: int(suite.attrib[k]) for k in ('tests', 'failures', 'errors', 'skipped')}
        counts['passed'] = counts['tests'] - counts['failures'] - counts['errors'] - counts['skipped']
        suites[path.stem] = counts
    application = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / 'src').rglob('*'))
                   if p.is_file() and '__pycache__' not in p.parts and '.egg-info' not in str(p)}
    tests = {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted((ROOT / 'tests').glob('*.py'))}
    uv = ['uv', 'run', '--frozen', '--no-sync', '--cache-dir', 'typing/.cache/uv', 'python']
    typing = ['uv', 'run', '--project', 'typing', '--frozen', '--cache-dir', 'typing/.cache/uv', 'python']
    commands = [
        {'command': ['uv', 'sync', '--locked', '--extra', 'lab', '--extra', 'test', '--cache-dir', 'typing/.cache/uv'],
         'exit_code': 0, 'scope': 'Installed locked extras in existing application environment; lockfile unchanged'},
        {'command': uv + ['-m', 'pytest', 'tests', '-q', '-ra', '--basetemp', 'typing/.cache/development-repairs/full-final', '-o',
                         'cache_dir=typing/.cache/development-repairs/pytest-cache', '--junitxml=evidence/development-repairs/full-final.xml'],
         'exit_code': 0, 'output': 'full-final.txt'},
        {'command': uv + ['-m', 'pytest', 'tests/test_v02_generation.py', '-q', '--basetemp', 'typing/.cache/development-repairs/generation-version', '-o',
                         'cache_dir=typing/.cache/development-repairs/pytest-cache', '--junitxml=evidence/development-repairs/generation-version.xml'],
         'exit_code': 0, 'output': 'generation-version.txt', 'scope': 'New version assertion added after full run; source unchanged'},
        {'command': typing + ['typing/check.py'], 'exit_code': 0, 'output': 'typing-check.txt'},
        {'command': typing + ['typing/check.py', '--source'], 'exit_code': 1, 'output': 'raw-source.txt', 'expected_failure': True},
        {'command': uv + ['evidence/development-repairs/probe_without_torch.py'], 'exit_code': 0, 'output': 'no-torch.txt'},
        {'command': typing + ['evidence/development-repairs/probe_windows_identity.py'], 'exit_code': 0, 'output': 'windows-py313.json'},
        {'command': typing + ['typing/pacer_inventory.py'], 'exit_code': 0, 'output': 'inventory-final.txt',
         'scope': 'File/export/dependency reconciliation only; PAC-005 symbol completeness remains open'},
    ]
    report = {
        'authorization': 'Implement the listed repairs, including source and test changes',
        'scope': 'Audited defects, source-derived contract compatibility and synthetic regression execution',
        'base_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'python': sys.version, 'platform': platform.platform(),
        'versions': {name: importlib.metadata.version(name) for name in ('torch', 'diffusers', 'transformers', 'pytest', 'fastapi', 'Pillow')},
        'application': application, 'tests_at_report_time': tests,
        'lockfiles': {name: sha(ROOT / name) for name in ('pyproject.toml', 'uv.lock', 'typing/pyproject.toml', 'typing/uv.lock')},
        'commands': commands, 'suites': suites,
        'raw_source_mypy': {'exit_code': 1, 'diagnostics': 980, 'files_with_errors': 36, 'files_checked': 41},
        'intermediate_failures': {
            'first': 'Unfixed browser/publication/request/job paths and first organizer implementation still missed restored-mtime mutation.',
            'second': 'Corrupt-PNG fixture expected NO_APPROVED but workspace audit correctly blocked first; fixture corrected to a valid changed PNG.',
            'model-before': '14 numerical regressions failed before model/optimizer repair.',
            'full': '758 passes; two new focus tests lacked selected image setup; one additional Windows symlink-privilege assumption.',
        },
        'unverified': ['pretrained effectiveness', 'artist visual acceptance', 'native console lifecycle', 'live TCP/browser integration',
                       'GPU behavior', 'fresh distribution equality', 'clean-machine bootstrap', 'Python 3.11 compatibility'],
        'deferred_governance': ['PAC-005 symbol coverage', 'PAC-006 selective-patch closure', 'PAC-015 model/native qualification'],
        'retained_files': {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(OUT.rglob('*')) if p.is_file()
                           and p.name not in ('report.json', 'OGM-004-acceptance.json', 'pacer-final.json') and '__pycache__' not in p.parts},
    }
    (OUT / 'report.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'suites': suites, 'application_files': len(application)}))


if __name__ == '__main__':
    main()
