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
  const change=(id,value)=>{$(id).value=value;$(id).dispatchEvent(new Event('input',{bubbles:true}));};
  clearInterval(pollTimer);await wait(()=>!refreshing);setView('publish');
  $('pub-select-all').click();change('pub-models','PRIVATE_LOCAL_MODEL');change('pub-device','cpu');
  $('pub-recipes').open=true;await wait(()=>$('pub-recipe-status').textContent.startsWith('0 saved'));
  assert($('pub-recipe-load').disabled,'empty library does not enable load');
  change('pub-recipe-name','Print');change('pub-seed','123');change('pub-extra-edges','768');
  const posts=[],fetchReal=window.fetch;
  window.fetch=async(url,options={})=>{if(options.body)posts.push({url,body:JSON.parse(options.body)});return fetchReal(url,options);};
  $('pub-recipe-preview').click();await wait(()=>!$('pub-recipe-save').disabled);
  assert($('pub-recipe-preview-values').textContent.includes('123'),'review includes seed');
  assert((await api('recipes')).recipes.length===0,'preview writes no library');
  $('pub-recipe-save').click();$('pub-recipe-save').click();await wait(()=>$('pub-recipe-status').textContent.startsWith('Saved Print'));
  assert(posts.filter(p=>p.body.save).length===1,'double save dispatched only once');
  assert(posts.filter(p=>p.body.save).every(p=>!JSON.stringify(p.body).includes('PRIVATE_LOCAL_MODEL')),'model path absent from save');
  assert((await api('state')).jobs.length===0,'save created no job');
  change('pub-seed','7');change('pub-extra-edges','');
  $('pub-recipe-list').value='Print';$('pub-recipe-list').dispatchEvent(new Event('change'));
  $('pub-recipe-load').click();await wait(()=>$('pub-recipe-status').textContent.startsWith('Loaded Print'));
  assert($('pub-seed').value==='123'&&$('pub-extra-edges').value==='768','custom edge and seed survive load');
  assert($('pub-models').value==='PRIVATE_LOCAL_MODEL'&&$('pub-device').value==='cpu','local execution choices retained');
  assert($('pub-selected-count').textContent==='1 SELECTED','selection retained');
  $('pub-plan-button').click();await wait(()=>posts.some(p=>p.url==='/api/publish'));
  const plan=posts.find(p=>p.url==='/api/publish').body;
  assert(plan.plan_only&&plan.seed===123&&plan.recipe_name==='Print','real publishing preview receives recipe and selection');
  assert(!$('pub-review-quality').checked&&!$('pub-review-ack').checked,'no output approval created');
  $('pub-recipe-preview').click();await wait(()=>!$('pub-recipe-save').disabled);
  change('pub-seed','124');assert($('pub-recipe-save').disabled,'edits invalidate reviewed save');
  $('pub-recipe-preview').click();await wait(()=>!$('pub-recipe-save').disabled);
  const external=await api('recipes',{name:'Print',settings:{seed:125}});
  await api('recipes',{name:'Print',settings:external.settings,save:true,expected_revision:external.revision});
  $('pub-recipe-save').click();await wait(()=>!$('pub-recipe-error').hidden);
  assert($('pub-recipe-error').textContent.includes('RECIPE_LIBRARY_CHANGED'),'real concurrent save rejected');
  assert($('pub-seed').value==='124'&&$('pub-recipe-save').disabled,'conflict preserves draft and requires repreview');
  $('pub-recipe-reload').click();await wait(()=>!$('pub-recipe-reload').disabled);
  let release,held=false;
  window.fetch=async(url,options={})=>{const response=await fetchReal(url,options);if(url.startsWith('/api/recipes?')){held=true;await new Promise(resolve=>release=resolve);}return response;};
  $('pub-recipe-load').click();await wait(()=>held);change('pub-seed','999');release();
  await wait(()=>!$('pub-recipe-load').disabled);
  assert($('pub-seed').value==='999','late load cannot overwrite newer settings');
  window.fetch=async(url,options={})=>{if(url==='/api/recipes')throw Error('offline');return fetchReal(url,options);};
  $('pub-recipe-reload').click();await wait(()=>!$('pub-recipe-error').hidden);
  assert($('pub-seed').value==='999'&&$('pub-recipe-load').disabled,'offline reload retains edits and disables stale list');
  window.fetch=fetchReal;$('pub-recipe-reload').click();await wait(()=>!$('pub-recipe-reload').disabled);
  change('pub-recipe-name','../private');$('pub-recipe-preview').click();await wait(()=>!$('pub-recipe-error').hidden);
  assert($('pub-recipe-name').getAttribute('aria-invalid')==='true','invalid name is explained inline');
  change('pub-recipe-name','Print');$('pub-recipe-preview').click();await wait(()=>!$('pub-recipe-save').disabled);
  assert((await api('state')).jobs.length===0,'all tested recipe operations remain job-free');
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
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-recipes-'));
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
        const ready=await command('Runtime.evaluate',{expression:'!!window.RiposteSort',returnByValue:true});
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
      await command('Runtime.evaluate',{expression:"$('pub-recipes').scrollIntoView({block:'start'})"});
      const layout=await command('Runtime.evaluate',{expression:"({scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth})",returnByValue:true});
      assert.ok(layout.result.value.scroll<=layout.result.value.client+1,JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
    }
    await command('Runtime.evaluate',{expression:"$('pub-recipe-list').value='';$('pub-recipe-list').focus()"});
    const key=async(key,code,virtual)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual});};
    await key('ArrowDown','ArrowDown',40);
    const selected=await command('Runtime.evaluate',{expression:"$('pub-recipe-list').value==='Print'&&!$('pub-recipe-load').disabled",returnByValue:true});
    assert.equal(selected.result.value,true,'native keyboard selects the highlighted saved recipe');
    const pos=await command('Runtime.evaluate',{expression:"(()=>{const r=$('pub-recipe-list').getBoundingClientRect();return {x:r.right-14,y:r.top+r.height/2}})()",returnByValue:true});
    for(const type of ['mousePressed','mouseReleased'])await command('Input.dispatchMouseEvent',{type,...pos.result.value,button:'left',clickCount:1});
    await pause(100);
    if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],'native-select-open.png'),Buffer.from(shot.data,'base64'));}
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
    assert.ok(path.basename(profile).startsWith('riposte-recipes-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS recipes_browser')).catch(e=>{console.error(e);process.exitCode=1;});
