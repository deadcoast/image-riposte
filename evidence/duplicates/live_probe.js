// Actual authenticated application API and engine; no fetch, controller or model mocks.
(async()=>{
  const assert=(ok,message)=>{if(!ok)throw Error(message);};
  const wait=async test=>{for(let n=0;n<600;n++){if(test())return;await new Promise(r=>setTimeout(r,25));}throw Error('Timed out: '+test);};
  await wait(()=>!refreshing);
  document.querySelector('[data-view="duplicates"]').click();$('dup-scan').click();
  await wait(()=>$('dup-status').textContent.startsWith('Scan complete'));
  await wait(()=>$('dup-list').querySelectorAll('button').length>=3);
  assert($('dup-counts').textContent.includes('CLOSELY RELATED'),'classifications from actual scan');
  $('dup-label').value='MAYBE DUPLICATE';$('dup-label').dispatchEvent(new Event('change'));
  await wait(()=>$('dup-list').querySelector('button'));
  assert($('dup-list').textContent.includes('MAYBE DUPLICATE'),'actual filter');
  $('dup-list').querySelector('button').click();
  await wait(()=>$('dup-detail').querySelectorAll('img').length===2);
  await wait(()=>[...$('dup-detail').querySelectorAll('img')].every(img=>img.complete&&img.naturalWidth>1));
  assert($('dup-detail').textContent.includes('structural 32px'),'actual measured matching evidence');
  const jobs=(await api('state')).jobs;const report=jobs.find(job=>job.result?.mode==='DUPLICATE_SCAN').result;
  const exported=await api('duplicates/'+report.scan_id+'/export?format=json');
  assert(exported.sources.length===6&&exported.findings.length>=3,'full export matches source inventory');
  assert(exported.counts.DUPLICATE>=1&&exported.counts['MAYBE DUPLICATE']>=1&&exported.counts['CLOSELY RELATED']>=1,'all three real classifications');
  $('native-proof').textContent='PASS';
})().catch(e=>{$('native-proof').textContent='FAIL '+e.stack;});
