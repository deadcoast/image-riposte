'use strict';
// The sorting dialog owns its draft and consent; app.js owns transport and jobs.
window.RiposteSort = (() => {
  let revision = 0, rulesRevision = 0, pending = false, writing = false, awaitingJob = false;
  let preview = null, undo = null, draft = null;
  const requests = new Map();
  const ruleFields = ['category-groups','category-exclusions','category-priorities','category-slugs','category-clear'];
  const inputFields = ['date-mode','discard-sidecars','sort-categories','category-assignments'];
  const buttons = ['run-plan','apply','category-load','category-review','category-save','category-discover','undo-preview','undo-apply'];
  const lines = id => $(id).value.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
  const options = () => ({date_mode:$('date-mode').value,discard_sidecars:$('discard-sidecars').checked,
    categories:$('sort-categories').checked,assignments:$('sort-categories').checked?lines('category-assignments'):[]});
  const ruleOptions = () => $('category-clear').checked ? {categories:[],exclusions:[],priorities:[],slugs:[],clear:true,review:true} :
    {categories:lines('category-groups'),exclusions:lines('category-exclusions'),
     priorities:lines('category-priorities'),slugs:lines('category-slugs'),clear:false,review:true};
  function status(text) {$('sort-status').textContent=text;}
  function fail(e) {
    const copy = {CATEGORY_PREVIEW_CHANGED:'Files, rules or destinations changed. Inspect again before applying.',
      SORT_PREVIEW_CHANGED:'Files, destinations or settings changed. Inspect again before applying.',
      SORT_PREVIEW_REQUIRED:'Inspect files and destinations, then confirm that preview before applying.',
      CATEGORY_RULES_CHANGED:'The saved rules changed. Load them and review your replacement again.',
      CATEGORY_ASSIGNMENT_INVALID:'Check manual assignments: one existing source path=category-slug per line.',
      CATEGORY_RULES_INVALID:'Check each rule: Label=keyword;alias. Clear all rules only with the explicit checkbox.',
      CATEGORY_DRAFT_REQUIRED:'Enter category rules, or select Clear all saved rules.',
      ACKNOWLEDGE_SOURCE_REMOVAL_REQUIRED:'Confirm the displayed sort before applying.'};
    const area=$('sort-error');area.textContent=copy[e.message]||('The operation could not finish: '+String(e.message||'request failed').replaceAll('_',' ').toLowerCase()+'. Your draft is retained. Review the details and retry.');
    area.hidden=false;area.focus();
  }
  function updateDisabled() {
    const busy=pending||!!busyJob;
    for(const id of buttons)$(id).disabled=busy;
    for(const button of document.querySelectorAll('.sort-suggestion button'))button.disabled=busy;
    $('apply').disabled=busy||!preview?.ready||!preview?.plan_id||!$('ack-remove').checked;
    $('category-save').disabled=busy||!draft;
    $('undo-apply').disabled=busy||!undo?.ready||!$('ack-undo').checked;
    for(const id of [...inputFields,...ruleFields,'category-min-count'])$(id).disabled=writing;
    $('organize-dialog').setAttribute('aria-busy',String(busy));
  }
  function invalidate() {
    revision++;preview=null;state.plan=false;$('ack-remove').checked=false;
    status('Settings changed. Inspect again before applying.');updateDisabled();
  }
  function ruleChanged() {rulesRevision++;draft=null;invalidate();$('category-review-result').textContent='Review this draft before saving.';}
  async function request(endpoint, body, kind) {
    if(pending||busyJob)return;
    const generation=revision;pending=true;awaitingJob=true;writing=kind==='apply'||kind==='restore';
    $('sort-error').hidden=true;status(kind==='plan'?'Inspecting files and exact destinations…':'Working…');updateDisabled();
    try {
      const result=await api(endpoint,body);
      requests.set(result.job_id,{generation,kind});busyJob=result.job_id;awaitingJob=false;
      await refresh();
    } catch(e) {writing=false;fail(e);} finally {pending=false;awaitingJob=false;updateDisabled();}
  }
  function destinations(result) {
    const area=$('category-destinations');area.replaceChildren();
    const counts=result.counts||{};
    if(result.category_sorting)area.append(el('p','',`${counts.without_category_files||0} without category · ${counts.ambiguous_files||0} ambiguous. Categories are optional; unmatched files use date/media/size, and existing categories stay.`));
    if(result.corpus)area.append(el('p','',`Local filename patterns: ${result.corpus.status.replaceAll('_',' ').toLowerCase()} · ${result.corpus.normalized_families} distinct title families. Pattern scores are lexical evidence, not accuracy estimates.`));
    for(const item of result.files||[]) {
      const row=el('article','sort-file');row.append(el('strong','',item.source));
      if(result.category_sorting) {
        row.append(el('p','', 'Original title: '+(item.original_filename||'unknown')));
        row.append(el('p','',(item.category?.label||'No category; standard date/media/size')+' · '+(item.category_source==='PRESERVED'?'Existing category retained':item.matched_terms?.join(', ')||item.match_status||item.action||'')));
        if(item.category_source==='CORPUS')row.append(el('p','',`Local filename pattern · support ${item.corpus_match.score.toFixed(2)} · margin ${item.corpus_match.margin.toFixed(2)}`));
      } else row.append(el('p','',item.action||'Blocked'));
      row.append(el('p','sort-destination',item.destination||item.error||item.action||'Blocked'));area.append(row);
    }
  }
  function completed(job) {
    const context=requests.get(job.id);if(!context)return false;
    requests.delete(job.id);writing=false;
    if(!['done','incomplete'].includes(job.state)){preview=null;undo=null;fail(new Error(job.code));return true;}
    const result=job.result;
    if(context.kind==='plan') {
      if(context.generation!==revision){status('This inspection is outdated. Inspect again with the current settings.');return true;}
      preview=result;state.plan=!!result.ready;$('plan-result').textContent=JSON.stringify(result,null,2);planSummary(result);destinations(result);
      status(result.ready?'Review the destinations, then confirm to apply.':'Resolve the listed blockers, then inspect again.');
    } else if(context.kind==='undo') {
      undo=result;$('ack-undo').checked=false;
      $('undo-summary').textContent=result.ready?`Restore ${result.files_to_restore} original files and remove ${result.outputs_to_remove} sorted copies; restore the private category records.`:'Undo is blocked: '+Object.keys(result.blockers||{}).join(', ').replaceAll('_',' ');
    } else {
      invalidate();undo=null;$('ack-undo').checked=false;
      $('plan-result').textContent=JSON.stringify(result,null,2);
      status((context.kind==='restore'?'Undo':'Sort')+': '+result.checkpoint+'. '+(result.checkpoint==='COMPLETE'?'Inspect again before another sort.':'Review the report. Undo is available for recorded changes.'));
      if(context.kind==='restore')$('undo-summary').textContent='Undo: '+result.checkpoint;
      else {planSummary(result);state.audit=result;renderAuditBadge();}
    }
    return true;
  }
  async function rulesAction(kind) {
    if(pending||busyJob)return;
    const generation=rulesRevision, selection=ruleOptions(), reviewed=draft;
    if(kind==='save'&&!reviewed)return;
    pending=true;writing=kind==='save';$('sort-error').hidden=true;updateDisabled();
    $('category-review-result').textContent=kind==='save'?'Saving reviewed rules…':'Reading filename rules…';
    try {
      const result=await api('category-rules',kind==='load'?undefined:kind==='save'?{...reviewed.options,save:true,expected_revision:reviewed.revision}:selection);
      if(generation!==rulesRevision){$('category-review-result').textContent='The draft changed while reading. Review it again.';return;}
      if(kind==='load') {
        const rows=result.rules.categories;
        $('category-groups').value=rows.map(r=>r.label+'='+r.terms.join(';')).join('\n');
        $('category-exclusions').value=rows.filter(r=>r.exclusions.length).map(r=>r.label+'='+r.exclusions.join(';')).join('\n');
        $('category-priorities').value=rows.map(r=>r.label+'='+r.priority).join('\n');
        $('category-slugs').value=rows.map(r=>r.label+'='+r.slug).join('\n');$('category-clear').checked=false;draft=null;
      } else if(kind==='review') {
        if(result.status!=='DRAFT')throw new Error('CATEGORY_DRAFT_REQUIRED');
        draft={options:selection,revision:result.revision};
      } else {draft=null;rulesRevision++;invalidate();}
      const rows=result.rules.categories;
      $('category-review-result').textContent=(kind==='save'?'Saved. ':kind==='load'?'Loaded. ':'Reviewed replacement. ')+rows.length+' categories. '+
        rows.map(r=>r.label+' → '+r.slug).join('; ')+(result.review?' Matching titles: '+JSON.stringify(result.review.counts):'')+(kind==='save'?' Inspect destinations before sorting.':'');
    } catch(e) {draft=null;fail(e);} finally {pending=false;writing=false;updateDisabled();}
  }
  $('run-plan').onclick=()=>{invalidate();request('organize',options(),'plan');};
  $('apply').onclick=()=>{if(!preview?.ready||!preview?.plan_id||!$('ack-remove').checked)return;const current=preview;preview=null;state.plan=false;request('organize',{...options(),apply:true,acknowledge_source_removal:true,plan_id:current.plan_id},'apply');};
  for(const id of inputFields)$(id).oninput=()=>{if(id==='sort-categories')$('category-options').hidden=!$(id).checked;invalidate();};
  for(const id of ruleFields)$(id).oninput=ruleChanged;
  $('ack-remove').onchange=updateDisabled;$('ack-undo').onchange=updateDisabled;
  for(const kind of ['load','review','save'])$('category-'+kind).onclick=()=>rulesAction(kind);
  $('category-discover').onclick=async()=>{
    if(pending||busyJob)return;
    const count=Number($('category-min-count').value);
    if(!Number.isInteger(count)||count<1){$('category-min-count').setAttribute('aria-invalid','true');fail(new Error('Minimum count must be a positive whole number'));return;}
    $('category-min-count').removeAttribute('aria-invalid');pending=true;updateDisabled();
    $('category-suggestions').textContent='Discovering recurring filename terms…';
    try {
      const result=await api('categories',{min_count:count});const area=$('category-suggestions');area.replaceChildren();
      for(const group of result.corpus?.categories||[]) {
        const row=el('div','sort-suggestion');const button=el('button','secondary compact','Use group '+group.label);
        button.onclick=()=>{if(pending||busyJob)return;$('category-groups').value+=($('category-groups').value?'\n':'')+group.label+'='+group.terms.join(';');ruleChanged();};
        row.append(button,el('span','',`${group.support} distinct title families · ${group.terms.join(' · ')}`));area.append(row);
      }
      for(const item of result.candidates) {
        const row=el('div','sort-suggestion');const button=el('button','secondary compact','Use '+item.term);
        button.onclick=()=>{if(pending||busyJob)return;$('category-groups').value+=($('category-groups').value?'\n':'')+item.term+'='+item.term;ruleChanged();};
        row.append(button,el('span','',`${item.count} files · ${item.examples.join(' · ')}`));area.append(row);
      }
      if(!result.candidates.length&&!result.corpus?.categories?.length)area.textContent='No supported groups or terms meet this count. Sorting remains available without categories.';
      if(result.checkpoint!=='COMPLETE')area.append(el('p','sort-error','Some paths could not be read. These counts are incomplete.'));
    } catch(e){fail(e);}finally{pending=false;updateDisabled();}
  };
  $('undo-preview').onclick=()=>{undo=null;request('undo-sort',{},'undo');};
  $('undo-apply').onclick=()=>{if(!undo?.ready||!$('ack-undo').checked)return;const current=undo;undo=null;request('undo-sort',{apply:true,acknowledge_restore:true,sort_id:current.sort_id},'restore');};
  updateDisabled();
  return {completed,updateDisabled,deferCompletion:()=>awaitingJob};
})();
