"""Exercise guided editing, real saved rules, sorting and undo in an isolated folder."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import time

from PIL import Image
import uvicorn
from riposte.server import create_app

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).parent
folder = Path(tempfile.mkdtemp(prefix='riposte-guided-live-'))
names = ['000-unknown.png', '001-street-hockey.png', '002-hockey.png']
names += [f'{i:03}-city-town.png' for i in range(3, 58)]
names += ['_float_/hockey.png', '__FLOAT__/city.png']
for index, name in enumerate(names):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new('RGB', (32, 24), (index, 90, 150)).save(path)
    os.utime(path, (1741305600, 1741305600))

def inventory():
    return {name: (hashlib.sha256((folder / name).read_bytes()).hexdigest(),
                   (folder / name).stat().st_mtime_ns) for name in names}

before = inventory()
listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen()
server = uvicorn.Server(uvicorn.Config(create_app(folder, 'guided-local-test'), log_level='error'))
thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True); thread.start()
for _ in range(100):
    if server.started: break
    time.sleep(.05)
assert server.started
try:
    run = subprocess.run(['node', str(ROOT / 'tests/category_sort_browser.cjs'),
                          'C:/Program Files/Google/Chrome/Application/chrome.exe', str(HERE)],
                         env={**os.environ, 'RIPOSTE_SORT_LIVE': f'http://127.0.0.1:{listener.getsockname()[1]}/#token=guided-local-test',
                              'RIPOSTE_SORT_PROBE': str(HERE / 'live_probe.js')},
                         capture_output=True, text=True, encoding='utf-8', timeout=110)
    print(run.stdout + run.stderr)
    assert run.returncode == 0
    assert inventory() == before, 'undo restores every original byte and mtime, including untouched float storage'
    # The shared operation lease is a persistent internal marker, also after undo.
    assert (folder / '.riposte-operation.lease').is_file()
    public = {p.relative_to(folder).as_posix() for p in folder.rglob('*') if p.is_file()
              and '.riposte' not in p.parts and p != folder / '.riposte-operation.lease'}
    assert public == set(names), public ^ set(names)
    (HERE / 'browser-live.json').write_text(json.dumps({'result': 'PASS', 'media_files': 58, 'float_files': 2,
        'restored_bytes_and_mtimes': True, 'no_unexpected_public_files': True, 'no_fetch_mocks': True,
        'scope': 'Native Chromium with authenticated API: empty rules, row creation, inline validation, review/save, stable rename, actual concurrent-rule conflict, per-file choices, exact preview, consented sort and undo, paging and keyboard.'}, indent=2) + '\n')
finally:
    server.should_exit = True; thread.join(10); listener.close()
