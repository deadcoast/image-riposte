"""Real local server, engine and Chromium with synthetic artwork; no user media."""
import hashlib
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time

from PIL import ImageEnhance
import uvicorn

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tests'))
from test_duplicates import artwork
from riposte.server import create_app

folder=Path(tempfile.mkdtemp(prefix='riposte-duplicate-live-'))
original=artwork();original.save(folder/'original.png')
(folder/'exact-copy.png').write_bytes((folder/'original.png').read_bytes())
original.save(folder/'reencoded.jpg',quality=85)
ImageEnhance.Brightness(original).enhance(1.1).save(folder/'brighter.png')
original.crop((80,60,240,180)).save(folder/'cropped.png')
artwork(99).save(folder/'unrelated.png')
def inventory():
    return {p.name:(p.stat().st_mtime_ns,hashlib.sha256(p.read_bytes()).hexdigest()) for p in folder.iterdir()}
before=inventory()
listener=socket.socket();listener.bind(('127.0.0.1',0));listener.listen()
server=uvicorn.Server(uvicorn.Config(create_app(folder,'duplicate-live-test'),log_level='error'))
thread=threading.Thread(target=server.run,kwargs={'sockets':[listener]},daemon=True);thread.start()
for _ in range(100):
    if server.started:break
    time.sleep(.05)
assert server.started
try:
    run=subprocess.run(['node',str(ROOT/'tests/duplicate_browser.cjs'),
                        'C:/Program Files/Google/Chrome/Application/chrome.exe',str(Path(__file__).parent)],
                       env={**os.environ,'RIPOSTE_DUPLICATE_LIVE':f'http://127.0.0.1:{listener.getsockname()[1]}/#token=duplicate-live-test'},
                       capture_output=True,text=True,encoding='utf-8',timeout=60)
    print(run.stdout+run.stderr)
    assert run.returncode==0
    assert inventory()==before
    result={'result':'PASS','scope':'Actual authenticated server, shared engine, native browser, six synthetic artwork files',
            'unchanged':True,'fixture':str(folder),'no_fetch_mocks':True}
    (Path(__file__).parent/'browser-live.json').write_text(json.dumps(result,indent=2)+'\n')
finally:
    server.should_exit=True;thread.join(10);listener.close()
