// Shipping DOM/JS in Chromium. Network fixtures test UI races; Python tests cover the real API.
(async()=>{
  const assert=(ok,message)=>{if(!ok)throw Error(message);};
  const wait=async test=>{for(let n=0;n<180;n++){if(test())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out: '+test);};
  clearInterval(pollTimer);await wait(()=>!refreshing);
  const jobs=[],posts=[],held=[];let serial=0,holdStart=false,holdFindings=false,previewFails=false,empty=false;
  const sources=[{id:'s1',relative:'original/artwork.png',media:'image',bytes:24000,width:320,height:240,sha256:'1'.repeat(64)},
    {id:'s2',relative:'copies/artwork <script>.png',media:'image',bytes:25000,width:320,height:240,sha256:'2'.repeat(64)}];
  const group={id:'g1',count:72,members:sources,offset:0,limit:50,representative:'s1'};
  const labels=['DUPLICATE','MAYBE DUPLICATE','CLOSELY RELATED'];
  const rows=labels.map((label,i)=>({id:'f'+i,label,confidence:i===0?100:97-i*4,basis:i===0?'NORMALIZED_PIXELS_EQUAL':'FULL_FRAME_SIMILARITY',left_source:'s1',right_source:'s2',left_path:sources[0].relative,right_path:sources[1].relative,member_count:72,media:'image'}));
  const report={mode:'DUPLICATE_SCAN',scan_id:'test-scan',root:'C:\\Artwork',checkpoint:'INCOMPLETE',counts:{DUPLICATE:1,'MAYBE DUPLICATE':1,'CLOSELY RELATED':1,files_discovered:74},issues:{counts:{UNREADABLE:1},examples:[{code:'UNREADABLE',path:'broken.png'}],omitted_examples:0},coverage:{exact:'Verified bytes and normalized pixels',video:'Five samples; no audio comparison'},confidence_policy:'100 means verified equality. Other scores are heuristic evidence, not probabilities.'};
  const png=Uint8Array.from(atob('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII='),c=>c.charCodeAt(0));
  window.fetch=async(url,options={})=>{
    const path=new URL(url,location.href),body=options.body?JSON.parse(options.body):null;let value={};
    if(body)posts.push({url,body});
    if(path.pathname==='/api/state')value={images:[],trials:[],publications:[],jobs};
    else if(path.pathname==='/api/duplicates'){
      if(holdStart)await new Promise(resolve=>held.push(resolve));
      const id='job-'+(++serial);jobs.push({id,state:'done',result:report});value={job_id:id};
    }else if(path.pathname.endsWith('/findings')){
      if(holdFindings)await new Promise(resolve=>held.push(resolve));
      const label=path.searchParams.get('label');let selected=label==='ALL'?rows:rows.filter(row=>row.label===label);
      if(empty)selected=[];value={total:selected.length,offset:0,rows:selected};
    }else if(path.pathname.includes('/findings/')){
      const row=rows.find(row=>path.pathname.endsWith(row.id));value={finding:{...row,metrics:{structural_32px:.97,colour_agreement:.99},left_time:null,right_time:null},left:group,right:row.id==='f0'?null:{...group,id:'g2',count:1,members:[sources[1]]},confidence_policy:report.confidence_policy};
    }else if(path.pathname.includes('/groups/'))value={...group,offset:50,members:[sources[1]]};
    else if(path.pathname.includes('/preview/')){
      assert(options.headers['X-Riposte-Token']!==undefined,'preview includes session header');
      if(previewFails)return new Response('{"code":"DUPLICATE_SOURCE_CHANGED"}',{status:400});
      return new Response(png,{headers:{'Content-Type':'image/png'}});
    }else if(path.pathname.endsWith('/export'))value=report;
    return new Response(JSON.stringify(value),{headers:{'Content-Type':'application/json'}});
  };
  document.querySelector('[data-view="duplicates"]').click();
  assert(!$('duplicates-view').hidden&&$('library-view').hidden,'independent navigation');
  assert(document.querySelector('.workflow').hidden,'separate from protection stages');
  assert(document.querySelector('.header-actions').hidden,'sorting CTA does not intrude into duplicate review');
  assert($('dup-status').textContent.includes('Ready'),'empty starting state');
  $('dup-max-files').value='0';$('dup-scan').click();
  assert(!$('dup-settings-error').hidden&&document.activeElement.id==='dup-max-files'&&!posts.length,'invalid settings remain inline and never start a scan');
  $('dup-max-files').value='100000';
  holdStart=true;$('dup-scan').click();await wait(()=>held.length===1);
  assert($('dup-scan').disabled&&$('dup-visual').disabled,'starting prevents duplicate submission');
  $('dup-scan').click();assert(posts.filter(post=>post.url==='/api/duplicates').length===1,'one scan request');
  held.shift()();holdStart=false;await wait(()=>$('dup-list').querySelectorAll('button').length===3);
  assert($('dup-status').textContent.includes('incomplete')&&$('dup-coverage').open,'partial result remains actionable');
  assert($('dup-counts').textContent.includes('CLOSELY RELATED'),'all classifications visible');
  document.body.dispatchEvent(new KeyboardEvent('keydown',{key:'/',bubbles:true}));
  assert(document.activeElement.id==='dup-search'&&state.view==='duplicates','search shortcut stays in duplicate review');
  $('dup-list').querySelector('button').click();await wait(()=>$('dup-detail').querySelectorAll('img').length===2);
  await wait(()=>[...$('dup-detail').querySelectorAll('img')].every(img=>img.complete&&img.naturalWidth));
  assert($('dup-detail').textContent.includes('<script>'),'paths rendered as literal text');
  assert(!$('dup-detail').querySelector('script'),'source names cannot inject markup');
  assert($('dup-detail').textContent.includes('structural 32px'),'comparison signals available');
  [...$('dup-detail').querySelectorAll('button')].find(button=>button.textContent==='Next members').click();
  await wait(()=>$('dup-detail').textContent.includes('51–51 of 72'));
  $('dup-label').value='MAYBE DUPLICATE';$('dup-label').dispatchEvent(new Event('change'));
  await wait(()=>$('dup-list').querySelectorAll('button').length===1);
  assert($('dup-list').textContent.includes('MAYBE DUPLICATE'),'classification filter');
  previewFails=true;$('dup-list').querySelector('button').click();await wait(()=>$('dup-detail').textContent.includes('source changed'));
  assert(!$('dup-detail').querySelector('img[src]'),'stale preview clears pixels');
  empty=true;$('dup-search').value='missing';$('dup-search').dispatchEvent(new Event('input'));
  await wait(()=>$('dup-list').textContent.includes('No findings'));
  assert($('dup-next').disabled&&$('dup-prev').disabled,'empty pagination disabled');
  // A slow old response cannot repopulate the list after a newer filter.
  empty=false;holdFindings=true;$('dup-search').value='old';$('dup-search').dispatchEvent(new Event('input'));await wait(()=>held.length===1);
  $('dup-search').value='new';$('dup-search').dispatchEvent(new Event('input'));await wait(()=>held.length===2);
  held.pop()();await wait(()=>$('dup-list').querySelectorAll('button').length===1);
  empty=true;held.shift()();await new Promise(r=>setTimeout(r,50));
  assert($('dup-list').querySelectorAll('button').length===1,'obsolete response ignored');
  holdFindings=false;empty=false;previewFails=false;$('dup-search').value='';$('dup-label').value='ALL';$('dup-label').dispatchEvent(new Event('change'));
  await wait(()=>$('dup-list').querySelectorAll('button').length===3);
  $('dup-list').querySelector('button').click();await wait(()=>$('dup-detail').querySelectorAll('img').length===2);
  await wait(()=>[...$('dup-detail').querySelectorAll('img')].every(img=>img.complete&&img.naturalWidth));
  assert(posts.every(post=>!post.url.includes('organize')),'finder never starts sorting');
  $('native-proof').textContent='PASS';
})().catch(e=>{$('native-proof').textContent='FAIL '+e.stack;});
