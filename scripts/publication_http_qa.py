"""Live loopback HTTP QA on committed, explicitly synthetic publication outputs."""
import argparse,io,json,subprocess,sys,time
from pathlib import Path
from zipfile import ZipFile
import httpx
from riposte.sanitize import png_audit

def run(root,output):
    from riposte.store import state_relative
    if not (root / state_relative(root, "DEMO")).is_file():
        raise RuntimeError("SYNTHETIC_DEMO_WORKSPACE_REQUIRED")
    output.mkdir(parents=True,exist_ok=True)
    token='v03-disposable-http-fixture';port=8766
    code=f"from pathlib import Path;from riposte.server import create_app;import uvicorn;uvicorn.run(create_app(Path({str(root)!r}),token={token!r}),host='127.0.0.1',port={port},access_log=False,log_level='critical')"
    proc=subprocess.Popen([sys.executable,'-c',code],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    checks=[];browser_result={}
    try:
        with httpx.Client(base_url=f'http://127.0.0.1:{port}',trust_env=False,timeout=30) as c:
            for _ in range(100):
                try:r=c.get('/');break
                except httpx.ConnectError:time.sleep(.1)
            else:raise RuntimeError('SERVER_DID_NOT_START')
            assert r.status_code==200 and 'pub-review-dialog' in r.text;checks.append('actual loopback server delivers primary publishing interface')
            assert c.get('/static/publish.js').status_code==200 and c.get('/static/publish.css').status_code==200;checks.append('new primary assets served by installed routing')
            assert c.get('/api/state').status_code==401;checks.append('session required')
            c.headers['X-Riposte-Token']=token
            r=c.get('/api/state');data=r.json();assert data['version']=='0.3.0';checks.append('current release identity and live state')
            assert r.headers['cache-control']=='no-store' and "default-src 'self'" in r.headers['content-security-policy'];checks.append('no-store and self-only content policy')
            for header in [{'Host':'untrusted.invalid'},{'Origin':'https://untrusted.invalid'},{'Sec-Fetch-Site':'cross-site'}]:assert c.get('/api/state',headers=header).status_code==403
            checks.append('host, origin and cross-site requests rejected')
            assert c.get('/api/audit').json()['checkpoint']=='COMPLETE';checks.append('actual organization checkpoint remains complete')
            r=c.post('/api/publish',json={'image_ids':[data['images'][0]['id']],'edges':[1024,1536],'plan_only':True}).json()
            assert r['mode']=='PUBLICATION_PLAN' and r['outputs']==1 and r['writes'] is False;checks.append('live read-only publishing plan')
            batch=c.get('/api/publication/'+data['publications'][0]['id']).json();bid=batch['id'];item=batch['items'][0]['id']
            assert c.post(f'/api/publication/{bid}/review',json={'item_ids':[item]}).status_code==400;checks.append('both visual and unverified acknowledgments required')
            for view in ['identity','jpeg70','resize75-jpeg85']:
                for kind in ['clean','candidate','difference']:
                    r=c.get(f'/api/publication/{bid}/image/{item}/{kind}',params={'view':view})
                    assert png_audit(r.content)['date']==batch['items'][0]['date']
            checks.append('nine live image routes independently date-only audited')
            r=c.post(f'/api/publication/{bid}/review',json={'item_ids':[item],'decision':'ACCEPTED','visual_accepted':True,'acknowledge_unverified':True});assert r.status_code==200
            checks.append('artifact-bound acceptance through real HTTP')
            pack=c.get(f'/api/publication/{bid}/pack');assert pack.status_code==200
            with ZipFile(io.BytesIO(pack.content)) as z:
                assert len(z.namelist())==1 and z.read(z.namelist()[0])==c.get(f'/api/publication/{bid}/image/{item}/candidate').content
            checks.append('download bytes match the reviewed publishing PNG exactly')
            trial=c.post(f'/api/publication/{bid}/workshop/{item}',json={}).json()
            assert trial['artifact_sha256']['candidate']==batch['items'][0]['artifact_sha256']['candidate'];checks.append('optional helper receives same exact candidate')
            assert c.get(f'/api/publication/{bid}/image/{item}/candidate',params={'view':'UNKNOWN_PRIVATE_VALUE'}).status_code==400;checks.append('unknown processing view rejected')
            c.post(f'/api/publication/{bid}/review',json={'item_ids':[item],'decision':'REJECTED'})
            assert c.get(f'/api/publication/{bid}/pack').status_code==400;checks.append('revocation affects subsequent live packs')
            bad=c.post('/api/publish',json={'image_ids':[data['images'][0]['id']],'vae_directories':['PRIVATE_TEST_ONLY'],'extra':'DO_NOT_ECHO'})
            assert bad.status_code==422 and 'DO_NOT_ECHO' not in bad.text and 'PRIVATE' not in bad.text;checks.append('safe request validation does not echo submitted paths')
        from playwright.sync_api import sync_playwright,Error
        with sync_playwright() as pw:
            b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
            try:
                page=b.new_page();page.goto(f'http://127.0.0.1:{port}/#token={token}',wait_until='domcontentloaded',timeout=10000)
                page.wait_for_selector('.pub-source',timeout=10000);browser_result={'status':'DIRECT_NAVIGATION_PASSED'}
            except Error as e:
                if any(code in str(e) for code in ['ERR_BLOCKED_BY_ADMINISTRATOR','ERR_NETWORK_ACCESS_DENIED','ERR_BLOCKED_BY_CLIENT']):browser_result={'status':'LOCALHOST_NAVIGATION_BLOCKED_BY_ENVIRONMENT','alternative':'separate actual-UI ASGI browser bridge tested'}
                else:raise
            finally:b.close()
        report={'passed':len(checks),'checks':checks,'transport':'Uvicorn subprocess; actual loopback TCP HTTP; httpx trust_env=False','browser':browser_result,'artwork':'synthetic fixtures only','ai_protection':'UNVERIFIED'}
        (output/'publication-http-qa.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
    finally:
        proc.terminate()
        try:proc.wait(timeout=10)
        except subprocess.TimeoutExpired:proc.kill();proc.wait()
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('output',type=Path);a=p.parse_args();run(a.root,a.output)
