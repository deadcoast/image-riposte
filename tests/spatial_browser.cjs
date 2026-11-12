// Shipping HTML, CSS and JavaScript in real Chromium; network fixtures isolate UI consent.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const http=require('node:http'),os=require('node:os');
const {spawn}=require('node:child_process');
const staticDir=path.join(__dirname,'../src/riposte/static');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const PROBE=String.raw`(async()=>{
  await recovery.ready;
  const assert=(ok,message)=>{if(!ok)throw Error(message);};
  const wait=async test=>{for(let n=0;n<500;n++){if(test())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out: '+test);};
  const input=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('input',{bubbles:true}));};
  setView('publish');$('pub-select-all').click();$('pub-spatial').open=true;
  assert($('spatial-image').options.length===2,'selected sources are the mask targets');
  assert($('spatial-preview').disabled&&$('spatial-export').disabled,'no mandatory mask');
  const upload=()=>{const bytes=Uint8Array.from(atob('__MASK_BASE64__'),c=>c.charCodeAt(0));const files=new DataTransfer();files.items.add(new File([bytes],'private-regions.png',{type:'image/png'}));$('spatial-file').files=files.files;$('spatial-file').dispatchEvent(new Event('change'));};
  upload();await wait(()=>!RiposteSpatial.pending());
  assert($('spatial-masks').children.length===1&&!$('spatial-preview').disabled,'actual PNG accepted by authenticated server');
  assert(RipostePublish.request().masks.length===1,'publishing carries source-bound pixels');
  $('spatial-preview').click();await wait(()=>$('spatial-previews').children.length===1);
  assert($('spatial-previews').textContent.includes('pixels unchanged'),'exact cap statistics shown');
  assert(document.querySelector('#spatial-previews img').naturalWidth===96,'actual final-size artwork overlay loaded');
  assert(!Object.values(localStorage).some(value=>value.includes('private-regions')),'no mask name stored');
  const fetchReal=window.fetch;
  let release,held=false;
  window.fetch=async(url,options={})=>{if(url==='/api/publish'){const response=await fetchReal(url,options);held=true;await new Promise(r=>release=r);return response;}return fetchReal(url,options);};
  $('spatial-preview').click();await wait(()=>held);input('pub-epsilon','3');release();await new Promise(r=>setTimeout(r,100));
  assert(!$('spatial-previews').children.length,'changed limits discard late previews');
  held=false;$('spatial-preview').click();await wait(()=>held);$('spatial-cancel').click();release();await new Promise(r=>setTimeout(r,100));
  assert(!$('spatial-previews').children.length&&$('spatial-cancel').hidden&&!$('spatial-preview').disabled,'cancel retains masks and suppresses late response');
  window.fetch=async(url,options={})=>{if(url==='/api/artist-mask'){const response=await fetchReal(url,options);held=true;await new Promise(r=>release=r);return response;}return fetchReal(url,options);};
  held=false;upload();await wait(()=>held);$('spatial-cancel').click();release();await new Promise(r=>setTimeout(r,100));
  assert(!RiposteSpatial.pending()&&RipostePublish.request().masks.length===1,'upload cancellation restores controls and prior attachment');
  window.fetch=async(url,options={})=>{if(url==='/api/publish')throw Error('offline');return fetchReal(url,options);};
  $('spatial-preview').click();await wait(()=>!$('spatial-error').hidden);
  assert(RipostePublish.request().masks.length===1&&$('spatial-previews').children.length===0,'offline retains mask and hides stale preview');
  window.fetch=fetchReal;input('pub-epsilon','4');$('spatial-preview').click();await wait(()=>$('spatial-previews').children.length===1);
  const wrong=new DataTransfer();wrong.items.add(new File(['invalid'],'bad.png',{type:'image/png'}));$('spatial-file').files=wrong.files;$('spatial-file').dispatchEvent(new Event('change'));await wait(()=>!RiposteSpatial.pending());
  assert(!$('spatial-error').hidden&&RipostePublish.request().masks.length===1,'invalid upload preserves prior mask and gives correction');
  document.querySelector('#spatial-masks button').click();assert(!RipostePublish.request().masks.length&&$('spatial-preview').disabled,'remove restores optional no-mask behavior');
  upload();await wait(()=>!RiposteSpatial.pending());$('spatial-preview').click();await wait(()=>$('spatial-previews').children.length===1);
  assert(document.querySelector('#spatial-previews a').download.startsWith('riposte-budget-'),'exact cap download available');
  $('spatial-image').selectedIndex=1;$('spatial-image').dispatchEvent(new Event('change'));upload();await wait(()=>!RiposteSpatial.pending());
  input('pub-extra-edges','64,80');$('spatial-preview').click();await wait(()=>$('spatial-previews').children.length===3&&!$('spatial-next').disabled);
  assert($('spatial-status').textContent.includes('1–3 of 6'),'bounded first raster page');
  $('spatial-next').click();await wait(()=>$('spatial-status').textContent.includes('4–6 of 6'));
  assert($('spatial-next').disabled&&!$('spatial-prev').disabled&&$('spatial-previews').children.length===3,'bounded next page controls');
  $('spatial-prev').click();await wait(()=>$('spatial-status').textContent.includes('1–3 of 6'));
  $('spatial-image').selectedIndex=0;
  $('spatial-image').focus();$('native-proof').textContent='PASS';
})().catch(e=>{document.getElementById('native-proof').textContent='FAIL '+(e.stack||e);});
`;
async function main(){
  const html=fs.readFileSync(path.join(staticDir,'index.html'),'utf8').replace('</body>','<output id="native-proof">PENDING</output><script defer src="/probe.js"></script></body>');
  const probe = PROBE.replace('__MASK_BASE64__',process.env.RIPOSTE_MASK_PNG);
  const server=http.createServer((request,response)=>{
    const url=request.url;
    if(url==='/'){response.setHeader('Content-Type','text/html; charset=utf-8');response.end(html);}
    else if(url==='/probe.js'){response.setHeader('Content-Type','text/javascript');response.end(probe);}
    else if(url.startsWith('/static/')&&/^[a-z.-]+$/.test(url.slice(8))){const file=path.join(staticDir,url.slice(8));if(!fs.existsSync(file)){response.writeHead(404);response.end();return;}response.setHeader('Content-Type',url.endsWith('.js')?'text/javascript':url.endsWith('.json')?'application/json':'text/css');response.end(fs.readFileSync(file));}
    else {response.setHeader('Content-Type','application/json');response.end(JSON.stringify(url==='/api/state'?{images:[],trials:[],jobs:[],publications:[]}:{}));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const tempRoot = fs.realpathSync(os.tmpdir());
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-spatial-'));
  const browser = spawn(process.argv[2], [
    '--headless=new', '--disable-gpu', '--disable-background-networking', '--no-first-run',
    '--no-default-browser-check', '--disable-extensions', '--user-data-dir=' + profile,
    '--remote-debugging-port=0', 'about:blank',
  ], {windowsHide: true, stdio: 'ignore'});
  let socket, command;
  try {
    const portFile = path.join(profile, 'DevToolsActivePort');
    for (let n = 0; n < 200 && !fs.existsSync(portFile); n++) await pause(25);
    assert.ok(fs.existsSync(portFile), 'browser starts with an isolated profile');
    const port = fs.readFileSync(portFile, 'utf8').split(/\r?\n/)[0];
    const targets = await (await fetch('http://127.0.0.1:' + port + '/json/list')).json();
    const target = targets.find(page => page.type === 'page');
    socket = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => {
      socket.addEventListener('open', resolve, {once: true});
      socket.addEventListener('error', reject, {once: true});
    });
    let sequence = 0;
    const pending = new Map();
    socket.addEventListener('message', event => {
      const message = JSON.parse(event.data), request = pending.get(message.id);
      if (request) {pending.delete(message.id); clearTimeout(request.timer); message.error ? request.reject(Error(JSON.stringify(message.error))) : request.resolve(message.result);}
    });
    command = (method, params = {}) => new Promise((resolve, reject) => {
      const id = ++sequence;
      const timer = setTimeout(() => {pending.delete(id); reject(Error('Browser command timed out: ' + method));}, 20000);
      pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
    });
    await command('Page.navigate', {url: process.env.RIPOSTE_SORT_LIVE || 'http://127.0.0.1:' + server.address().port + '/'});
    if(process.env.RIPOSTE_SORT_LIVE){
      for(let n=0;n<200;n++){
        const ready=await command('Runtime.evaluate',{expression:"!!window.RiposteSpatial&&state.images.length===2",returnByValue:true});
        if(ready.result.value)break;await pause(25);
      }
      await command('Runtime.evaluate',{expression:`document.body.append(Object.assign(document.createElement('output'),{id:'native-proof',textContent:'PENDING'}));`+probe});
    }
    let observed;
    for (let n = 0; n < (process.env.RIPOSTE_SORT_LIVE?2400:200); n++) {
      const response = await command('Runtime.evaluate', {expression: "document.getElementById('native-proof')?.textContent", returnByValue: true});
      observed = response.result.value;
      if (observed && observed !== 'PENDING') break;
      await pause(25);
    }
    assert.equal(observed, 'PASS', 'native browser result: ' + observed);
    for(const [name,width,height] of [['wide',1280,1000],['narrow',390,844]]){
      await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
      await command('Runtime.evaluate',{expression:"$('pub-spatial').scrollIntoView({block:'start'})"});
      const layout=await command('Runtime.evaluate',{expression:"({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})",returnByValue:true});
      assert.ok(layout.result.value.scroll<=layout.result.value.client+1,JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
    }
    const key=async(key,code,virtual)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual});};
    await command('Runtime.evaluate',{expression:"$('spatial-image').focus()"});
    await key(' ','Space',32); await pause(100);
    await key('ArrowDown','ArrowDown',40); await key('Enter','Enter',13); await pause(500);
    const chosen=await command('Runtime.evaluate',{expression:"$('spatial-image').selectedIndex",returnByValue:true});
    assert.equal(chosen.result.value,1,'native select keyboard choice');
    await key('Escape','Escape',27);
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-spatial-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS spatial_browser')).catch(e=>{console.error(e);process.exitCode=1;});
