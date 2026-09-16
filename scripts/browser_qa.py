"""Run against a temporary synthetic fixture workspace, not real personal files."""
import json
import argparse
import base64
from pathlib import Path
from playwright.sync_api import sync_playwright

def run(output:Path, root:Path|None=None):
    output.mkdir(parents=True,exist_ok=True)
    issues=[];checks=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
        page=browser.new_page(viewport={'width':1512,'height':1060},device_scale_factor=1)
        page.on('pageerror',lambda exc:issues.append(str(exc)))
        if root is None:
            page.goto('http://127.0.0.1:8765/#token=browser-validation-only',wait_until='networkidle')
        else:
            # Render the real UI on about:blank, with requests dispatched through
            # FastAPI TestClient. No browser URL-policy changes or network bypass.
            from fastapi.testclient import TestClient
            from riposte.server import create_app, STATIC
            app=create_app(root, token='browser-validation-only')
            client=TestClient(app)
            def dispatch(path, options):
                response=client.request(options.get('method','GET'),path,
                    headers=options.get('headers',{}),content=options.get('body'))
                return {'status':response.status_code,'headers':dict(response.headers),
                        'body':base64.b64encode(response.content).decode('ascii')}
            page.expose_function('_riposte_test_dispatch',dispatch)
            html=(STATIC/'index.html').read_text()
            html=html.replace('<link rel="stylesheet" href="/static/style.css">','')
            html=html.replace('<script src="/static/app.js" defer></script>','')
            html=html.replace('<script src="/static/publish.js" defer></script>','')
            html=html.replace('<link rel="stylesheet" href="/static/publish.css">','')
            page.set_content(html)
            page.add_style_tag(content=(STATIC/'style.css').read_text())
            page.add_style_tag(content=(STATIC/'publish.css').read_text())
            page.add_script_tag(content="""
                Object.defineProperty(window,'sessionStorage',{value:{getItem:()=>
                    'browser-validation-only',setItem:()=>{}}});
                window.fetch=async(path,options={})=>{
                    const value=await window._riposte_test_dispatch(String(path),options);
                    const bytes=Uint8Array.from(atob(value.body),c=>c.charCodeAt(0));
                    return new Response(bytes,{status:value.status,headers:value.headers});
                };
            """)
            page.add_script_tag(content=(STATIC/'app.js').read_text())
            page.add_script_tag(content=(STATIC/'publish.js').read_text())
        page.wait_for_selector('.art',timeout=10000)
        assert page.locator('.art').count()==6;checks.append('live catalog renders six fixture images')
        assert page.locator('#inspect-name').inner_text().endswith('.png');checks.append('selection populates inspector')
        assert 'RIPOSTE' in page.title() and 'SHROUD' not in page.locator('body').inner_text();checks.append('application rename reaches rendered interface')
        assert page.locator('#demo-badge').is_visible();checks.append('synthetic demo status is explicit')
        assert 'July' not in page.locator('#tree').inner_text();checks.append('calendar navigator only exposes populated months')
        page.screenshot(path=str(output/'library-desktop.png'),full_page=True)
        page.get_by_role('button',name='MED',exact=True).click();assert page.locator('.art').count()==0
        page.get_by_role('button',name='All sizes',exact=True).click();assert page.locator('.art').count()==6;checks.append('live size filtering')
        page.locator('#search').fill('2025');assert page.locator('.art').count()==2;page.locator('#search').fill('');checks.append('canonical date search')
        page.locator('.art').first.dblclick();page.wait_for_selector('#lab-view:not([hidden])');page.wait_for_timeout(500)
        checks.append('actual artwork double-click opens lab without losing second click')
        assert page.locator('#transport-body tr').count()==8;checks.append('real trial measurements populate lab')
        page.locator('#split').fill('23');assert '23%' in page.locator('#candidate-clip').get_attribute('style');checks.append('before-after split control')
        page.locator('#zoom-in').click();assert page.locator('#zoom-value').inner_text()=='140%'
        stage=page.locator('#stage');stage.scroll_into_view_if_needed();box=stage.bounding_box()
        page.mouse.move(box['x']+box['width']*.2,box['y']+box['height']*.5);page.mouse.down()
        page.mouse.move(box['x']+box['width']*.2+30,box['y']+box['height']*.5+20);page.mouse.up()
        assert 'translate(0px,0px)' not in page.locator('#clean-layer').get_attribute('style')
        assert page.locator('#clean-layer').get_attribute('style')==page.locator('#candidate-layer').get_attribute('style')
        checks.append('zoom and pan stay synchronized between actual image layers')
        page.locator('#zoom-fit').click();assert page.locator('#zoom-value').inner_text()=='FIT'
        page.locator('#zoom-native').click();assert page.locator('#zoom-value').inner_text()!='FIT';page.locator('#zoom-fit').click()
        checks.append('fit and native-raster inspection controls operate')
        page.locator('#transport-view').select_option('jpeg70');page.wait_for_timeout(250)
        assert 'view=jpeg70' in page.locator('#lab-candidate').get_attribute('data-image-path')
        assert page.locator('#transport-body tr.active').count()==1;checks.append('publication view selects actual paired codec output')
        page.locator('#transport-body tr').first.click();page.wait_for_timeout(150)
        assert page.locator('#transport-view').input_value()=='identity';checks.append('measurement rows drive the inspector')
        page.locator('#divider').focus();page.keyboard.press('ArrowRight');assert page.locator('#split').input_value()=='25'
        checks.append('comparison divider is keyboard-operable')
        page.locator('#split').fill('50');page.screenshot(path=str(output/'lab-desktop.png'),full_page=True)
        page.get_by_role('button',name='Δ ×12',exact=True).click();page.wait_for_timeout(200);assert page.locator('#divider').is_hidden();checks.append('difference view')
        page.get_by_role('button',name='Compare',exact=True).click()
        page.locator('[data-control=challenge]').click();page.wait_for_function("document.querySelectorAll('#qualification-body tr').length===24")
        assert 'Encoder evidence only' in page.locator('#qualification-summary').inner_text()
        assert 'SYNTHETIC_TEST_ORACLE' in page.locator('#qualification-summary').inner_text()
        checks.append('real synthetic-oracle qualification report renders with its evidence boundary')
        page.screenshot(path=str(output/'challenge-desktop.png'),full_page=True)
        page.locator('[data-results=generation]').click();page.wait_for_function("document.querySelectorAll('.generation-arm').length===5")
        assert 'NOT PRETRAINED' in page.locator('#generation-summary').inner_text();checks.append('five-arm review labels synthetic generator honestly')
        page.locator('#generation-frame').fill('1');page.wait_for_timeout(200)
        assert page.locator('#generation-frame-value').inner_text()=='2 / 2'
        assert all('F001.png' in p for p in page.locator('.generation-arm img').evaluate_all('(images)=>images.map(i=>i.dataset.imagePath)'))
        checks.append('video review frame slider synchronizes every control arm')
        page.locator('#generation-group').select_option('1');page.wait_for_timeout(100)
        assert 'jpeg70' in page.locator('#generation-group option:checked').inner_text().lower().replace(' · ','') or 'JPEG' in page.locator('#generation-group option:checked').inner_text()
        checks.append('generation review selects paired publication view and seed')
        page.screenshot(path=str(output/'generation-desktop.png'),full_page=True)
        page.locator('[data-control=build]').click();page.locator('#preflight').click()
        page.wait_for_function("!document.querySelector('#preflight-result').textContent.includes('Inspecting')")
        assert 'CPU' in page.locator('#preflight-result').inner_text();checks.append('read-only runtime preflight uses real backend')
        page.locator('[data-control=export]').click();assert page.locator('#export').is_disabled()
        page.locator('#ack-export').check();assert page.locator('#export').is_enabled()
        page.locator('#export').click();page.wait_for_selector('#report-dialog[open]')
        assert 'DATE_ONLY' in page.locator('#report-content').inner_text() and 'UNVERIFIED' in page.locator('#report-content').inner_text()
        page.locator('#report-dialog .dialog-close').click();page.locator('#ack-export').uncheck();checks.append('export is separately acknowledged and reports audited output')
        page.locator('[data-view=evidence]').click();page.wait_for_selector('.method-row');assert page.locator('.method-row').count()==12;checks.append('12 primary-source method records')
        page.locator('#audit').click();page.wait_for_selector('#report-dialog[open]');assert 'COMPLETE' in page.locator('#report-content').inner_text();page.locator('#report-dialog .dialog-close').click();checks.append('live workspace audit')
        page.locator('#scan').click();page.locator('#run-plan').click();page.wait_for_function("document.querySelector('#plan-result').textContent.includes('READ_ONLY')")
        assert page.locator('#apply').is_disabled();page.locator('#ack-remove').check();assert page.locator('#apply').is_enabled();checks.append('read-only migration preview and explicit source-removal gate')
        page.locator('#organize-dialog .dialog-close').click()
        page.locator('[data-view=library]').click()
        for width,height in [(1024,900),(390,844)]:
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'horizontal overflow at {width}'
            page.screenshot(path=str(output/f'library-{width}.png'),full_page=True)
            checks.append(f'no library horizontal overflow at {width}px')
            page.locator('[data-view=lab]').click();page.locator('[data-results=generation]').click();page.wait_for_timeout(200)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),f'lab overflow at {width}'
            page.screenshot(path=str(output/f'lab-{width}.png'),full_page=True)
            checks.append(f'no generation-review horizontal overflow at {width}px')
            page.locator('[data-view=library]').click()
        assert not issues,issues
        checks.append('no browser JavaScript errors')
        browser.close()
        if root is not None:
            client.close()
            app.state.jobs.pool.shutdown(wait=True)
    report={'harness':'In-process FastAPI transport / Chromium about:blank rendering' if root else 'Live localhost HTTP','passed':len(checks),'checks':checks,'errors':issues,'fixture':'Synthetic geometric images, real gradients through a toy oracle, and stub generation frames. None is pretrained-model efficacy evidence.'}
    (output/'browser-qa.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--in-process-root',type=Path)
    args=parser.parse_args()
    run(Path(__file__).resolve().parents[1]/'evidence',args.in_process_root)
