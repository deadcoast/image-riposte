"""Fresh distribution equality and installed exact-plan/undo smoke verification."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIST = ROOT / '.tmp/category-sort/dist'
INSTALLED = ROOT / '.tmp/category-sort/installed'


def main():
    sources = {p.relative_to(ROOT / 'src').as_posix(): p.read_bytes()
               for p in (ROOT / 'src/riposte').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    with ZipFile(DIST / 'riposte_studio-0.5.0-py3-none-any.whl') as wheel, tarfile.open(DIST / 'riposte_studio-0.5.0.tar.gz') as sdist:
        assert {n for n in wheel.namelist() if n.startswith('riposte/')} == set(sources)
        for name, data in sources.items():
            assert wheel.read(name) == data
            assert sdist.extractfile('riposte_studio-0.5.0/src/' + name).read() == data
            assert (INSTALLED / name).read_bytes() == data
        for name in ('docs/DESIGN.md', 'docs/UX-CONTRACT.md', 'docs/CLI.md', 'riposte.cmd'):
            assert sdist.extractfile('riposte_studio-0.5.0/' + name).read() == (ROOT / name).read_bytes()
    env = {**os.environ, 'PYTHONPATH': str(INSTALLED)}
    with tempfile.TemporaryDirectory(prefix='installed-sort-', dir=ROOT / '.tmp/category-sort') as directory:
        root = Path(directory)
        source = root / 'hockey-goalie.png'
        Image.new('RGB', (96, 80), (160, 120, 100)).save(source)
        original = source.read_bytes()
        probe = subprocess.run([sys.executable, '-c', 'import riposte; print(riposte.__file__)'],
                               cwd=root, env=env, capture_output=True, text=True, timeout=30)
        assert probe.returncode == 0 and Path(probe.stdout.strip()).is_relative_to(INSTALLED)

        def invoke(command, *options):
            result = subprocess.run([sys.executable, '-m', 'riposte', '--json', command, str(root), *options],
                                    cwd=root, env=env, capture_output=True, text=True, encoding='utf-8', timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            return json.loads(result.stdout)

        invoke('category-rules', '--category', 'Hockey=hockey;goalie', '--save', '--expected-revision', 'missing')
        preview = invoke('sort', '--categories', '--date-mode', 'modified')
        assert preview['ready'] and '/img/hockey/SML/' in preview['files'][0]['destination']
        wrapper = subprocess.run([str(ROOT / 'riposte.cmd'), '--json', 'sort', str(root), '--categories', '--date-mode', 'modified'],
                                 cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30)
        assert wrapper.returncode == 0 and json.loads(wrapper.stdout) == preview
        result = invoke('sort', '--categories', '--date-mode', 'modified', '--apply', '--plan-id', preview['plan_id'])
        assert result['checkpoint'] == 'COMPLETE' and not source.exists()
        assert invoke('audit')['checkpoint'] == 'COMPLETE'
        undo = invoke('undo-sort')
        assert undo['ready']
        assert invoke('undo-sort', '--apply', '--sort-id', undo['sort_id'])['checkpoint'] == 'COMPLETE'
        assert source.read_bytes() == original and not invoke('list')
        report = {'result': 'PASS', 'source_files': len(sources), 'installed_origin': probe.stdout.strip(),
                  'scope': 'Checkout/sdist/wheel/isolated target byte equality; installed CLI saved rules, exact preview, apply, audit and byte-exact undo; actual Windows wrapper preview.'}
        (HERE / 'package.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print('PASS package bytes, installed category sorting/recovery and Windows wrapper')


if __name__ == '__main__':
    main()
