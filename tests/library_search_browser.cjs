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
  const done=()=>!$('private-search-run').disabled&&!$('private-results').getAttribute('aria-busy').includes('true');
  const input=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('input',{bubbles:true}));};
  $('private-search-open').click(); await wait(done);
  assert($('private-results').children.length===50,'bounded first page');
  assert($('private-results').textContent.includes('Private-Café'),'original titles available only after opt in');
  assert(!$('private-next').disabled,'next page available');
  $('private-next').click(); await wait(done);
  assert($('private-results').children.length===2&&$('private-search-status').textContent.includes('51–52'),'next page actual server');
  $('private-prev').click(); await wait(done);
  input('private-query','CAFE\u0301-MOONLIGHT-000'); $('private-search-run').click(); await wait(done);
  assert($('private-results').children.length===1,'normalized Unicode literal query');
  assert(!location.href.includes('CAFE')&&!Object.values(localStorage).some(x=>x.includes('Moonlight')),'query not persisted');
  const fetchReal=window.fetch;
  let posts=0,release,held=false;
  window.fetch=async(url,options={})=>{if(url==='/api/library-search'){posts++;if(posts===1){const response=await fetchReal(url,options);held=true;await new Promise(r=>release=r);return response;}}return fetchReal(url,options);};
  input('private-query','Moonlight'); $('private-search-run').click(); await wait(()=>held);
  input('private-query','no-match-unique'); $('private-search-run').click(); await wait(done);release();await new Promise(r=>setTimeout(r,100));
  assert(!$('private-results').children.length&&$('private-search-status').textContent.includes('No matches'),'late results never replace new filters');
  window.fetch=async(url,options={})=>{if(url==='/api/library-search')throw Error('offline');return fetchReal(url,options);};
  $('private-search-run').click();await wait(done);
  assert(!$('private-search-error').hidden&&!$('private-results').children.length,'offline error retains inputs without stale rows');
  assert($('private-query').value==='no-match-unique','draft retained after failure');
  window.fetch=fetchReal;
  input('private-year','0000');$('private-search-run').click();await wait(done);
  assert($('private-year').getAttribute('aria-invalid')==='true'&&document.activeElement===$('private-year'),'invalid field identified and focused');
  input('private-year','');$('private-query-clear').click();await wait(done);
  assert($('private-query').value===''&&document.activeElement===$('private-query'),'clear immediate and focus retained');
  let count=0;window.fetch=async(url,options={})=>{if(url==='/api/library-search')count++;return fetchReal(url,options);};
  $('private-query').dispatchEvent(new CompositionEvent('compositionstart'));input('private-query','Moonlight');
  await new Promise(r=>setTimeout(r,400));assert(count===0,'IME composition does not submit');
  $('private-query').dispatchEvent(new CompositionEvent('compositionend'));await wait(()=>count===1);await wait(done);
  window.fetch=fetchReal;
  document.querySelector('#private-results button').click();await wait(()=>!$('private-search-dialog').open);
  await new Promise(r=>setTimeout(r,100));
  assert(state.selected&&document.activeElement===$('private-search-open'),'inspect uses existing canonical selection and restores focus');
  assert(!('original_filename' in state.selected)&&!$('private-results').children.length&&!$('private-query').value,'close clears private results and text');
  $('private-search-open').click();await wait(done);
  input('private-title-state','unknown');await wait(()=>$('private-search-status').textContent.includes('No matches'));
  input('private-title-state','all');await wait(()=>$('private-results').children.length===50);await wait(done);
  $('private-query').dispatchEvent(new CompositionEvent('compositionstart'));
  $('private-search-close').click();await new Promise(r=>setTimeout(r,100));
  $('private-search-open').click();await wait(()=>!$('private-search-run').disabled&&$('private-results').children.length===50);
  window.fetch=async(url,options={})=>url==='/api/library-search'?new Response(JSON.stringify({code:'LIBRARY_SEARCH_STALE'}),{status:400,headers:{'Content-Type':'application/json'}}):fetchReal(url,options);
  $('private-next').click();await wait(done);
  assert(!$('private-search-error').hidden&&$('private-search-error').textContent.includes('first page'),'stale page has restart guidance');
  window.fetch=fetchReal;$('private-search-run').click();await wait(done);
  document.querySelector('#private-search-form details').open=false;
  $('native-proof').textContent='PASS';
})().catch(e=>{document.getElementById('native-proof').textContent='FAIL '+(e.stack||e);});
`;
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
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-search-'));
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
        const ready=await command('Runtime.evaluate',{expression:"!!$('private-search-open')?.onclick",returnByValue:true});
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
      await command('Runtime.evaluate',{expression:"$('private-search-dialog').scrollTop=0"});
      const layout=await command('Runtime.evaluate',{expression:"({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})",returnByValue:true});
      assert.ok(layout.result.value.scroll<=layout.result.value.client+1,JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
    }
    const key=async(key,code,virtual)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual});};
    await command('Runtime.evaluate',{expression:"$('private-title-state').focus()"});
    await key(' ','Space',32); await pause(100);
    await key('ArrowDown','ArrowDown',40); await key('Enter','Enter',13); await pause(500);
    const chosen=await command('Runtime.evaluate',{expression:"$('private-title-state').value",returnByValue:true});
    assert.equal(chosen.result.value,'known','native select keyboard choice');
    await key('Escape','Escape',27);
    await pause(100); // Native dialog close/focus restoration runs as a queued event.
    const closed=await command('Runtime.evaluate',{expression:"!$('private-search-dialog').open&&document.activeElement===$('private-search-open')",returnByValue:true});
    if(!closed.result.value){const state=await command('Runtime.evaluate',{expression:"JSON.stringify({open:$('private-search-dialog').open,focus:document.activeElement.id,opener:getComputedStyle($('private-search-open')).display,rail:getComputedStyle(document.querySelector('.rail')).display})",returnByValue:true});throw Error('Escape state: '+state.result.value);}
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-search-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS library_search_browser')).catch(e=>{console.error(e);process.exitCode=1;});
