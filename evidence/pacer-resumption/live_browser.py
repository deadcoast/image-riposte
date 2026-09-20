"""Run the real local scanner and browser on an isolated synthetic folder."""
import hashlib
import io
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
folder = Path(tempfile.mkdtemp(prefix='riposte-scan-live-'))
buffer = io.BytesIO()
Image.new('RGB', (512, 384), (30, 90, 150)).save(buffer, format='PNG')
for index in range(960):
    (folder / f'hockey-player-{index:04}.png').write_bytes(buffer.getvalue())
def inventory():
    return {p.name: (p.stat().st_mtime_ns, hashlib.sha256(p.read_bytes()).hexdigest()) for p in folder.iterdir()}
before = inventory()
listener = socket.socket(); listener.bind(('127.0.0.1', 0)); listener.listen()
server = uvicorn.Server(uvicorn.Config(create_app(folder, 'scan-live-test'), log_level='error'))
thread = threading.Thread(target=server.run, kwargs={'sockets': [listener]}, daemon=True); thread.start()
for _ in range(100):
    if server.started: break
    time.sleep(.05)
assert server.started
try:
    run = subprocess.run(['node', str(ROOT / 'tests/category_sort_browser.cjs'),
                          'C:/Program Files/Google/Chrome/Application/chrome.exe', str(HERE)],
                         env={**os.environ, 'RIPOSTE_SORT_LIVE': f'http://127.0.0.1:{listener.getsockname()[1]}/#token=scan-live-test'},
                         capture_output=True, text=True, encoding='utf-8', timeout=110)
    print(run.stdout + run.stderr)
    assert run.returncode == 0
    assert inventory() == before
    (HERE / 'browser-live.json').write_text(json.dumps({'result': 'PASS', 'files': len(before),
        'unchanged_bytes_and_mtimes': True, 'no_fetch_mocks': True,
        'scope': 'Authenticated API and actual sorter scans: cancellation, discovery, rule review, exact preview, consent, keyboard and narrow layout.'}, indent=2) + '\n')
finally:
    server.should_exit = True; thread.join(10); listener.close()
