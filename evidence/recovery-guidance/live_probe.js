// Real authenticated local API and filesystem. No network or controller stubs.
(async()=>{
  const assert=(ok,message)=>{if(!ok)throw Error(message);};
  const wait=async test=>{for(let n=0;n<1500;n++){if(test())return;await new Promise(r=>setTimeout(r,20));}throw Error('Timed out: '+test);};
  const rows=()=>[...document.querySelectorAll('.category-row')];
  const field=(row,key)=>row.querySelector(`[data-field="${key}"]`);
  const edit=(row,key,value)=>{const input=field(row,key);input.value=value;input.dispatchEvent(new Event('input',{bubbles:true}));};
  const inspect=async()=>{$('run-plan').click();await wait(()=>$('sort-status').textContent.startsWith('Review the destinations'));};
  await wait(()=>!refreshing);
  $('scan').focus();$('scan').click();$('date-mode').value='modified';$('date-mode').dispatchEvent(new Event('input',{bubbles:true}));
  $('sort-categories').click();await wait(()=>$('category-choice-status').textContent.startsWith('0 saved'));
  await inspect();assert(state.plan,'no rules still produces a usable preview');
  assert(document.querySelectorAll('.category-assignment').length===50,'live folder uses bounded pages');
  assert(!$('category-destinations').textContent.includes('_float_'),'float storage omitted');
  $('category-editor').open=true;$('category-add').click();
  edit(rows()[0],'label','Hockey');field(rows()[0],'label').dispatchEvent(new Event('blur'));
  edit(rows()[0],'terms','hockey\ngoalie');edit(rows()[0],'exclusions','street hockey');edit(rows()[0],'priority','10');
  $('category-add').click();edit(rows()[1],'label','City');field(rows()[1],'label').dispatchEvent(new Event('blur'));edit(rows()[1],'terms','city\ntown');
  assert(field(rows()[0],'slug').value==='hockey','suggested stable folder');
  $('category-review').click();await wait(()=>!$('category-save').disabled);
  assert((await api('category-rules')).rules.categories.length===0,'review never saves');
  $('category-save').click();await wait(()=>$('category-review-result').textContent.startsWith('Saved.'));
  const hockey=rows().find(row=>field(row,'slug').value==='hockey');edit(hockey,'label','Ice hockey');
  assert(field(hockey,'slug').value==='hockey','renaming preserves folder name');
  $('category-review').click();await wait(()=>!$('category-save').disabled);$('category-save').click();await wait(()=>$('category-review-result').textContent.startsWith('Saved.'));
  const saved=(await api('category-rules')).rules.categories;
  assert(saved.find(r=>r.label==='Ice hockey').slug==='hockey','actual saved rename preserves identity');
  // A later rule writer invalidates the reviewed revision without losing the draft.
  edit(rows().find(row=>field(row,'slug').value==='hockey'),'priority','12');
  $('category-review').click();await wait(()=>!$('category-save').disabled);
  const current=await api('category-rules');
  const external=await api('category-rules',{categories:['City=city;town','Ice hockey=hockey;goalie'],slugs:['City=city','Ice hockey=hockey'],priorities:['City=1','Ice hockey=10'],exclusions:['Ice hockey=street hockey'],save:true,expected_revision:current.revision});
  let externalDone=false;
  for(let n=0;n<200;n++){externalDone=(await api('state')).jobs.some(j=>j.id===external.job_id&&j.state==='done');if(externalDone)break;await new Promise(r=>setTimeout(r,20));}
  assert(externalDone,'second writer completed');
  $('category-save').click();await wait(()=>!$('sort-error').hidden);
  assert($('sort-error').textContent.toLowerCase().includes('saved category rules changed')&&$('sort-error').textContent.includes('Copy any draft edits')&&$('sort-error').textContent.includes('Code: CATEGORY_RULES_CHANGED'),'real revision conflict is actionable');
  assert(field(rows().find(row=>field(row,'slug').value==='hockey'),'priority').value==='12','conflict retains unsaved input');
  $('category-load').click();assert(!$('category-reload-confirm').hidden,'reload requires deliberate draft discard');
  $('category-reload-confirmed').click();await wait(()=>$('category-review-result').textContent.startsWith('Loaded.'));
  $('category-editor').open=false;await inspect();
  const pick=(path,value)=>{const select=[...document.querySelectorAll('.category-assignment')].find(s=>s.dataset.source===path);assert(select&&!select.disabled,'file choice available: '+path);select.value=value;select.dispatchEvent(new Event('change'));};
  $('ack-remove').click();assert(!$('apply').disabled,'reviewed preview and explicit consent');
  pick('000-unknown.png','hockey');assert($('apply').disabled&&!$('ack-remove').checked,'assignment clears consent');
  pick('001-street-hockey.png','uncategorized');pick('002-hockey.png','auto');
  await inspect();const plan=JSON.parse($('plan-result').textContent);
  assert(plan.files.find(f=>f.source==='000-unknown.png').destination.includes('/hockey/'),'manual saved category destination');
  assert(plan.files.find(f=>f.source==='001-street-hockey.png').destination.includes('/uncategorized/'),'explicit uncategorized destination');
  assert(plan.files.find(f=>f.source==='002-hockey.png').category.slug==='hockey','automatic uses saved rule');
  assert(plan.files.length===58&&!plan.files.some(f=>f.source.includes('float')),'both float names excluded by actual planner');
  $('ack-remove').click();$('apply').click();await wait(()=>$('sort-status').textContent.startsWith('Sort: COMPLETE'));
  const after=await api('state');assert(after.images.length===58,'actual filesystem sort completes');
  $('sort-recovery').open=true;$('undo-preview').click();await wait(()=>$('undo-summary').textContent.startsWith('Restore 58'));
  assert($('undo-apply').disabled,'undo still needs consent');$('ack-undo').click();$('undo-apply').click();await wait(()=>$('undo-summary').textContent==='Undo: COMPLETE');
  assert((await api('state')).images.length===0,'undo removes managed outputs');
  $('sort-recovery').open=false;await inspect();$('category-editor').open=true;
  let refused=false;
  try {await api('organize',{apply:true});} catch(e) {
    refused=true;error(e,'sort');
    assert($('recovery-message').textContent.includes('Code: ACKNOWLEDGE_SOURCE_REMOVAL_REQUIRED'),'actual consent rejection retains code');
    assert($('recovery-message').textContent.includes('Inspect the exact destinations first'),'actual rejection gives safe next action');
    assert($('organize-dialog').contains($('recovery-notice'))&&!$('recovery-notice').hidden,'guidance is visible in the live modal');
    $('recovery-dismiss').click();
  }
  assert(refused,'consent cannot be bypassed');
  assert((await api('state')).images.length===0,'recovery guidance did not retry or write');
  $('native-proof').textContent='PASS';
})().catch(error=>{$('native-proof').textContent='FAIL '+error.stack;});
