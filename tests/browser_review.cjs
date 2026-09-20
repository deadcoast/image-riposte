'use strict';
// Run the actual publication module and shared image loader. Only browser I/O is
// substituted, so tests choose when fetch and HTMLImageElement.decode settle.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const staticDir = path.join(__dirname, '../src/riposte/static');
const deferred = () => {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return {promise, resolve, reject};
};
const flush = () => new Promise(resolve => setImmediate(resolve));

function setup() {
  const images = [], decodes = [], decisions = [], workshops = [], revoked = [], notices = [], views = [];
  class Element {
    constructor(tag, id = '') {
      this.tagName = tag; this.id = id; this.children = []; this.dataset = {};
      this.value = ''; this.checked = false; this.disabled = false; this.open = false;
      this.attributes = {}; this.listeners = new Map(); this.textContent = '';
      this.classList = {add() {}, remove() {}, toggle() {}};
    }
    append(...children) { this.children.push(...children); }
    replaceChildren(...children) { this.children = children; }
    get options() { return this.children; }
    setAttribute(key, value) { this.attributes[key] = String(value); }
    removeAttribute(key) { delete this.attributes[key]; }
    get src() { return this.attributes.src || ''; }
    set src(value) { this.attributes.src = value; }
    addEventListener(event, handler) {
      if (!this.listeners.has(event)) this.listeners.set(event, []);
      this.listeners.get(event).push(handler);
    }
    fire(event) {
      this['on' + event]?.();
      for (const handler of this.listeners.get(event) || []) handler();
    }
    click() { if (!this.disabled) return this.onclick?.(); }
    showModal() { this.open = true; }
    close() {
      if (!this.open) return;
      this.open = false;
      // Native dialog close is queued; reopening before it fires is allowed.
      setImmediate(() => this.fire('close'));
    }
    decode() {
      if (!this.id.startsWith('pub-review-')) return Promise.resolve();
      const pending = {...deferred(), element: this, src: this.src};
      decodes.push(pending);
      return pending.promise;
    }
  }
  const elements = new Map();
  for (const match of fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8')
    .matchAll(/<([a-z][a-z0-9]*)\b[^>]*\bid="([^"]+)"/g)) {
    elements.set(match[2], new Element(match[1], match[2]));
  }
  const $ = id => { assert.ok(elements.has(id), 'HTML has ' + id); return elements.get(id); };
  $('pub-models').value = 'local-model';
  const size = new Element('input'); size.value = '1024'; size.checked = true;
  const item = id => ({id, status: 'READY_FOR_REVIEW', review: 'UNREVIEWED',
    relative: '2026/September/SML/' + id + '.png', date: '2026-09-17', width: 32, height: 32,
    quality: {max_channel_delta_255: 1, worst_tile_rmse_255: 0.1, delta_e76_p95: 0.2},
    transport: {rows: [{transform: 'jpeg85', rmse_255: 0.1, max_channel_delta_255: 1}]}});
  const batch = {id: 'batch', sequence: 1, items: [item('one'), item('two')],
    counts: {PENDING: 0, BLOCKED: 0, READY_FOR_REVIEW: 2, ACCEPTED: 0}};
  let urlSequence = 0;
  const context = vm.createContext({
    console, setTimeout, clearTimeout, AbortController,
    document: {getElementById: $, createElement: tag => new Element(tag), addEventListener() {},
      querySelectorAll: selector => selector.startsWith('.pub-sizes') ? [size] : []},
    window: {}, location: {hash: '', pathname: '/'}, URLSearchParams,
    sessionStorage: {getItem: () => 'test-session'}, history: {},
    URL: {createObjectURL: () => 'blob:preview-' + (++urlSequence),
      revokeObjectURL: url => revoked.push(url)},
    fetch: (url, options) => {
      if(url==='/static/recovery-catalog.json')return Promise.resolve({ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(staticDir,'recovery-catalog.json'),'utf8'))});
      assert.equal(options.headers['X-Riposte-Token'], 'test-session');
      if (url.includes('/image/') && url.includes('?view=')) {
        const pending = {...deferred(), url, options}; images.push(pending);
        return pending.promise;
      }
      if (url.endsWith('/review')) {
        const pending = {...deferred(), url, body: JSON.parse(options.body)};
        decisions.push(pending); return pending.promise;
      }
      if (url.includes('/workshop/')) {
        const pending = {...deferred(), url}; workshops.push(pending); return pending.promise;
      }
      if (url === '/api/publication/batch') return Promise.resolve({ok: true, json: async () => batch});
      if (url.includes('?thumb=true')) return Promise.resolve({ok: true, blob: async () => ({})});
      throw Error('Unexpected fetch ' + url);
    },
  });
  const source = fs.readFileSync(path.join(staticDir, 'app.js'), 'utf8');
  vm.runInContext(fs.readFileSync(path.join(staticDir, 'recovery.js'), 'utf8'), context);
  // Load the shared declarations and functions, without starting application polling.
  vm.runInContext(source.slice(0, source.indexOf('function shortName(')), context);
  vm.runInContext('toast = message => notices.push(message); error = (e,op) => notices.push(recovery.text(e.message,op||e.operation));',
    Object.assign(context, {notices}));
  context.setView = view => views.push(view);
  vm.runInContext(fs.readFileSync(path.join(staticDir, 'publish.js'), 'utf8'), context);
  async function start() {
    context.window.RipostePublish.onState({images: [], publications: [batch]});
    await flush();
  }
  function open(index = 0) { $('pub-outputs').children[index].children[0].click(); }
  function acknowledge() {
    $('pub-review-quality').checked = true; $('pub-review-ack').checked = true;
    $('pub-review-quality').fire('change');
  }
  async function fetchImages(start = 0) {
    for (const request of images.slice(start)) request.resolve({ok: true, blob: async () => ({})});
    await flush();
  }
  async function ready(start = 0) {
    await fetchImages(start);
    for (const pending of decodes) pending.resolve();
    await flush();
  }
  function result(index = 0, accepted = true) {
    const response = structuredClone(batch);
    response.items[index].review = accepted ? 'ACCEPTED' : 'REJECTED';
    response.counts.ACCEPTED = Number(accepted);
    return {ok: true, json: async () => response};
  }
  return {$, context, images, decodes, decisions, workshops, revoked, notices, views, start, open,
    acknowledge, fetchImages, ready, result};
}

const scenarios = {
  async approval_waits_for_decode(t) {
    t.open(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true, 'approval waits for pixels');
    await t.$('pub-review-accept').onclick();
    assert.equal(t.decisions.length, 0, 'handler also enforces readiness');
    await t.fetchImages();
    t.decodes[0].resolve(); await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true, 'both images must decode');
    t.decodes[1].resolve(); await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, false);
    const pending = t.$('pub-review-accept').click();
    assert.deepEqual(t.decisions[0].body, {item_ids: ['one'], decision: 'ACCEPTED',
      visual_accepted: true, acknowledge_unverified: true});
    t.decisions[0].resolve(t.result()); await pending;
    assert.equal(t.$('pub-review-dialog').open, false);
  },
  async failed_image_blocks_approval(t) {
    t.open(); t.images[0].resolve({ok: false});
    t.images[1].resolve({ok: true, blob: async () => ({})}); await flush();
    t.decodes.forEach(d => d.resolve()); await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
    assert.match(t.$('pub-review-help').textContent, /could not load/i);
  },
  async failed_decode_blocks_approval(t) {
    t.open(); await t.fetchImages();
    t.decodes[0].reject(Error('invalid PNG')); t.decodes[1].resolve();
    await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
    assert.equal(t.$('pub-review-clean').src, '');
  },
  async new_review_clears_old_pixels(t) {
    t.open(); await t.ready(); t.$('pub-review-close').click(); t.open(1);
    assert.equal(t.$('pub-review-clean').src, '');
    assert.equal(t.$('pub-review-candidate').src, '');
    await flush();
    assert.equal(t.$('pub-review-dialog').open, true, 'queued old close keeps new dialog');
    await t.ready(2); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, false);
  },
  async superseded_load_cannot_authorize(t) {
    t.open(); t.$('pub-review-view').value = 'jpeg85'; t.$('pub-review-view').fire('change');
    t.images[0].resolve({ok: true, blob: async () => ({})});
    t.images[1].resolve({ok: true, blob: async () => ({})}); await flush();
    t.decodes.forEach(d => d.resolve()); await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
    assert.equal(t.$('pub-review-candidate').src, '');
  },
  async original_pixels_required(t) {
    t.open(); t.$('pub-review-difference').click(); await t.ready(2); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true, 'difference is not the candidate');
    t.$('pub-review-difference').click(); await t.ready(4); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, false);
    t.$('pub-review-view').value = 'jpeg85'; t.$('pub-review-view').fire('change');
    assert.equal(t.$('pub-review-quality').checked, false, 'new view requires inspection');
    await t.ready(6); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, false, 'stress view follows original inspection');
  },
  async cached_preview_is_revalidated(t) {
    t.open(); await t.ready(); t.$('pub-review-close').click(); await flush(); t.open();
    assert.equal(t.images.length, 4, 'reopening revalidates both files at server');
    assert.ok(t.images.every(x => x.options.cache === 'no-store'));
    t.images[2].resolve({ok: false}); t.images[3].resolve({ok: false});
    await flush(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
  },
  async closed_review_cannot_submit(t) {
    t.open(); t.$('pub-review-close').click(); await t.ready(); t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
    await t.$('pub-review-reject').onclick();
    assert.equal(t.decisions.length, 0);
    assert.equal(t.$('pub-review-candidate').src, '');
  },
  async native_close_cancels_review(t) {
    t.open(); t.$('pub-review-dialog').close(); await flush(); await t.ready();
    t.acknowledge();
    assert.equal(t.$('pub-review-accept').disabled, true);
    assert.equal(t.$('pub-review-candidate').src, '');
  },
  async duplicate_decisions_blocked(t) {
    t.open(); await t.ready(); t.acknowledge();
    const first = t.$('pub-review-accept').onclick();
    const duplicate = t.$('pub-review-accept').onclick();
    const opposite = t.$('pub-review-reject').onclick();
    assert.equal(t.decisions.length, 1, 'only one decision can be in flight');
    assert.equal(t.$('pub-review-view').disabled, true);
    t.decisions[0].resolve(t.result()); await Promise.all([first, duplicate, opposite]);
  },
  async old_decision_keeps_new_review_open(t) {
    t.open(); await t.ready(); t.acknowledge();
    const pending = t.$('pub-review-accept').click();
    t.$('pub-review-close').click(); await flush(); t.open(1); await t.ready(2);
    t.decisions[0].resolve(t.result()); await pending;
    assert.equal(t.$('pub-review-dialog').open, true, 'old decision cannot dismiss next image');
    assert.match(t.$('pub-review-title').textContent, /two.png/);
    t.acknowledge(); assert.equal(t.$('pub-review-accept').disabled, false);
  },
  async failed_decision_can_retry(t) {
    t.open(); await t.ready(); t.acknowledge();
    const pending = t.$('pub-review-accept').click();
    t.decisions[0].reject(Error('offline')); await pending;
    assert.equal(t.$('pub-review-dialog').open, true);
    assert.equal(t.$('pub-review-accept').disabled, false);
    const retry = t.$('pub-review-accept').click();
    assert.equal(t.decisions.length, 2);
    t.decisions[1].resolve(t.result()); await retry;
  },
  async rejection_without_images(t) {
    t.open();
    const pending = t.$('pub-review-reject').click();
    assert.equal(t.decisions.length, 1);
    assert.equal(t.decisions[0].body.decision, 'REJECTED');
    t.decisions[0].resolve(t.result(0, false)); await pending;
    assert.equal(t.$('pub-review-dialog').open, false);
  },
  async same_path_load_race(t) {
    const image = t.$('pub-review-clean'), url = 'publication/batch/image/one/clean?view=identity';
    const first = t.context.loadImage(image, url, {fresh: true});
    const second = t.context.loadImage(image, url, {fresh: true});
    assert.equal(t.images.length, 2, 'fresh calls are independently validated');
    t.images[1].resolve({ok: true, blob: async () => ({})}); await flush();
    const wanted = image.src; t.decodes[0].resolve(); assert.equal(await second, true);
    t.images[0].resolve({ok: true, blob: async () => ({})});
    assert.equal(await first, false); assert.equal(image.src, wanted);
  },
  async late_decode_keeps_current_image(t) {
    const image = t.$('pub-review-clean');
    const first = t.context.loadImage(image, 'publication/batch/image/one/clean?view=identity', {fresh: true});
    await t.fetchImages();
    const second = t.context.loadImage(image, 'publication/batch/image/two/clean?view=identity', {fresh: true});
    await t.fetchImages(1); t.decodes[1].resolve(); assert.equal(await second, true);
    const wanted = image.src;
    t.decodes[0].reject(Error('old decode aborted')); assert.equal(await first, false);
    assert.equal(image.src, wanted);
  },
  async fresh_urls_are_released(t) {
    t.open(); await t.ready();
    const urls = [t.$('pub-review-clean').src, t.$('pub-review-candidate').src];
    t.$('pub-review-close').click(); await flush();
    for (const url of urls) assert.ok(t.revoked.includes(url), 'released ' + url);
  },
  async acknowledgements_required(t) {
    t.open(); await t.ready();
    await t.$('pub-review-accept').onclick(); assert.equal(t.decisions.length, 0);
    t.$('pub-review-quality').checked = true; t.$('pub-review-quality').fire('change');
    assert.equal(t.$('pub-review-accept').disabled, true);
    await t.$('pub-review-accept').onclick(); assert.equal(t.decisions.length, 0);
    t.$('pub-review-quality').checked = false; t.$('pub-review-ack').checked = true;
    await t.$('pub-review-accept').onclick(); assert.equal(t.decisions.length, 0);
  },
  async stale_receipt_is_not_success(t) {
    t.open(); await t.ready(); t.acknowledge();
    const pending = t.$('pub-review-accept').click();
    const response = await t.result().json(); response.items[0].review = 'STALE';
    t.decisions[0].resolve({ok: true, json: async () => response}); await pending;
    assert.match(t.notices.at(-1), /not approved/i);
    assert.equal(t.$('pub-review-dialog').open, false);
  },
  async old_workshop_keeps_new_review_open(t) {
    t.open(); const pending = t.$('pub-workshop').click();
    await t.$('pub-workshop').onclick(); assert.equal(t.workshops.length, 1);
    t.$('pub-review-close').click(); await flush(); t.open(1);
    t.workshops[0].resolve({ok: true, json: async () => ({id: 'trial', image_id: 'master'})});
    await pending;
    assert.equal(t.$('pub-review-dialog').open, true); assert.deepEqual(t.views, []);
  },
  async workshop_handoff(t) {
    t.open(); const pending = t.$('pub-workshop').click();
    t.workshops[0].resolve({ok: true, json: async () => ({id: 'trial', image_id: 'master'})});
    await pending;
    assert.equal(t.$('pub-review-dialog').open, false); assert.deepEqual(t.views, ['lab']);
    assert.equal(vm.runInContext('state.trial.id', t.context), 'trial');
  },
};

async function nativeBrowser() {
  const http = require('node:http'), os = require('node:os');
  const {spawn} = require('node:child_process');
  const pause = ms => new Promise(resolve => setTimeout(resolve, ms));
  const item = {id: 'one', status: 'READY_FOR_REVIEW', review: 'UNREVIEWED',
    relative: '2026/September/SML/one.png', date: '2026-09-17', width: 1, height: 1,
    quality: {max_channel_delta_255: 1, worst_tile_rmse_255: 0.1, delta_e76_p95: 0.2}};
  const batch = {id: 'batch', sequence: 1, items: [item],
    counts: {PENDING: 0, BLOCKED: 0, READY_FOR_REVIEW: 1, ACCEPTED: 0}};
  const probe = `
    (async()=>{
      const assert=(ok,message)=>{if(!ok)throw Error(message);};
      const wait=async test=>{for(let n=0;n<100;n++){if(test())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out: '+test);};
      const held=[],fetchImage=window.fetch;let broken=false;
      window.fetch=(url,options)=>url.includes('?view=')?new Promise(resolve=>held.push(()=>resolve(broken?new Response('invalid png',{headers:{'Content-Type':'image/png'}}):fetchImage(url,options)))):fetchImage(url,options);
      window.RipostePublish.onState({images:[],publications:[${JSON.stringify(batch)}]});
      await wait(()=>document.querySelector('#pub-outputs button'));
      document.querySelector('#pub-outputs button').click();
      assert($('pub-review-dialog').open,'native dialog opened');
      assert($('pub-review-quality').disabled,'acknowledgement disabled during fetch');
      $('pub-review-quality').checked=true;$('pub-review-ack').checked=true;$('pub-review-quality').dispatchEvent(new Event('change'));
      assert($('pub-review-accept').disabled,'no premature approval');
      held.splice(0).forEach(release=>release());
      await wait(()=>!$('pub-review-quality').disabled);
      assert($('pub-review-clean').naturalWidth===1&&$('pub-review-candidate').naturalWidth===1,'real PNG decode');
      assert(!$('pub-review-quality').checked,'premature acknowledgement reset');
      $('pub-review-quality').click();$('pub-review-ack').checked=true;$('pub-review-ack').dispatchEvent(new Event('change'));
      assert(!$('pub-review-accept').disabled,'loaded pixels allow acknowledged approval');
      $('pub-review-dialog').close();await wait(()=>$('pub-review-reject').disabled);
      assert(!$('pub-review-candidate').getAttribute('src'),'native close releases pixels');
      document.querySelector('#pub-outputs button').click();
      assert(held.length===2,'reopening fetches current files');
      broken=true;held.splice(0).forEach(release=>release());
      await wait(()=>$('pub-review-help').textContent.includes('Could not load'));
      assert($('pub-review-accept').disabled,'real decode error blocks approval');
      assert(!$('pub-review-reject').disabled,'rejection remains available');
      document.getElementById('native-proof').textContent='PASS';
    })().catch(error=>{document.getElementById('native-proof').textContent=error.stack;});
  `;
  const png = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jG3sAAAAASUVORK5CYII=', 'base64');
  const app = fs.readFileSync(path.join(staticDir, 'app.js'), 'utf8');
  const html = fs.readFileSync(path.join(staticDir, 'index.html'), 'utf8')
    .replace('</body>', '<output id="native-proof">PENDING</output><script defer src="/probe.js"></script></body>');
  const server = http.createServer((request, response) => {
    const url = request.url;
    if (url === '/') {response.setHeader('Content-Type', 'text/html; charset=utf-8'); response.end(html);}
    else if (url === '/static/app.js') {response.setHeader('Content-Type', 'text/javascript'); response.end(app.slice(0, app.indexOf('function shortName(')));}
    else if (url === '/static/publish.js') {response.setHeader('Content-Type', 'text/javascript'); response.end(fs.readFileSync(path.join(staticDir, 'publish.js')));}
    else if (url === '/static/recovery.js' || url === '/static/recovery-catalog.json') {response.setHeader('Content-Type',url.endsWith('.js')?'text/javascript':'application/json');response.end(fs.readFileSync(path.join(staticDir,path.basename(url))));}
    else if (url === '/probe.js') {response.setHeader('Content-Type', 'text/javascript'); response.end(probe);}
    else if (url === '/api/publication/batch') {response.setHeader('Content-Type', 'application/json'); response.end(JSON.stringify(batch));}
    else if (url.startsWith('/api/publication/batch/image/')) {response.setHeader('Content-Type', 'image/png'); response.end(png);}
    else {response.statusCode = 404; response.end();}
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const tempRoot = fs.realpathSync(os.tmpdir());
  const profile = fs.mkdtempSync(path.join(tempRoot, 'riposte-browser-review-'));
  const browser = spawn(process.argv[3], [
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
    await command('Page.navigate', {url: 'http://127.0.0.1:' + server.address().port + '/'});
    let observed;
    for (let n = 0; n < 200; n++) {
      const response = await command('Runtime.evaluate', {expression: "document.getElementById('native-proof')?.textContent", returnByValue: true});
      observed = response.result.value;
      if (observed && observed !== 'PENDING') break;
      await pause(25);
    }
    assert.equal(observed, 'PASS', 'native browser result: ' + observed);
  } finally {
    if (socket?.readyState === WebSocket.OPEN) {
      await command('Browser.close').catch(() => {}); socket.close();
    }
    for (let n = 0; n < 100 && browser.exitCode === null; n++) await pause(20);
    if (browser.exitCode === null) browser.kill();
    await new Promise(resolve => server.close(resolve));
    // Only remove the unique temporary browser profile created by this process.
    assert.equal(path.dirname(fs.realpathSync(profile)), tempRoot);
    assert.ok(path.basename(profile).startsWith('riposte-browser-review-'));
    fs.rmSync(profile, {recursive: true, force: true, maxRetries: 5, retryDelay: 100});
  }
}

(async () => {
  if (process.argv[2] === 'native_browser') {
    await nativeBrowser(); console.log('PASS native_browser'); return;
  }
  const t = setup(); await t.start();
  await scenarios[process.argv[2]](t);
  console.log('PASS ' + process.argv[2]);
})().catch(error => { console.error(error); process.exitCode = 1; });
