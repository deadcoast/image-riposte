'use strict';
// The sorting dialog owns its draft and consent; app.js owns transport and jobs.
window.RiposteSort = (() => {
  let revision = 0, rulesRevision = 0, discoveryRevision = 0, pending = false, writing = false, awaitingJob = false;
  let preview = null, undo = null, draft = null;
  let dirty = false, rulesInitialized = false, rowSerial = 0, choiceRevision = null, choicesLoading = false, choicesGeneration = 0;
  let savedRules = [], displayed = null, filePage = 0;
  const assignments = new Map(), ruleRows = [];
  const pageSize = 50;
  const requests = new Map();
  const ruleFields = ['category-clear'];
  const inputFields = ['date-mode','discard-sidecars','sort-categories'];
  const buttons = ['run-plan','apply','category-load','category-review','category-save','category-discover','undo-preview','undo-apply'];
  const words = value => value.split(/\r?\n/).map(v=>v.trim()).filter(Boolean);
  const options = () => ({date_mode:$('date-mode').value,discard_sidecars:$('discard-sidecars').checked,
    categories:$('sort-categories').checked,assignments:$('sort-categories').checked?[...assignments].map(([path,slug])=>path+'='+slug):[]});
  const ruleOptions = () => $('category-clear').checked ? {categories:[],exclusions:[],priorities:[],slugs:[],clear:true,review:true} :
    {categories:ruleRows.map(r=>r.fields.label.value.trim()+'='+words(r.fields.terms.value).join(';')),
     exclusions:ruleRows.filter(r=>words(r.fields.exclusions.value).length).map(r=>r.fields.label.value.trim()+'='+words(r.fields.exclusions.value).join(';')),
     priorities:ruleRows.map(r=>r.fields.label.value.trim()+'='+r.fields.priority.value),
     slugs:ruleRows.map(r=>r.fields.label.value.trim()+'='+r.fields.slug.value.trim()),clear:false,review:true};
  // These checks provide immediate correction hints. The shared server parser remains authoritative.
  const fold = value => value.normalize('NFKC').toLowerCase().replaceAll('ß','ss').replaceAll('ς','σ').normalize('NFKC');
  const tokens = value => fold(value).match(/[\p{L}\p{N}][\p{L}\p{N}\p{M}]*/gu)||[];
  const reserved = /^(uncategorized|con|prn|aux|nul|com[1-9]|lpt[1-9])$/;
  function fieldError(row,key,message) {
    row.errors[key].textContent=message;row.errors[key].hidden=!message;
    if(message)row.fields[key].setAttribute('aria-invalid','true');else row.fields[key].removeAttribute('aria-invalid');
  }
  function validateRules(focus=false) {
    const clearing=$('category-clear').checked, labels=new Map(), slugs=new Map();
    for(const row of ruleRows)for(const key of Object.keys(row.fields))fieldError(row,key,'');
    if(!clearing)for(const row of ruleRows) {
      const f=row.fields, label=f.label.value.trim().normalize('NFKC'), slug=f.slug.value.trim();
      if(!label||[...label].length>80||/[=\p{C}]/u.test(label)||fold(label)==='uncategorized')fieldError(row,'label','Use a name of 1–80 characters, without = or control characters. Uncategorized is reserved.');
      if(!slug||[...slug].length>80||slug!==tokens(slug).join('-')||reserved.test(slug))fieldError(row,'slug','Use lowercase words separated by hyphens, up to 80 characters. Choose a non-reserved folder name.');
      for(const [key,value,map] of [['label',fold(label),labels],['slug',slug,slugs]]) {
        if(map.has(value)){fieldError(row,key,'Each category needs a unique '+(key==='slug'?'folder name.':'name.'));fieldError(map.get(value),key,'This '+(key==='slug'?'folder name':'name')+' is used by another category.');}else map.set(value,row);
      }
      const terms=words(f.terms.value), exclusions=words(f.exclusions.value);
      if((label+'='+terms.join(';')).length>4096)fieldError(row,'terms','Shorten this category to at most 4096 characters including its name and phrases.');
      for(const [key,values,required] of [['terms',terms,true],['exclusions',exclusions,false]]) {
        if(values.length>32||(required&&!values.length))fieldError(row,key,'Enter '+(required?'1–32':'up to 32')+' words or short phrases, one per line.');
        else if(values.some(v=>[...v].length>255||/[;\p{C}]/u.test(v)||!tokens(v).length||tokens(v).length>3||tokens(v).every(t=>/^\p{N}+$/u.test(t))))fieldError(row,key,'Use 1–3 words per phrase, one phrase per line, up to 255 characters. Numbers alone and semicolons are not supported.');
      }
      const matched=new Set(terms.map(v=>tokens(v).join(' ')));
      if(exclusions.some(v=>matched.has(tokens(v).join(' '))))fieldError(row,'exclusions','A matching phrase cannot also be excluded. Remove it from one list.');
      if(!/^-?\d{1,7}$/.test(f.priority.value)||Math.abs(Number(f.priority.value))>1000000)fieldError(row,'priority','Enter a whole number from -1000000 to 1000000. Higher priorities win.');
    }
    const area=$('category-row-error');area.textContent=!clearing&&!ruleRows.length?'Add a category, or explicitly choose Clear all saved rules.':'';area.hidden=!area.textContent;
    const first=$('category-rows').querySelector('[aria-invalid="true"]');
    if(focus){if(first)first.focus();else if(!area.hidden)$('category-add').focus();}
    return !first&&area.hidden;
  }
  function addRule(value={},focus=true) {
    if(ruleRows.length>=32){$('category-row-error').textContent='Up to 32 categories are supported. Edit or remove an existing category.';$('category-row-error').hidden=false;return;}
    const row={node:el('fieldset','category-row'),fields:{},errors:{}};
    const serial=++rowSerial;row.node.append(el('legend','','Category'));
    const grid=el('div','category-rule-grid');
    for(const [key,title,type,help] of [
      ['label','Category name','text','A display name; renaming it keeps the folder name.'],
      ['slug','Folder name','text','Stable name in the sorted path. Change it only to change the destination.'],
      ['terms','Matching words or phrases','textarea','One per line. Any match can select this category.'],
      ['exclusions','Exclude words or phrases','textarea','Optional, one per line. Any match rules this category out.'],
      ['priority','Priority','number','Higher numbers win. Ties still sort without a category.']]) {
      const label=el('label','',title), field=el(type==='textarea'?'textarea':'input',''),hint=el('span','field-help',help),error=el('span','sort-error','');
      field.id=`category-row-${serial}-${key}`;field.dataset.field=key;field.spellcheck=false;
      if(type==='textarea'){field.rows=3;field.className='resize-none';}else field.type=type;
      if(type==='number'){field.min='-1000000';field.max='1000000';field.step='1';}
      field.value=Array.isArray(value[key])?value[key].join('\n'):value[key]??(key==='priority'?'0':'');
      hint.id=field.id+'-help';error.id=field.id+'-error';error.hidden=true;
      field.setAttribute('aria-describedby',hint.id+' '+error.id);
      field.oninput=event=>{ruleChanged();if(!event.isComposing)validateRules();};
      field.addEventListener('compositionend',()=>validateRules());
      label.append(field,hint,error);grid.append(label);row.fields[key]=field;row.errors[key]=error;
    }
    row.fields.label.onblur=()=>{if(!row.fields.slug.value&&row.fields.label.value.trim()){row.fields.slug.value=tokens(row.fields.label.value).join('-');ruleChanged();validateRules();}};
    const remove=el('button','secondary compact','Remove category');remove.type='button';
    remove.onclick=()=>{if(writing)return;const index=ruleRows.indexOf(row);ruleRows.splice(index,1);row.node.remove();ruleChanged();validateRules();(ruleRows[index]?.fields.label||ruleRows[index-1]?.fields.label||$('category-add')).focus();};
    row.node.append(grid,remove);ruleRows.push(row);$('category-rows').append(row.node);
    if(focus){$('category-clear').checked=false;ruleChanged();row.fields.label.focus();}
    updateDisabled();return row;
  }
  function replaceRows(rows) {rulesInitialized=true;ruleRows.length=0;$('category-rows').replaceChildren();for(const row of rows)addRule(row,false);$('category-clear').checked=false;$('category-row-error').hidden=true;}
  async function loadChoices() {
    if(choicesLoading)return;
    const generation=choicesGeneration;
    choicesLoading=true;$('category-choice-retry').hidden=true;$('category-choice-status').textContent='Loading saved category choices…';updateDisabled();
    try {
      const result=await api('category-rules');if(generation!==choicesGeneration)return;
      savedRules=result.rules.categories;choiceRevision=result.revision;
      if(!rulesInitialized&&!dirty){replaceRows(savedRules);$('category-draft-state').textContent=savedRules.length?'Saved rules loaded · no unsaved changes.':'No saved categories. Sorting works without them; add a category only if needed.';}
      $('category-choice-status').textContent=savedRules.length+' saved categories. Unsaved rule edits are not used for sorting.';
      if(displayed?.rules_revision&&displayed.rules_revision!==choiceRevision)invalidate();
    } catch(e){if(generation===choicesGeneration){choiceRevision=null;$('category-choice-status').textContent='Category choices could not load. Sorting with current rules is still available.';$('category-choice-retry').hidden=false;}}
    finally {choicesLoading=false;if(displayed)renderFiles();updateDisabled();}
  }
  function status(text) {$('sort-status').textContent=text;}
  function fail(e,operation='sort') {
    const code=recovery.safeCode(e?.message),item=recovery.lookup(code,e?.operation||operation);
    const area=$('sort-error');area.textContent=recovery.text(code,e?.operation||operation);area.hidden=false;area.focus();
    if(['CATEGORY_RULES_INVALID','CATEGORY_DRAFT_INVALID','CATEGORY_SLUG_INVALID','CATEGORY_SLUG_DUPLICATE','CATEGORY_RULE_CONTRADICTION','CATEGORY_PRIORITY_INVALID'].includes(code)) {
      validateRules();const key=code.includes('SLUG')?'slug':code.includes('PRIORITY')?'priority':code.includes('CONTRADICTION')?'exclusions':'label';
      if(!$('category-rows').querySelector('[aria-invalid="true"]'))for(const row of ruleRows)fieldError(row,key,item.action);
      $('category-rows').querySelector('[aria-invalid="true"]')?.focus();
    }
  }
  function updateDisabled() {
    const busy=pending||!!busyJob;
    for(const id of buttons)$(id).disabled=busy;
    for(const button of document.querySelectorAll('.sort-suggestion button'))button.disabled=busy;
    $('apply').disabled=busy||!preview?.ready||!preview?.plan_id||!$('ack-remove').checked;
    $('category-save').disabled=busy||!draft;
    $('undo-apply').disabled=busy||!undo?.ready||!$('ack-undo').checked;
    for(const id of [...inputFields,...ruleFields,'category-min-count'])$(id).disabled=writing;
    for(const field of $('category-rows').querySelectorAll('input,textarea,button'))field.disabled=writing||$('category-clear').checked;
    $('category-add').disabled=writing||$('category-clear').checked||ruleRows.length>=32;
    $('category-reload-confirmed').disabled=busy;
    for(const field of $('category-destinations').querySelectorAll('select'))field.disabled=writing||choicesLoading||choiceRevision===null||!$('sort-categories').checked;
    $('category-choice-retry').disabled=choicesLoading||writing;
    $('category-choice-reset').hidden=!assignments.size;$('category-choice-reset').disabled=writing;
    $('organize-dialog').setAttribute('aria-busy',String(busy));
  }
  function invalidate() {
    revision++;preview=null;state.plan=false;$('ack-remove').checked=false;
    $('category-destinations').classList.add('sort-outdated');
    status('Settings changed. Inspect again before applying.');updateDisabled();
  }
  function ruleChanged() {rulesRevision++;draft=null;dirty=true;invalidate();$('category-draft-state').textContent='Unsaved draft · sorting still uses saved rules.';$('category-review-result').textContent='Review this draft before saving.';}
  async function request(endpoint, body, kind, extra = {}) {
    if(pending||busyJob)return;
    const context={generation:revision,rulesGeneration:rulesRevision,discoveryGeneration:discoveryRevision,kind,...extra};
    pending=true;awaitingJob=true;writing=['apply','restore','save'].includes(kind);
    $('sort-error').hidden=true;status(kind==='plan'?'Inspecting files and exact destinations…':'Working…');updateDisabled();
    try {
      const result=await api(endpoint,body);
      requests.set(result.job_id,context);busyJob=result.job_id;awaitingJob=false;
      await refresh();
    } catch(e) {writing=false;fail(e,kind);} finally {pending=false;awaitingJob=false;updateDisabled();}
  }
  function destinations(result) {
    displayed=result;filePage=0;renderFiles();
    $('category-destinations').classList.remove('sort-outdated');
    if(result.category_sorting&&(choiceRevision===null||result.rules_revision&&result.rules_revision!==choiceRevision))loadChoices();
  }
  function renderFiles() {
    if(!displayed)return;
    const result=displayed, files=result.files||[];
    filePage=Math.max(0,Math.min(filePage,Math.ceil(files.length/pageSize)-1));
    const area=$('category-destinations');area.replaceChildren();
    const counts=result.counts||{};
    if(result.category_sorting)area.append(el('p','',`${counts.without_category_files||0} without category · ${counts.ambiguous_files||0} ambiguous. Categories are optional; unmatched files use date/media/size, and existing categories stay.`));
    if(result.corpus)area.append(el('p','',`Local filename patterns: ${result.corpus.status.replaceAll('_',' ').toLowerCase()} · ${result.corpus.normalized_families} distinct title families. Pattern scores are lexical evidence, not accuracy estimates.`));
    if(!files.length)area.append(el('p','','No files were found for this inspection.'));
    for(const item of files.slice(filePage*pageSize,(filePage+1)*pageSize)) {
      const row=el('article','sort-file');row.append(el('strong','',item.source));
      if(result.category_sorting) {
        if(['AMBIGUOUS','ORIGINAL_TITLE_UNAVAILABLE','UNMATCHED'].includes(item.match_status))row.append(el('p','field-help',recovery.text(item.match_status,'sort')));
        row.append(el('p','', 'Original title: '+(item.original_filename||'unknown')));
        row.append(el('p','',(item.category?.label||'No category; standard date/media/size')+' · '+(item.category_source==='PRESERVED'?'Existing category retained':item.matched_terms?.join(', ')||item.match_status||item.action||'')));
        if(item.category_source==='CORPUS')row.append(el('p','',`Local filename pattern · support ${item.corpus_match.score.toFixed(2)} · margin ${item.corpus_match.margin.toFixed(2)}`));
        if(['IMAGE','VIDEO'].includes(item.kind)||(!item.kind&&item.destination)) {
          const label=el('label','','Category for this file'),select=el('select','category-assignment');select.dataset.source=item.source;
          select.setAttribute('aria-label','Category for '+item.source);
          for(const [value,text] of [['','Keep current choice'],['auto','Automatic — clear manual choice'],['uncategorized','Uncategorized — explicit folder'],...savedRules.filter(r=>r.slug!=='auto').map(r=>[r.slug,r.label+' · '+r.slug])]) {
            const option=el('option','',text);option.value=value;select.append(option);
          }
          const selected=assignments.get(item.source)||'',missing=selected&&!['auto','uncategorized',...savedRules.map(r=>r.slug)].includes(selected);
          if(missing){const option=el('option','','Unavailable category · '+selected);option.value=selected;select.append(option);select.setAttribute('aria-invalid','true');}
          select.value=selected;label.append(select);row.append(label);
          const hint=el('p','field-help',missing?'This category is no longer saved. Choose another option before inspecting.':'Current result: '+(item.category?.label||'No category; standard date/media/size'));
          hint.id='category-file-'+(filePage*pageSize+area.querySelectorAll('article').length)+'-help';select.setAttribute('aria-describedby',hint.id);row.append(hint);
          select.onchange=()=>{if(select.value)assignments.set(item.source,select.value);else assignments.delete(item.source);select.removeAttribute('aria-invalid');hint.textContent='Choice changed. Inspect again to update the destination.';invalidate();};
        }
      } else row.append(el('p','',item.action||'Blocked'));
      row.append(el('p','sort-destination',item.destination||item.error||item.action||'Blocked'));area.append(row);
    }
    $('category-pages').hidden=files.length<=pageSize;
    $('category-range').textContent=files.length?`${filePage*pageSize+1}–${Math.min(files.length,(filePage+1)*pageSize)} of ${files.length} files`:'';
    $('category-prev').disabled=filePage===0;$('category-next').disabled=(filePage+1)*pageSize>=files.length;
    updateDisabled();
  }
  function completed(job) {
    const context=requests.get(job.id);if(!context)return false;
    requests.delete(job.id);writing=false;$('sort-activity').hidden=true;
    if(['plan','undo','discover','review'].includes(context.kind) &&
       (context.generation!==revision || context.rulesGeneration!==rulesRevision ||
        (context.kind==='discover'&&context.discoveryGeneration!==discoveryRevision))) {
      status('This inspection is outdated. Inspect again with the current settings.');return true;
    }
    if(job.state==='cancelled') {
      preview=null;undo=null;state.plan=false;
      if(context.kind==='review')draft=null;
      if(context.kind==='discover')$('category-suggestions').textContent='Discovery cancelled. Change the count or try again.';
      if(context.kind==='review')$('category-review-result').textContent='Review cancelled. Your draft is retained.';
      status('Inspection cancelled. No files changed. Your settings are retained.');return true;
    }
    if(!['done','incomplete'].includes(job.state)){preview=null;undo=null;fail(new Error(job.code),context.kind);return true;}
    const result=job.result;
    if(['review','save'].includes(context.kind)) {
      try{acceptRules(context.kind,result,context.selection);}catch(e){draft=null;fail(e,context.kind);return true;}
      status(context.kind==='save'?'Rules saved. Inspect destinations before sorting.':'Rules reviewed. Save explicitly to use this replacement.');
    } else if(context.kind==='discover') {
      suggestions(result);status('Filename discovery complete. Choose a suggestion or inspect without categories.');
    } else if(context.kind==='plan') {
      if(context.generation!==revision){status('This inspection is outdated. Inspect again with the current settings.');return true;}
      preview=result;state.plan=!!result.ready;$('plan-result').textContent=JSON.stringify(result,null,2);planSummary(result);destinations(result);
      status(result.ready?'Review the destinations, then confirm to apply.':'Resolve the listed blockers, then inspect again.');
    } else if(context.kind==='undo') {
      undo=result;$('ack-undo').checked=false;
      $('undo-summary').textContent=result.ready?`Restore ${result.files_to_restore} original files and remove ${result.outputs_to_remove} sorted copies; restore the private category records.`:Object.keys(result.blockers||{}).map(code=>recovery.text(code,'undo')).join('\n\n');
    } else {
      if(context.kind==='apply'||context.kind==='restore'){assignments.clear();displayed=null;$('category-destinations').replaceChildren();$('category-pages').hidden=true;}
      invalidate();undo=null;$('ack-undo').checked=false;
      $('plan-result').textContent=JSON.stringify(result,null,2);
      status((context.kind==='restore'?'Undo':'Sort')+': '+result.checkpoint+'. '+(result.checkpoint==='COMPLETE'?'Inspect again before another sort.':'Review the report. Undo is available for recorded changes.'));
      if(context.kind==='restore')$('undo-summary').textContent='Undo: '+result.checkpoint;
      else {planSummary(result);state.audit=result;renderAuditBadge();}
    }
    return true;
  }
  async function rulesAction(kind,discardConfirmed=false) {
    if(pending||busyJob)return;
    if(kind==='load'&&dirty&&!discardConfirmed){$('category-reload-confirm').hidden=false;$('category-reload-cancel').focus();return;}
    if(kind!=='load'&&!validateRules(true))return;
    const generation=rulesRevision, selection=ruleOptions(), reviewed=draft;
    if(kind==='save'&&!reviewed)return;
    if(kind!=='load') {
      draft=null;
      return request('category-rules',kind==='save'?{...reviewed.options,save:true,expected_revision:reviewed.revision}:selection,kind,{selection});
    }
    pending=true;$('sort-error').hidden=true;updateDisabled();
    $('category-review-result').textContent=kind==='save'?'Saving reviewed rules…':'Reading filename rules…';
    try {
      const result=await api('category-rules');
      if(generation!==rulesRevision){$('category-review-result').textContent='The draft changed while reading. Review it again.';return;}
      acceptRules(kind,result,selection);
    } catch(e) {draft=null;fail(e);} finally {pending=false;writing=false;updateDisabled();}
  }
  function acceptRules(kind,result,selection) {
      if(kind==='load') {
        const rows=result.rules.categories;
        replaceRows(rows);draft=null;dirty=false;rulesRevision++;invalidate();
      } else if(kind==='review') {
        if(result.status!=='DRAFT')throw new Error('CATEGORY_DRAFT_REQUIRED');
        draft={options:selection,revision:result.revision};
      } else {draft=null;dirty=false;replaceRows(result.rules.categories);rulesRevision++;invalidate();}
      if(kind!=='review'){choicesGeneration++;savedRules=result.rules.categories;choiceRevision=result.revision;if(displayed)renderFiles();$('category-choice-status').textContent=savedRules.length+' saved categories. Unsaved rule edits are not used for sorting.';}
      const rows=result.rules.categories;
      $('category-draft-state').textContent=kind==='review'?'Reviewed draft · not saved. Sorting still uses saved rules.':kind==='save'?'Saved rules · used by the next inspection.':'Saved rules loaded · no unsaved changes.';
      $('category-review-result').textContent=(kind==='save'?'Saved. ':kind==='load'?'Loaded. ':'Reviewed replacement. ')+rows.length+' categories. '+
        rows.map(r=>r.label+' → '+r.slug).join('; ')+(result.review?' Matching titles: '+JSON.stringify(result.review.counts):'')+(kind==='save'?' Inspect destinations before sorting.':'');
  }
  $('run-plan').onclick=()=>{if($('sort-categories').checked&&choiceRevision!==null){const allowed=new Set(['auto','uncategorized',...savedRules.map(r=>r.slug)]);if([...assignments.values()].some(v=>!allowed.has(v))){fail(new Error('CATEGORY_ASSIGNMENT_INVALID'));return;}}invalidate();request('organize',options(),'plan');};
  $('apply').onclick=()=>{if(!preview?.ready||!preview?.plan_id||!$('ack-remove').checked)return;const current=preview;preview=null;state.plan=false;request('organize',{...options(),apply:true,acknowledge_source_removal:true,plan_id:current.plan_id},'apply');};
  for(const id of inputFields)$(id).oninput=()=>{if(id==='sort-categories'){$('category-options').hidden=!$(id).checked;if($(id).checked)loadChoices();}invalidate();};
  for(const id of ruleFields)$(id).oninput=()=>{ruleChanged();validateRules();updateDisabled();};
  $('category-add').onclick=()=>{if(!writing)addRule();};
  $('category-choice-retry').onclick=loadChoices;
  $('category-choice-reset').onclick=()=>{assignments.clear();invalidate();if(displayed)renderFiles();};
  $('category-reload-cancel').onclick=()=>{$('category-reload-confirm').hidden=true;$('category-load').focus();};
  $('category-reload-confirmed').onclick=()=>{$('category-reload-confirm').hidden=true;rulesAction('load',true);};
  for(const [id,step] of [['category-prev',-1],['category-next',1]])$(id).onclick=()=>{filePage+=step;renderFiles();$('category-destinations').scrollTop=0;};
  $('ack-remove').onchange=updateDisabled;$('ack-undo').onchange=updateDisabled;
  for(const kind of ['load','review','save'])$('category-'+kind).onclick=()=>rulesAction(kind);
  $('category-discover').onclick=async()=>{
    if(pending||busyJob)return;
    const count=Number($('category-min-count').value);
    if(!Number.isInteger(count)||count<1){$('category-min-count').setAttribute('aria-invalid','true');fail(new Error('CATEGORY_OPTIONS_INVALID'));return;}
    $('category-min-count').removeAttribute('aria-invalid');
    $('category-suggestions').textContent='Discovering recurring filename terms…';
    await request('categories',{min_count:count},'discover');
  };
  function suggestions(result) {
      const area=$('category-suggestions');area.replaceChildren();
      for(const group of result.corpus?.categories||[]) {
        const row=el('div','sort-suggestion');const button=el('button','secondary compact','Use group '+group.label);
        button.onclick=()=>{if(pending||busyJob)return;addRule({label:group.label,slug:tokens(group.label).join('-'),terms:group.terms});validateRules();};
        row.append(button,el('span','',`${group.support} distinct title families · ${group.terms.join(' · ')}`));area.append(row);
      }
      for(const item of result.candidates) {
        const row=el('div','sort-suggestion');const button=el('button','secondary compact','Use '+item.term);
        button.onclick=()=>{if(pending||busyJob)return;addRule({label:item.term,slug:tokens(item.term).join('-'),terms:[item.term]});validateRules();};
        row.append(button,el('span','',`${item.count} files · ${item.examples.join(' · ')}`));area.append(row);
      }
      if(!result.candidates.length&&!result.corpus?.categories?.length)area.textContent='No supported groups or terms meet this count. Sorting remains available without categories.';
      if(result.checkpoint!=='COMPLETE')area.append(el('p','sort-error','Some paths could not be read. These counts are incomplete.'));
  }
  $('category-min-count').oninput=()=>{discoveryRevision++;};
  function onJob(job) {
    if(!requests.has(job.id))return;
    const running=['queued','running'].includes(job.state);
    $('sort-activity').hidden=!running;
    $('sort-job-detail').textContent=(job.read_only?'Read-only inspection · ':'')+job.phase+
      (job.total?` · ${job.processed||0} / ${job.total}`:Number.isInteger(job.processed)?` · ${job.processed} checked`:'');
    const bar=$('sort-job-progress');
    if(job.total)bar.value=Math.min(100,100*(job.processed||0)/job.total);else bar.removeAttribute('value');
    const button=$('sort-cancel');button.hidden=!job.cancellable;
    button.disabled=!!job.cancel_requested;button.textContent=job.cancel_requested?'Cancellation requested':'Cancel inspection';
  }
  $('sort-cancel').onclick=async()=>{
    if(!busyJob||!requests.has(busyJob))return;
    $('sort-cancel').disabled=true;
    try{await api('jobs/'+busyJob+'/cancel',{});await refresh();}
    catch(e){$('sort-cancel').disabled=false;fail(e);}
  };
  $('organize-dialog').addEventListener('close',()=>{
    revision++;rulesRevision++;discoveryRevision++;preview=null;undo=null;draft=null;state.plan=false;
    $('category-draft-state').textContent=dirty?'Unsaved draft retained · review again before saving.':'Saved rules are used for sorting. Review again before saving a replacement.';
    $('category-destinations').classList.add('sort-outdated');status('Inspection closed. Your draft and choices are retained; inspect again before applying.');
    $('ack-remove').checked=false;$('ack-undo').checked=false;updateDisabled();
  });
  $('undo-preview').onclick=()=>{undo=null;request('undo-sort',{},'undo');};
  $('undo-apply').onclick=()=>{if(!undo?.ready||!$('ack-undo').checked)return;const current=undo;undo=null;request('undo-sort',{apply:true,acknowledge_restore:true,sort_id:current.sort_id},'restore');};
  updateDisabled();
  return {completed,onJob,updateDisabled,deferCompletion:()=>awaitingJob};
})();
