// Shipping HTML, CSS and JavaScript in real Chromium; network fixtures isolate UI consent.
'use strict';
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const http=require('node:http'),os=require('node:os');
const {spawn}=require('node:child_process');
const staticDir=path.join(__dirname,'../src/riposte/static');
const pause=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function main(){
  const html=fs.readFileSync(path.join(staticDir,'index.html'),'utf8').replace('</body>','<output id="native-proof">PENDING</output><script defer src="/probe.js"></script></body>');
  const probe=fs.readFileSync(path.join(__dirname,process.env.RIPOSTE_DUPLICATE_LIVE?'../evidence/duplicates/live_probe.js':'duplicate_probe.js'),'utf8');
  const server=http.createServer((request,response)=>{
    const url=request.url;
    if(url==='/'){response.setHeader('Content-Type','text/html; charset=utf-8');response.end(html);}
    else if(url==='/probe.js'){response.setHeader('Content-Type','text/javascript');response.end(probe);}
    else if(url.startsWith('/static/')&&/^[a-z.-]+$/.test(url.slice(8))){const file=path.join(staticDir,url.slice(8));if(!fs.existsSync(file)){response.writeHead(404);response.end();return;}response.setHeader('Content-Type',url.endsWith('.js')?'text/javascript':'text/css');response.end(fs.readFileSync(file));}
    else {response.setHeader('Content-Type','application/json');response.end(JSON.stringify(url==='/api/state'?{images:[],trials:[],jobs:[],publications:[]}:{}));}
  });
  await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
  const tempRoot = fs.realpathSync(os.tmpdir());
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-duplicates-'));
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
    await command('Page.navigate', {url: process.env.RIPOSTE_DUPLICATE_LIVE || 'http://127.0.0.1:' + server.address().port + '/'});
    if(process.env.RIPOSTE_DUPLICATE_LIVE){
      for(let n=0;n<200;n++){
        const ready=await command('Runtime.evaluate',{expression:'!!window.RiposteDuplicates',returnByValue:true});
        if(ready.result.value)break;await pause(25);
      }
      await command('Runtime.evaluate',{expression:`document.body.append(Object.assign(document.createElement('output'),{id:'native-proof',textContent:'PENDING'}));`+probe});
    }
    let observed;
    for (let n = 0; n < 600; n++) {
      const response = await command('Runtime.evaluate', {expression: "document.getElementById('native-proof')?.textContent", returnByValue: true});
      observed = response.result.value;
      if (observed && observed !== 'PENDING') break;
      await pause(25);
    }
    assert.equal(observed, 'PASS', 'native browser result: ' + observed);
    for (const [name,width,height] of [['wide',1100,900],['narrow',390,844]]) {
      await command('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
      await command('Emulation.setEmulatedMedia',{features:[{name:'prefers-reduced-motion',value:'reduce'}]});
      const layout=await command('Runtime.evaluate',{expression:`({viewport:innerWidth,scroll:document.documentElement.scrollWidth,client:document.documentElement.clientWidth,visible:!document.getElementById('duplicates-view').hidden})`,returnByValue:true});
      assert.ok(layout.result.value.visible && layout.result.value.scroll<=layout.result.value.client+1, JSON.stringify(layout.result.value));
      if(process.argv[3]){const shot=await command('Page.captureScreenshot',{format:'png'});fs.writeFileSync(path.join(process.argv[3],name+'.png'),Buffer.from(shot.data,'base64'));}
      if(process.argv[3]){
        await command('Runtime.evaluate',{expression:"document.getElementById('dup-detail').scrollIntoView({block:'start'})"});
        await pause(100);
        const shot=await command('Page.captureScreenshot',{format:'png'});
        fs.writeFileSync(path.join(process.argv[3],name+'-review.png'),Buffer.from(shot.data,'base64'));
        await command('Runtime.evaluate',{expression:'window.scrollTo(0,0)'});
      }
    }
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-duplicates-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}
main().then(()=>console.log('PASS duplicate_browser')).catch(e=>{console.error(e);process.exitCode=1;});
