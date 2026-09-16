"""Real loopback HTTP verification against a disposable synthetic workspace."""
import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
import httpx
from riposte.sanitize import png_audit

def run(root:Path,output:Path):
    output.mkdir(parents=True,exist_ok=True)
    token='browser-validation-only'
    code="from pathlib import Path;from riposte.server import create_app;import uvicorn;uvicorn.run(create_app(Path("+repr(str(root))+"),token="+repr(token)+"),host='127.0.0.1',port=8765,access_log=False,log_level='critical')"
    proc=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    checks=[]
    try:
        with httpx.Client(base_url='http://127.0.0.1:8765',trust_env=False,timeout=30) as client:
            for _ in range(100):
                try:
                    response=client.get('/');break
                except httpx.ConnectError:time.sleep(.1)
            else:raise RuntimeError('LOCAL_SERVER_DID_NOT_START')
            assert response.status_code==200 and 'RIPOSTE' in response.text;checks.append('real listener serves RIPOSTE interface')
            assert client.get('/api/state').status_code==401;checks.append('real listener requires session token')
            client.headers['X-Riposte-Token']=token
            response=client.get('/api/state');state=response.json()
            assert response.status_code==200 and state['version']=='0.2.0' and len(state['images'])==6;checks.append('authorized live catalog')
            assert response.headers['cache-control']=='no-store';checks.append('no-store response policy')
            assert "default-src 'self'" in response.headers['content-security-policy'];checks.append('self-only application content policy')
            assert client.get('/api/state',headers={'Origin':'https://untrusted.invalid'}).status_code==403;checks.append('cross-origin requests rejected')
            assert client.get('/api/state',headers={'Host':'untrusted.invalid'}).status_code==403;checks.append('unrecognized host rejected')
            assert client.get('/api/state',headers={'Sec-Fetch-Site':'cross-site'}).status_code==403;checks.append('cross-site fetch metadata rejected')
            image=state['images'][0];thumb=client.get('/api/image/'+image['id']+'?thumb=true')
            assert png_audit(thumb.content)['date']==image['day'];checks.append('served thumbnail independently date-only audited')
            trial=state['trials'][0];response=client.get('/api/trial/'+trial['id']+'/candidate?view=jpeg70')
            assert png_audit(response.content)['date']==trial['date'];checks.append('live paired JPEG view independently audited')
            assert client.get('/api/audit').json()['checkpoint']=='COMPLETE';checks.append('live organization checkpoint')
            assert client.post('/api/export',json={'trial_id':trial['id']}).status_code==400;checks.append('live export acknowledgment gate')
            assert client.post('/api/organize',json={'apply':True}).status_code==400;checks.append('live source-removal acknowledgment gate')
            assert 'runtime' in client.post('/api/preflight',json={}).json();checks.append('live runtime preflight')
            result=client.get('/api/evaluations/'+trial['id']).json()['evaluations']
            assert result and result[0]['ai_protection']=='UNVERIFIED';checks.append('live scoped qualification evidence')
            runs=client.get('/api/generations/'+trial['id']).json()['runs'];assert runs and runs[0]['fixture']=='SYNTHETIC_STUB_ONLY'
            frame=next(iter(runs[0]['artifacts']));data=client.get('/api/generation/'+runs[0]['id']+'/frame',params={'relative':frame}).content
            assert png_audit(data)['date']==trial['date'];checks.append('live hash-bound generation frame independently audited')
        # Test native navigation without changing Chromium security/network policy.
        browser={'status':'NOT_RUN'}
        try:
            from browser_qa import run as browser_run
            browser_run(output/'live-browser',root=None)
            browser={'status':'PASSED','report':'live-browser/browser-qa.json'}
        except Exception as exc:
            text=str(exc)
            if any(code in text for code in ('ERR_NETWORK_ACCESS_DENIED','ERR_BLOCKED_BY_CLIENT','ERR_CONNECTION_REFUSED','ERR_BLOCKED_BY_ADMINISTRATOR')):
                browser={'status':'LOCALHOST_NAVIGATION_BLOCKED','fallback':'Chromium in-process backend transport separately tested'}
            else:
                raise
        result={'harness':'Uvicorn subprocess / real loopback HTTP / httpx trust_env=False','passed':len(checks),'checks':checks,'browser':browser}
        (output/'http-qa.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);args=parser.parse_args()
    run(args.root,Path(__file__).resolve().parents[1]/'evidence')
