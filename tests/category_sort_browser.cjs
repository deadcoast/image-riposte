// Shipping HTML, CSS and JavaScript in real Chromium; network fixtures isolate UI consent.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const http=require('node:http'),os=require('node:os');
const {spawn}=require('node:child_process');
const staticDir=path.join(__dirname,'../src/riposte/static');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main(){
  const html=fs.readFileSync(path.join(staticDir,'index.html'),'utf8').replace('</body>','<output id="native-proof">PENDING</output><script defer src="/probe.js"></script></body>');
  const probe=fs.readFileSync(process.env.RIPOSTE_SORT_PROBE||path.join(__dirname,process.env.RIPOSTE_SORT_LIVE?'../evidence/pacer-resumption/live_probe.js':'category_sort_probe.js'),'utf8');
  const server=http.createServer((request,response)=>{
    const url=request.url;
    if(url==='/'){response.setHeader('Content-Type','text/html; charset=utf-8');response.end(html);}
    else if(url==='/probe.js'){response.setHeader('Content-Type','text/javascript');response.end(probe);}
    else if(url.startsWith('/static/')&&/^[a-z.-]+$/.test(url.slice(8))){const file=path.join(staticDir,url.slice(8));if(!fs.existsSync(file)){response.writeHead(404);response.end();return;}response.setHeader('Content-Type',url.endsWith('.js')?'text/javascript':url.endsWith('.json')?'application/json':'text/css');response.end(fs.readFileSync(file));}
    else {response.setHeader('Content-Type','application/json');response.end(JSON.stringify(url==='/api/state'?{images:[],trials:[],jobs:[],publications:[]}:{}));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const tempRoot = fs.realpathSync(os.tmpdir());
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-category-sort-'));
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
      const timer = setTimeout(() => {pending.delete(id); reject(Error('Browser command timed out: ' + method));}, 5000);
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
    for (const [name,width,height] of [['wide',1100,900],['narrow',390,844]]) {
      await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
      await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
      const layout=await command('Runtime.evaluate',{expression:`(()=>{const d=document.getElementById('organize-dialog');d.scrollTop=0;return {viewport:innerWidth,width:d.getBoundingClientRect().width,scroll:d.scrollWidth,client:d.clientWidth}})()`,returnByValue:true});
      assert.ok(layout.result.value.width<=width && layout.result.value.scroll<=layout.result.value.client+1, JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
      const rowLayout=await command('Runtime.evaluate',{expression:`(()=>{const d=document.getElementById('organize-dialog'),r=document.querySelector('.category-row');if(!r)return null;document.getElementById('category-editor').open=true;r.scrollIntoView({block:'start'});const fields=[...r.querySelectorAll('input,textarea')];return {width:r.getBoundingClientRect().width,client:d.clientWidth,validLabels:fields.every(f=>f.closest('label')&&f.getAttribute('aria-describedby').split(' ').every(id=>document.getElementById(id)))}})()`,returnByValue:true});
      if(rowLayout.result.value){assert.ok(rowLayout.result.value.width<=layout.result.value.client);assert.equal(rowLayout.result.value.validLabels,true);}
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'-rules.png'),Buffer.from(shot.data,'base64'));}
      if(process.argv[3]){
        const notice=await command('Runtime.evaluate',{expression:`(()=>{error(new Error('WORKSPACE_LOCKED'),'sort');const n=$('recovery-notice'),r=n.getBoundingClientRect();return {visible:!n.hidden,left:r.left,right:r.right,bottom:r.bottom,scroll:n.scrollWidth,client:n.clientWidth,modal:$('organize-dialog').contains(n)}})()`,returnByValue:true});
        assert.ok(notice.result.value.visible&&notice.result.value.modal&&notice.result.value.left>=0&&notice.result.value.right<=width&&notice.result.value.bottom<=height&&notice.result.value.scroll<=notice.result.value.client+1,JSON.stringify(notice.result.value));
        const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'-recovery.png'),Buffer.from(shot.data,'base64'));
        await command('Runtime.evaluate',{expression:`$('recovery-dismiss').click()`});
      }
    }
    const key=async(key,code,virtual,modifiers=0)=>{await command('Input.dispatchKeyEvent',{type:'keyDown',key,code,windowsVirtualKeyCode:virtual,modifiers});await command('Input.dispatchKeyEvent',{type:'keyUp',key,code,windowsVirtualKeyCode:virtual,modifiers});};
    const focused=await command('Runtime.evaluate',{expression:`(()=>{const f=document.querySelector('.category-row [data-field="label"]');if(!f)return false;f.focus();return true})()`,returnByValue:true});
    if(focused.result.value){await key('Tab','Tab',9);const tabbed=await command('Runtime.evaluate',{expression:`document.activeElement.dataset.field==='slug'`,returnByValue:true});assert.equal(tabbed.result.value,true,'native Tab follows row labels to folder name');}
    const selectable=await command('Runtime.evaluate',{expression:`(()=>{const f=document.querySelector('.category-assignment:not(:disabled)');if(!f)return false;f.value='';f.scrollIntoView({block:'center'});f.focus();return true})()`,returnByValue:true});
    if(selectable.result.value){
      await key('ArrowDown','ArrowDown',40);
      const changed=await command('Runtime.evaluate',{expression:`document.activeElement.value==='auto'&&document.getElementById('apply').disabled&&!document.getElementById('ack-remove').checked`,returnByValue:true});assert.equal(changed.result.value,true,'native arrow choice revokes consent');
      const position=await command('Runtime.evaluate',{expression:`(()=>{const r=document.activeElement.getBoundingClientRect();return {x:r.right-14,y:r.top+r.height/2}})()`,returnByValue:true});
      await command('Input.dispatchMouseEvent',{type:'mousePressed',...position.result.value,button:'left',clickCount:1});
      await command('Input.dispatchMouseEvent',{type:'mouseReleased',...position.result.value,button:'left',clickCount:1});await pause(100);
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],'narrow-choice-open.png'),Buffer.from(shot.data,'base64'));}
      await key('Escape','Escape',27);
      const kept=await command('Runtime.evaluate',{expression:`document.getElementById('organize-dialog').open`,returnByValue:true});assert.equal(kept.result.value,true,'Escape closes select before dialog');
    }
    await command('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await command('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
    await pause(100);
    const focus=await command('Runtime.evaluate',{expression:`!document.getElementById('organize-dialog').open && document.activeElement.id==='scan'`,returnByValue:true});
    assert.equal(focus.result.value,true,'Escape closes and restores trigger focus');
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-category-sort-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS category_sort_browser')).catch(e=>{console.error(e);process.exitCode=1;});
