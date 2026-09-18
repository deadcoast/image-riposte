"""Verify fresh package bytes and run read-only installed/launcher smoke checks."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
from zipfile import ZipFile

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
INSTALLED = ROOT / 'typing/.cache/menu-installed'
WHEEL = ROOT / 'dist/riposte_studio-0.5.0-py3-none-any.whl'
SDIST = ROOT / 'dist/riposte_studio-0.5.0.tar.gz'


def main():
    sources = {p.relative_to(ROOT / 'src').as_posix(): p.read_bytes()
               for p in (ROOT / 'src/riposte').rglob('*')
               if p.is_file() and '__pycache__' not in p.parts}
    with ZipFile(WHEEL) as archive, tarfile.open(SDIST) as source_archive:
        assert {n for n in archive.namelist() if n.startswith('riposte/')} == set(sources)
        for name, data in sources.items():
            assert archive.read(name) == data, name
            assert source_archive.extractfile('riposte_studio-0.5.0/src/' + name).read() == data, name
            assert (INSTALLED / name).read_bytes() == data, name
        assert 'riposte/terminal/paths.py' in sources
        for name in ['INSTALL.ps1','INSTALL.sh','START.ps1','START.sh','START.cmd','riposte.cmd','uv.lock']:
            assert source_archive.extractfile('riposte_studio-0.5.0/' + name).read() == (ROOT / name).read_bytes(), name
        entry = archive.read('riposte_studio-0.5.0.dist-info/entry_points.txt').decode()
        assert 'riposte = riposte.cli:main' in entry
    env = {**os.environ, 'PYTHONPATH': str(INSTALLED)}
    results = []
    with tempfile.TemporaryDirectory(prefix='riposte-install-smoke-') as directory:
        scratch = Path(directory).resolve()
        assert scratch.parent == Path(tempfile.gettempdir()).resolve()
        art = scratch / 'artwork'
        art.mkdir()
        source = art / 'source.png'
        Image.new('RGB', (96, 80), (160, 120, 100)).save(source)
        original = source.read_bytes()
        probe = subprocess.run([sys.executable, '-c', 'import riposte,json;from typer.main import get_command;from riposte.cli import app;print(json.dumps({"origin":riposte.__file__,"commands":sorted(get_command(app).commands)}))'], cwd=scratch, env=env, capture_output=True, text=True, timeout=30)
        assert probe.returncode == 0, probe.stderr
        installed = json.loads(probe.stdout)
        assert Path(installed['origin']).resolve().is_relative_to(INSTALLED.resolve())
        assert {'sort', 'riposte', 'sort-riposte', 'organize', 'publish', 'protect'} <= set(installed['commands'])
        for args, mode in [(['sort', str(art)], 'READ_ONLY'),
                           (['riposte', str(art), '--input', str(source), '--plan'], 'PUBLICATION_PLAN'),
                           (['sort-riposte', str(art), '--all'], 'SORT_RIPOSTE_PLAN')]:
            command = [sys.executable, '-m', 'riposte', '--json', *args]
            run = subprocess.run(command, cwd=scratch, env=env, capture_output=True, text=True, timeout=30)
            assert run.returncode == 0, run.stdout + run.stderr
            data = json.loads(run.stdout)
            assert data['mode'] == mode
            results.append({'workflow': args[0], 'mode': mode, 'exit_code': run.returncode})
        menu = subprocess.run([sys.executable, '-m', 'riposte', '--plain'], cwd=scratch, env=env, input='q\n', capture_output=True, text=True, timeout=30)
        assert menu.returncode == 0 and 'MAIN MENU' in menu.stdout
        assert 'value (/cancel)>' not in menu.stdout
        # The repository's actual launcher uses the existing editable environment.
        local_env = dict(os.environ)
        local_env.pop('PYTHONPATH', None)
        host = shutil.which('pwsh') or shutil.which('powershell')
        assert host is not None
        run = subprocess.run([host, '-NoProfile', '-File', str(ROOT / 'START.ps1'), '-Linear', '-NoAnimation'], cwd=scratch, env=local_env, input='q\n', capture_output=True, text=True, timeout=30)
        assert run.returncode == 0, run.stdout + run.stderr
        assert 'Sort + RIPOSTE' in run.stdout and 'MAIN MENU' in run.stdout
        (HERE / 'windows-launcher.txt').write_text(run.stdout + run.stderr, encoding='utf-8')
        wrapper = subprocess.run(['cmd.exe', '/c', str(ROOT / 'riposte.cmd'), '--help'], cwd=scratch, env=local_env, capture_output=True, text=True, timeout=30)
        assert wrapper.returncode == 0 and 'sort-riposte' in wrapper.stdout, wrapper.stdout + wrapper.stderr
        assert source.read_bytes() == original and list(art.iterdir()) == [source]
    report = {'result': 'PASS', 'source_files': len(sources), 'equal_bytes': 'checkout = sdist = wheel = isolated installation',
              'installed_origin': installed['origin'], 'commands': installed['commands'], 'previews': results,
              'windows_launcher': 'actual START.ps1 and existing environment; linear menu entered and exited',
              'windows_wrapper': 'actual riposte.cmd help; all new workflow commands visible',
              'images_changed': False,
              'wheel_sha256': hashlib.sha256(WHEEL.read_bytes()).hexdigest(),
              'sdist_sha256': hashlib.sha256(SDIST.read_bytes()).hexdigest(),
              'limits': ['Installed previews do not execute models', 'Native Windows terminal is checked separately; no GPU/model efficacy claim',
                         'Bash installer behavior is separately tested with installation/UI subprocess adapters']}
    (HERE / 'package.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
