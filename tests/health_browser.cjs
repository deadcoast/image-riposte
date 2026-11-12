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
  const wait=async test=>{for(let n=0;n<300;n++){if(test())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out: '+test);};
  clearInterval(pollTimer);await wait(()=>!refreshing);pollTimer=setInterval(refresh,100);
  $('health-open').click();assert($('health-dialog').open,'workspace health dialog opens');
  const fetchReal=window.fetch;let posts=0;
  window.fetch=async(url,options={})=>{if(url==='/api/health'&&options.body)posts++;return fetchReal(url,options);};
  $('health-run').click();$('health-run').click();
  await wait(()=>!$('health-result').hidden);
  assert(posts===1,'double activation submits once');
  assert($('health-result').textContent.includes('Backup envelope'),'readable capacity summary');
  assert($('health-result').textContent.includes('Headers and entry shapes only'),'recovery qualification');
  assert(!$('health-result').textContent.includes('undefined'),'all result values render');
  const actual=(await api('state')).jobs.find(j=>j.operation==='health');
  assert(actual.read_only&&!actual.result.writes,'real authenticated job is read-only');
  assert(actual.result.history.statuses.APPLIED===1,'actual recovery journal summarized');
  busyJob=null;window.RiposteHealth.updateDisabled();
  window.fetch=async(url,options={})=>{if(url==='/api/health')throw Error('NETWORK_UNAVAILABLE');return fetchReal(url,options);};
  $('health-run').click();await wait(()=>!$('health-run').disabled);
  assert($('health-result').hidden&&$('health-status').textContent!=='Starting read-only storage inspection…','offline does not leave old totals looking current');
  window.fetch=fetchReal;
  let release,held=false;
  window.fetch=async(url,options={})=>{const response=await fetchReal(url,options);if(url==='/api/health'){held=true;await new Promise(r=>release=r);}return response;};
  $('health-run').click();await wait(()=>held);$('health-close').click();release();
  await wait(()=>!$('health-run').disabled);
  assert(!$('health-dialog').open,'late completion does not reopen dialog');
  assert(document.activeElement===$('health-open'),'focus restored to opener');
  window.fetch=fetchReal;$('health-open').click();
  window.RiposteHealth.onJob({id:'partial',operation:'health',state:'running',phase:'Inspecting workspace storage',processed:5});
  assert(!$('health-stop').hidden,'running inspection exposes cancellation');
  const partial={...actual.result,status:'INCOMPLETE',checkpoint:'INCOMPLETE',coverage:{...actual.result.coverage,issues:{ENTRY_LIMIT:1}}};
  window.RiposteHealth.completed({id:'partial',operation:'health',state:'incomplete',result:partial});
  assert($('health-status').textContent.includes('incomplete')&&$('health-result').textContent.includes('entry limit'),'partial results identified');
  window.RiposteHealth.onJob({id:'cancel',operation:'health',state:'running',phase:'Starting operation'});
  window.RiposteHealth.completed({id:'cancel',operation:'health',state:'cancelled'});
  assert($('health-result').hidden&&$('health-status').textContent.includes('No files changed'),'cancellation leaves no stale totals');
  window.RiposteHealth.onJob({id:'final',operation:'health',state:'running',phase:'Starting operation'});
  window.RiposteHealth.completed({id:'final',operation:'health',state:'done',result:actual.result});
  $('native-proof').textContent='PASS';
})().catch(e=>{document.getElementById('native-proof').textContent='FAIL '+(e.stack||e);});`;
async function main(){
  const html=fs.readFileSync(path.join(staticDir,'index.html'),'utf8').replace('</body>','<output id="native-proof">PENDING</output><script defer src="/probe.js"></script></body>');
  const probe = PROBE;
  const server=http.createServer((request,response)=>{
    const url=request.url;
    if(url==='/'){response.setHeader('Content-Type','text/html; charset=utf-8');response.end(html);}
    else if(url==='/probe.js'){response.setHeader('Content-Type','text/javascript');response.end(probe);}
    else if(url.startsWith('/static/')&&/^[a-z.-]+$/.test(url.slice(8))){const file=path.join(staticDir,url.slice(8));if(!fs.existsSync(file)){response.writeHead(404);response.end();return;}response.setHeader('Content-Type',url.endsWith('.js')?'text/javascript':url.endsWith('.json')?'application/json':'text/css');response.end(fs.readFileSync(file));}
    else {response.setHeader('Content-Type','application/json');response.end(JSON.stringify(url==='/api/state'?{images:[],trials:[],jobs:[],publications:[]}:{}));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const tempRoot = fs.realpathSync(os.tmpdir());
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-health-'));
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
        const ready=await command('Runtime.evaluate',{expression:'!!window.RiposteHealth',returnByValue:true});
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
      await command('Runtime.evaluate',{expression:"$('health-dialog').scrollTop=0"});
      const layout=await command('Runtime.evaluate',{expression:"({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})",returnByValue:true});
      assert.ok(layout.result.value.scroll<=layout.result.value.client+1,JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
    }
    const key=async(key,code,virtual)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual});};
    await key('Escape','Escape',27);
    await pause(100); // Native dialog close/focus restoration runs as a queued event.
    const closed=await command('Runtime.evaluate',{expression:"!$('health-dialog').open&&document.activeElement===$('health-open')",returnByValue:true});
    if(!closed.result.value){const state=await command('Runtime.evaluate',{expression:"JSON.stringify({open:$('health-dialog').open,focus:document.activeElement.id,opener:getComputedStyle($('health-open')).display,rail:getComputedStyle(document.querySelector('.rail')).display})",returnByValue:true});throw Error('Escape state: '+state.result.value);}
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-health-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS health_browser')).catch(e=>{console.error(e);process.exitCode=1;});
