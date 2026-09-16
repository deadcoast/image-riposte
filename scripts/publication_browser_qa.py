"""Actual UI/API/optimizer integration with a labeled synthetic encoder, not pretrained efficacy."""
from __future__ import annotations
import argparse, base64, importlib.util, json, re, shutil
from pathlib import Path
from unittest.mock import patch
from zipfile import ZipFile
import torch
from fastapi.testclient import TestClient
from playwright.sync_api import sync_playwright
from riposte.server import create_app, STATIC

class SyntheticEncoder:
    device='cpu'
    identity={'kind':'SYNTHETIC_BROWSER_ORACLE_NOT_PRETRAINED','weights_sha256':'c'*64}
    def __call__(self,x):
        small=torch.nn.functional.avg_pool2d(x,4)
        return small.square()+.05*small

def run(root:Path,output:Path):
    output.mkdir(parents=True,exist_ok=True)
    if not root.exists():
        spec=importlib.util.spec_from_file_location('fixtures',Path(__file__).with_name('make_demo.py'))
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);module.make_demo(root)
    from riposte.store import state_relative
    if not (root / state_relative(root, "DEMO")).is_file():
        raise RuntimeError("SYNTHETIC_DEMO_WORKSPACE_REQUIRED")
    checks=[];errors=[]
    with patch('riposte.models.LocalEncoder',lambda *a,**k:SyntheticEncoder()),TestClient(create_app(root,'publication-browser-fixture')) as client,sync_playwright() as pw:
        browser=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1512,'height':1120},device_scale_factor=1)
        page.on('pageerror',lambda e:errors.append(str(e)))
        def dispatch(path,options):
            r=client.request(options.get('method','GET'),path,headers=options.get('headers',{}),content=options.get('body'))
            return {'status':r.status_code,'headers':dict(r.headers),'body':base64.b64encode(r.content).decode('ascii')}
        page.expose_function('_riposte_fixture_dispatch',dispatch)
        html=re.sub(r'<link rel="stylesheet" href="/static/[^\"]+">','',(STATIC/'index.html').read_text())
        html=re.sub(r'<script src="/static/[^\"]+" defer></script>','',html)
        page.set_content(html)
        for file in ('style.css','publish.css'):page.add_style_tag(content=(STATIC/file).read_text())
        page.add_script_tag(content="""Object.defineProperty(window,'sessionStorage',{value:{getItem:()=> 'publication-browser-fixture',setItem:()=>{}}});window.fetch=async(path,options={})=>{const r=await window._riposte_fixture_dispatch(String(path),options);return new Response(Uint8Array.from(atob(r.body),c=>c.charCodeAt(0)),{status:r.status,headers:r.headers});};""")
        for file in ('app.js','publish.js'):page.add_script_tag(content=(STATIC/file).read_text())
        page.wait_for_selector('.art',timeout=10000)
        assert page.locator('#demo-badge').is_visible();checks.append('synthetic demo banner visible')
        page.locator('#open-lab').click();page.wait_for_selector('#publish-view:not([hidden])')
        assert page.locator('#lab-view').is_hidden();checks.append('primary library action enters publishing, not workshop')
        assert page.locator('.pub-source').count()==6 and page.locator('.pub-source input:checked').count()==1
        checks.append('real canonical collection and selection carried into publishing')
        page.locator('#pub-select-all').click();assert page.locator('.pub-source input:checked').count()==6
        page.locator('#pub-clear').click();assert page.locator('#pub-plan-button').is_disabled();checks.append('select-all, clear and empty selection guard')
        for i in (0,1,2):page.locator('.pub-source input').nth(i).check()
        assert page.locator('#pub-start').is_disabled();checks.append('missing local-model choice cannot silently trigger a noise filter')
        page.locator('#pub-models').fill('SYNTHETIC_BROWSER_FIXTURE')
        page.locator('#pub-steps').fill('3');page.locator('#pub-restarts').select_option('1')
        page.locator('.pub-sizes input[value="1536"]').check();page.locator('#pub-plan-button').click()
        page.wait_for_function("document.querySelector('#pub-plan').textContent.includes('3 independently protected')")
        assert '3 duplicate sizes skipped' in page.locator('#pub-plan').inner_text();checks.append('read-only planning explains no-upscale duplicate avoidance')
        assert not (root/'.riposte/publishing').exists();checks.append('planning did not create publishing folders')
        page.locator('#pub-start').click()
        page.wait_for_function("document.querySelectorAll('.pub-output:not(.placeholder)').length===3",timeout=45000)
        page.wait_for_function("!document.querySelector('#pub-start').disabled",timeout=10000)
        assert page.locator('#pub-download').is_disabled();checks.append('real optimizer produced three unapproved final-raster outputs')
        assert page.locator('#demo-badge').is_visible();checks.append('render completion never hides synthetic or unverified status')
        page.wait_for_selector('#toast',state='hidden',timeout=10000)
        page.screenshot(path=str(output/'publish-desktop.png'),full_page=True)
        page.locator('.pub-output button').first.click();page.wait_for_selector('#pub-review-dialog[open]')
        assert page.locator('#pub-review-accept').is_disabled();checks.append('exact-output review requires both explicit acknowledgements')
        page.wait_for_function("document.querySelector('#pub-review-clean').naturalWidth>0&&document.querySelector('#pub-review-candidate').naturalWidth>0")
        assert 'view=identity' in page.locator('#pub-review-candidate').get_attribute('data-image-path');checks.append('review initially serves exact verified PNGs')
        page.locator('#pub-review-native').click();assert 'native' in page.locator('#pub-review-pair').get_attribute('class')
        page.locator('#pub-review-fit').click();checks.append('fit and native-pixel inspection')
        page.locator('#pub-review-difference').click();assert '/difference?' in page.locator('#pub-review-candidate').get_attribute('data-image-path')
        page.locator('#pub-review-difference').click();checks.append('difference visualization stays a preview, not a defense')
        page.locator('#pub-review-view').select_option('jpeg70');page.wait_for_timeout(250)
        assert 'view=jpeg70' in page.locator('#pub-review-clean').get_attribute('data-image-path') and 'view=jpeg70' in page.locator('#pub-review-candidate').get_attribute('data-image-path')
        assert 'RESIDUAL RMS' in page.locator('#pub-review-metrics').inner_text();checks.append('actual matched JPEG previews with separate fidelity scope')
        page.locator('#pub-review-view').select_option('identity');page.wait_for_timeout(200)
        page.screenshot(path=str(output/'publish-review-desktop.png'),full_page=True)
        page.locator('#pub-review-quality').check();assert page.locator('#pub-review-accept').is_disabled()
        page.locator('#pub-review-ack').check();assert page.locator('#pub-review-accept').is_enabled();page.locator('#pub-review-accept').click()
        page.wait_for_selector('#pub-review-dialog',state='hidden');page.wait_for_function("!document.querySelector('#pub-download').disabled")
        assert page.locator('.pub-output.approved').count()==1;checks.append('review commits acceptance only for the inspected output')
        with page.expect_download(timeout=10000) as dl:page.locator('#pub-download').click()
        archive=output/'browser-approved-pack.zip';dl.value.save_as(str(archive))
        with ZipFile(archive) as z:
            assert len(z.namelist())==1 and all(s.endswith('.png') for s in z.namelist());assert not z.comment
        checks.append('browser downloads a pack containing only approved PNGs')
        page.locator('.pub-output button').first.click();page.locator('#pub-review-reject').click();page.wait_for_selector('#pub-review-dialog',state='hidden')
        assert page.locator('#pub-download').is_disabled();checks.append('rejecting an approved image revokes it from new packs')
        page.locator('.pub-output button').nth(1).click();page.locator('#pub-workshop').click();page.wait_for_selector('#lab-view:not([hidden])')
        assert page.locator('#pub-review-dialog').is_hidden();checks.append('optional workshop handoff uses committed publishing output')
        page.locator('[data-view=publish]').click();page.wait_for_timeout(200)
        for width,height in [(1024,1000),(390,844)]:
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),f'publishing overflow {width}'
            page.screenshot(path=str(output/f'publish-{width}.png'),full_page=True);checks.append(f'publishing layout fits {width}px')
            page.locator('.pub-output button').first.click();page.wait_for_selector('#pub-review-dialog[open]')
            page.screenshot(path=str(output/f'publish-review-{width}.png'),full_page=True)
            assert page.evaluate("document.querySelector('#pub-review-dialog').scrollWidth <= document.querySelector('#pub-review-dialog').clientWidth"),f'review overflow {width}'
            checks.append(f'review fits {width}px')
            page.locator('#pub-review-close').click()
        assert not errors,errors;checks.append('no JavaScript exceptions')
        browser.close()
    result={'checks_passed':len(checks),'checks':checks,'javascript_errors':errors,'transport':'Real FastAPI TestClient through browser fetch bridge','models':'SYNTHETIC_ORACLE_NOT_PRETRAINED','optimizer':'actual release-v1 CPU autograd, codecs, best-iterate and quality gates','ai_protection':'UNVERIFIED'}
    (output/'publication-browser-qa.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('root',type=Path);parser.add_argument('output',type=Path);args=parser.parse_args();run(args.root,args.output)
