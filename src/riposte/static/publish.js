/* The primary product path. The workshop is an optional exact-output handoff. */
'use strict';
window.RipostePublish = (() => {
  const selected = new Set();
  let sourceKey='', batchesKey='', batch=null, current='', fetching=false;
  let review=null, difference=false, native=false;
  const models=()=>$('pub-models').value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
  let recipeEdges=[], loadedRecipe=null, recipeDraft=null, recipeRows=[], recipePending=false, recipeEpoch=0, recipeEdit=0;
  const edges=()=>{
    const values=[...document.querySelectorAll('.pub-sizes input:checked')].map(x=>Number(x.value));
    if($('pub-extra-edges').value.trim())values.push(...$('pub-extra-edges').value.split(',').map(x=>x.trim()?Number(x):NaN));
    if(new Set(values).size!==values.length)return values; // Keep duplicates visible to validation.
    return [...recipeEdges.filter(x=>values.includes(x)),...values.filter(x=>!recipeEdges.includes(x))];
  };
  function settings(){return {vae_directories:models(),device:$('pub-device').value,pipeline_directory:$('pub-inpaint').value.trim(),temporal_directory:$('pub-video').value.trim()};}
  function recipeSettings(){return {edges:edges(),epsilon:Number($('pub-epsilon').value),steps:Number($('pub-steps').value),restarts:Number($('pub-restarts').value),seed:Number($('pub-seed').value),preserve_white:$('pub-white').checked,rms_fraction:Number($('pub-rms').value),delta_e76_p95:Number($('pub-colour').value)};}
  function request(){return {...settings(),...recipeSettings(),...(loadedRecipe||{}),image_ids:[...selected],masks:window.RiposteSpatial?.payload(selected)||[]};}
  const recipeSnapshot=()=>JSON.stringify({name:$('pub-recipe-name').value,settings:recipeSettings()});
  function recipeControls(){
    $('pub-recipe-load').disabled=recipePending||!$('pub-recipe-list').value;
    $('pub-recipe-reload').disabled=$('pub-recipe-preview').disabled=recipePending;
    $('pub-recipe-save').disabled=recipePending||!recipeDraft||recipeDraft.snapshot!==recipeSnapshot();
    $('pub-recipe-list').disabled=recipePending;
  }
  function recipeMessage(message){$('pub-recipe-status').textContent=message;}
  function recipeError(e){
    const node=$('pub-recipe-error');node.hidden=false;node.textContent=recovery.text(e.message,'publish');
    $('pub-recipe-name').setAttribute('aria-invalid',String(e.message==='RECIPE_NAME_INVALID'));
    node.focus();
  }
  function recipeBegin(message){
    recipePending=true;recipeDraft=null;$('pub-recipe-preview-values').hidden=true;
    $('pub-recipe-error').hidden=true;$('pub-recipe-name').removeAttribute('aria-invalid');
    recipeMessage(message);recipeControls();return ++recipeEpoch;
  }
  function recipeChanged(){
    window.RiposteSpatial?.invalidate();
    ++recipeEdit;recipeDraft=null;$('pub-recipe-preview-values').hidden=true;
    recipeMessage('Settings edited. Preview again before saving.');
    $('pub-plan').querySelector('p').textContent='Settings changed. Preview this batch again before starting.';
    recipeControls();disabled();
  }
  function recipeOptions(rows){
    const select=$('pub-recipe-list'),previous=select.value;recipeRows=rows;select.replaceChildren();
    const empty=el('option','',rows.length?'Choose a saved recipe':'No saved recipes yet');empty.value='';select.append(empty);
    for(const row of rows){const option=el('option','',row.name);option.value=row.name;select.append(option);}
    if(rows.some(row=>row.name===previous))select.value=previous;
  }
  async function reloadRecipes(){
    if(recipePending)return;const epoch=recipeBegin('Loading recipes…');
    try{const result=await api('recipes');if(epoch!==recipeEpoch)return;recipeOptions(result.recipes);recipeMessage(result.recipes.length+' saved recipes. Choose one, then Load settings.');}
    catch(e){if(epoch===recipeEpoch){recipeOptions([]);recipeError(e);recipeMessage('Could not load recipes. Your settings are retained; retry Reload recipes.');}}
    finally{if(epoch===recipeEpoch){recipePending=false;recipeControls();}}
  }
  async function loadRecipe(){
    if(recipePending)return;const name=$('pub-recipe-list').value,row=recipeRows.find(x=>x.name===name);if(!row)return;
    const edit=recipeEdit,epoch=recipeBegin('Loading '+name+'…');
    try{
      const result=await api('recipes?name='+encodeURIComponent(name));if(epoch!==recipeEpoch)return;
      if(edit!==recipeEdit){recipeMessage('Settings changed while loading. Choose Load settings again to replace them.');return;}
      if(result.recipe_revision!==row.recipe_revision)throw new Error('RECIPE_CHANGED');
      const values=result.settings;recipeEdges=[...values.edges];
      const known=[...document.querySelectorAll('.pub-sizes input')];
      for(const input of known)input.checked=values.edges.includes(Number(input.value));
      $('pub-extra-edges').value=values.edges.filter(x=>!known.some(i=>Number(i.value)===x)).join(', ');
      for(const [key,id] of Object.entries({epsilon:'epsilon',steps:'steps',restarts:'restarts',seed:'seed',rms_fraction:'rms',delta_e76_p95:'colour'}))$('pub-'+id).value=values[key];
      $('pub-white').checked=values.preserve_white;$('pub-epsilon-value').textContent=values.epsilon+' / 255';
      $('pub-recipe-name').value=result.name;loadedRecipe={recipe_name:result.name,recipe_revision:result.recipe_revision};
      recipeChanged();recipeMessage('Loaded '+result.name+'. Review the settings before starting protection.');
    }catch(e){if(epoch===recipeEpoch){recipeError(e);recipeMessage('Recipe was not loaded. Reload the library and try again.');}}
    finally{if(epoch===recipeEpoch){recipePending=false;recipeControls();}}
  }
  async function previewRecipe(){
    if(recipePending)return;const snapshot=recipeSnapshot(),edit=recipeEdit,epoch=recipeBegin('Checking recipe settings…');
    try{
      const result=await api('recipes',JSON.parse(snapshot));if(epoch!==recipeEpoch)return;
      if(edit!==recipeEdit||snapshot!==recipeSnapshot()){recipeMessage('Settings changed while checking. Preview again.');return;}
      recipeDraft={result,snapshot};const area=$('pub-recipe-preview-values');area.replaceChildren();area.hidden=false;
      const labels={edges:'Longest edges',epsilon:'Channel-change cap',steps:'Iterations',restarts:'Search restarts',seed:'Seed',preserve_white:'Preserve smooth white',rms_fraction:'Local RMS fraction',delta_e76_p95:'Colour ΔE76 cap'};
      for(const [key,value] of Object.entries(result.settings))area.append(el('dt','',labels[key]),el('dd','',Array.isArray(value)?value.join(', '):typeof value==='boolean'?(value?'On':'Off'):String(value)));
      recipeMessage((recipeRows.some(row=>row.name.toLocaleLowerCase()===result.name.toLocaleLowerCase())?'Save replaces ':'Save creates ')+result.name+'. Settings only; no processing starts.');
    }catch(e){if(epoch===recipeEpoch){recipeError(e);recipeMessage('Check the name and settings, then preview again.');}}
    finally{if(epoch===recipeEpoch){recipePending=false;recipeControls();}}
  }
  async function saveRecipe(){
    if(recipePending||!recipeDraft||recipeDraft.snapshot!==recipeSnapshot())return;
    const draft=recipeDraft,edit=recipeEdit,epoch=recipeBegin('Saving recipe…');
    try{
      const result=await api('recipes',{name:draft.result.name,settings:draft.result.settings,save:true,expected_revision:draft.result.revision});
      if(epoch!==recipeEpoch)return;recipeOptions(result.recipes);$('pub-recipe-list').value=result.name;
      if(edit===recipeEdit){loadedRecipe={recipe_name:result.name,recipe_revision:result.recipe_revision};$('pub-recipe-name').value=result.name;}
      recipeMessage('Saved '+result.name+'. No processing started.'+(edit!==recipeEdit?' Your newer form edits were not saved.':''));
    }catch(e){if(epoch===recipeEpoch){recipeError(e);recipeMessage('Save was not confirmed. Reload recipes to check the stored version, then preview your retained settings again.');}}
    finally{if(epoch===recipeEpoch){recipePending=false;recipeControls();}}
  }
  function disabled(){
    window.RiposteSpatial?.sync(state.images,selected);
    $('pub-selected-count').textContent=selected.size+' SELECTED';
    $('pub-start').disabled=!!busyJob||window.RiposteSpatial?.pending()||!selected.size||!models().length||models().length>4||!edges().length;
    $('pub-plan-button').disabled=!!busyJob||!selected.size||!edges().length;
    $('pub-execute').disabled=!!busyJob||!models().length||models().length>4;
    $('pub-resume').hidden=!batch||!(batch.counts.PENDING+batch.counts.BLOCKED);
    $('pub-resume').disabled=!!busyJob||!models().length;
    $('pub-download').disabled=!!busyJob||!batch?.counts.ACCEPTED;
    const reviewing=!!review&&$('pub-review-dialog').open,waiting=!!busyJob||!!review?.pending;
    const visible=reviewing&&review.ready&&review.originalSeen;
    $('pub-review-quality').disabled=waiting||!visible;
    $('pub-review-ack').disabled=waiting||!reviewing;
    $('pub-review-accept').disabled=waiting||!visible||!$('pub-review-quality').checked||!$('pub-review-ack').checked;
    $('pub-review-reject').disabled=waiting||!reviewing;
    $('pub-workshop').disabled=waiting||!reviewing;
    $('pub-review-view').disabled=$('pub-review-difference').disabled=waiting||!reviewing;
  }
  function renderSources(force=false){
    const key=JSON.stringify(state.images.map(x=>[x.id,x.sha256]));
    if(!force&&key===sourceKey){disabled();return;}sourceKey=key;
    const area=$('pub-sources');area.replaceChildren();
    const ids=new Set(state.images.map(x=>x.id));for(const id of selected)if(!ids.has(id))selected.delete(id);
    for(const row of state.images){
      const label=el('label','pub-source'),input=el('input'),image=el('img'),text=el('span','',shortName(row));
      input.type='checkbox';input.value=row.id;input.checked=selected.has(row.id);input.setAttribute('aria-label','Select '+shortName(row)+' '+row.day);
      input.onchange=()=>{if(input.checked)selected.add(row.id);else selected.delete(row.id);disabled();};
      image.alt='';image.loading='lazy';text.append(el('small','',row.day+' · '+row.width+'×'+row.height));label.append(input,image,text);area.append(label);loadImage(image,'image/'+row.id+'?thumb=true');
    }
    $('pub-no-art').hidden=!!state.images.length;disabled();
  }
  function renderBatch(){
    const area=$('pub-outputs'),summary=$('pub-batch-summary');area.replaceChildren();summary.replaceChildren();
    $('pub-empty').hidden=!!batch;$('pub-delivery').hidden=!batch;
    if(!batch){summary.append(el('p','','The files you make belong here. Advanced experiments stay in the workshop.'));disabled();return;}
    for(const [key,label] of [['READY_FOR_REVIEW','RENDERED'],['ACCEPTED','APPROVED'],['PENDING','PENDING'],['BLOCKED','BLOCKED']]){
      const count=el('div','pub-count');count.append(el('strong',key==='ACCEPTED'?'mint':'',String(batch.counts[key])),el('span','',label));summary.append(count);
    }
    for(const item of batch.items){
      const ready=item.status==='READY_FOR_REVIEW',card=el('article','pub-output'+(ready?'':' placeholder')+(item.review==='ACCEPTED'?' approved':''));
      const content=ready?el('button'):el('div'),picture=el('div','pub-output-image'),copy=el('div','pub-output-copy');
      if(ready){const image=el('img');image.alt='';picture.append(image);loadImage(image,'publication/'+batch.id+'/image/'+item.id+'/candidate?thumb=true');content.setAttribute('aria-label','Review '+item.relative.split('/').pop());const batchID=batch.id;content.onclick=()=>openReview(item,batchID);}
      else picture.textContent=item.status==='BLOCKED'?recovery.text(item.code,'publish'):'WAITING FOR PROTECTION';
      copy.append(el('strong','',ready?item.relative.split('/').pop():'Image '+String(batch.items.indexOf(item)+1).padStart(2,'0')),
        el('span','',item.date+(ready?' · '+item.width+' × '+item.height:' · edge '+item.max_edge)),
        el('span','pub-output-status',ready?(item.review==='ACCEPTED'?'APPROVED · UNVERIFIED':item.review==='REJECTED'?'DO NOT PUBLISH':item.review==='STALE'?'CHANGED · REVIEW AGAIN':'VISUAL REVIEW REQUIRED'):item.status));
      if(ready)copy.append(el('span','pub-review-link','Inspect actual pixels ↗'));content.append(picture,copy);card.append(content);area.append(card);
    }
    $('pub-approved-count').textContent=batch.counts.ACCEPTED+' file'+(batch.counts.ACCEPTED===1?'':'s')+' approved';disabled();
  }
  async function loadBatch(force=false){
    if(!current||fetching)return;fetching=true;const id=current;
    try{const data=await api('publication/'+id);if(current===id){batch=data;renderBatch();}}
    catch(e){error(e,'publish');}finally{fetching=false;}
  }
  function onState(data){
    $('candidate-count').textContent=String((data.publications||[]).reduce((n,b)=>n+b.counts.READY_FOR_REVIEW,0));
    renderSources();const list=data.publications||[];const key=JSON.stringify(list);
    if(key!==batchesKey){
      const oldLatest=$('pub-batches').options[0]?.value;batchesKey=key;
      if(!current||!list.some(x=>x.id===current)||(busyJob&&list[0]?.id!==oldLatest))current=list[0]?.id||'';
      const select=$('pub-batches');select.replaceChildren();for(const row of list){const o=el('option','',String(row.sequence).padStart(2,'0')+' · '+row.counts.READY_FOR_REVIEW+' rendered / '+row.counts.ACCEPTED+' approved');o.value=row.id;select.append(o);}if(!list.length){const o=el('option','','No batches yet');o.value='';select.append(o);}select.value=current;
      if(current)loadBatch(true);
    }
    disabled();
  }
  function chooseCurrent(){if(state.selected)selected.add(state.selected.id);renderSources(true);}
  function activate(){renderSources();if(!selected.size&&state.selected){selected.add(state.selected.id);renderSources(true);}if(current)loadBatch();}
  async function completed(result){
    current=result.id;batch=result;renderBatch();setView('publish');
    state.audit=null;renderAuditBadge();
    try{state.audit=await api('audit');}catch(e){error(e,'publish');}
    renderAuditBadge();
  }
  async function openReview(item,batchID){
    review={item,batchID,revision:0,ready:false,originalSeen:false,pending:false};difference=false;native=false;
    $('pub-review-title').textContent=item.relative;$('pub-review-view').value='identity';$('pub-review-quality').checked=false;$('pub-review-ack').checked=false;
    $('pub-review-pair').classList.remove('native');$('pub-review-fit').classList.add('selected');$('pub-review-native').classList.remove('selected');$('pub-review-difference').classList.remove('selected');
    if(!$('pub-review-dialog').open)$('pub-review-dialog').showModal();renderReview();disabled();
  }
  async function renderReview(){
    if(!review||review.pending)return;
    const target=review,revision=++target.revision,{item,batchID}=target,view=$('pub-review-view').value,original=view==='identity'&&!difference;
    target.ready=false;$('pub-review-quality').checked=false;
    $('pub-review-help').textContent='Loading both images for review…';disabled();
    const path='publication/'+batchID+'/image/'+item.id+'/';
    const pixels=Promise.all([loadImage($('pub-review-clean'),path+'clean?view='+view,{fresh:true}),loadImage($('pub-review-candidate'),path+(difference?'difference':'candidate')+'?view='+view,{fresh:true})]);
    $('pub-review-candidate-label').textContent=difference?'ABSOLUTE DIFFERENCE ×12':view==='identity'?'CANDIDATE · ACTUAL EXPORT PIXELS':'CANDIDATE · SAME TRANSPORT TRANSFORM';
    const row=item.transport?.rows.find(r=>r.transform===view),area=$('pub-review-metrics');area.replaceChildren();
    const metrics=view==='identity'?[[item.quality.max_channel_delta_255,'PEAK CHANGE / 255'],[item.quality.worst_tile_rmse_255.toFixed(2),'WORST LOCAL RMS'],[item.quality.delta_e76_p95.toFixed(2),'COLOUR ΔE76 / P95'],['PASS','NUMERIC QUALITY ONLY']]:[[row?.rmse_255.toFixed(3)||'—','RESIDUAL RMS / 255'],[row?.max_channel_delta_255??'—','POST-TRANSPORT PEAK Δ'],['UNVERIFIED','AI RESISTANCE']];
    for(const [value,label] of metrics){const box=el('div');box.append(el('strong','',String(value)),el('span','',label));area.append(box);}
    if(item.quality.spatial_budget){const box=el('div');box.append(el('strong','',item.quality.spatial_budget.unchanged_pixels.toLocaleString()),el('span','','PIXELS KEPT EXACT · ARTIST + AUTOMATIC LIMITS'));area.append(box);}
    const loaded=await pixels;
    if(review!==target||target.revision!==revision||!$('pub-review-dialog').open)return;
    target.ready=loaded.every(Boolean);if(target.ready&&original)target.originalSeen=true;
    // A click made while pixels were loading cannot count as inspecting them.
    $('pub-review-quality').checked=false;
    $('pub-review-help').textContent=!target.ready?'Could not load both images. Reopen this review or choose another view to retry. Approval is unavailable; you can still reject this output.':
      !target.originalSeen?'Choose Original raster with Difference switched off to inspect the publishing PNG before approving.':
      original?'Compare line work, flat areas and colour. These are the exact baseline and candidate PNG pixels; numeric quality passing does not replace your judgment.':
      'This preview helps inspect changes. Approval applies to the original publishing PNG. Pixel differences are not proof of AI resistance.';
    disabled();
  }
  function closeReview(){
    review=null;clearImage($('pub-review-clean'));clearImage($('pub-review-candidate'));
    $('pub-review-quality').checked=false;$('pub-review-ack').checked=false;
    $('pub-review-dialog').close();disabled();
  }
  async function decision(accepted){
    const target=review;
    if(!target||target.pending||busyJob||!$('pub-review-dialog').open)return;
    if(accepted&&(!target.ready||!target.originalSeen||!$('pub-review-quality').checked||!$('pub-review-ack').checked))return;
    target.pending=true;disabled();
    try{
      const result=await api('publication/'+target.batchID+'/review',{item_ids:[target.item.id],decision:accepted?'ACCEPTED':'REJECTED',visual_accepted:$('pub-review-quality').checked,acknowledge_unverified:$('pub-review-ack').checked});
      if(current===result.id){batch=result;renderBatch();}
      if(review!==target)return;
      closeReview();
      const approved=result.items.some(item=>item.id===target.item.id&&item.review==='ACCEPTED');
      toast(accepted?(approved?'This exact PNG is approved for the publishing pack. AI resistance remains unverified.':'The output changed and is not approved. Reopen it for review.'):'This image is excluded from the publishing pack.');
    }catch(e){if(review===target)error(e,'publish');}
    finally{target.pending=false;if(review===target)disabled();}
  }
  $('pub-select-all').onclick=()=>{for(const row of state.images)selected.add(row.id);renderSources(true);};$('pub-clear').onclick=()=>{selected.clear();renderSources(true);};
  for(const id of ['pub-models','pub-device','pub-steps','pub-restarts','pub-inpaint','pub-video','pub-rms','pub-colour','pub-white'])$(id).addEventListener('input',disabled);
  for(const input of document.querySelectorAll('.pub-sizes input'))input.onchange=disabled;
  for(const input of document.querySelectorAll('.pub-sizes input'))input.addEventListener('change',recipeChanged);
  for(const id of ['pub-epsilon','pub-steps','pub-restarts','pub-seed','pub-white','pub-rms','pub-colour','pub-extra-edges','pub-recipe-name'])$(id).addEventListener('input',recipeChanged);
  $('pub-recipes').addEventListener('toggle',()=>{if($('pub-recipes').open&&!recipeRows.length)reloadRecipes();});
  $('pub-recipe-reload').onclick=reloadRecipes;$('pub-recipe-load').onclick=loadRecipe;
  $('pub-recipe-preview').onclick=previewRecipe;$('pub-recipe-save').onclick=saveRecipe;
  $('pub-recipe-list').onchange=recipeControls;
  $('pub-epsilon').oninput=()=>{$('pub-epsilon-value').textContent=$('pub-epsilon').value+' / 255';};
  $('pub-plan-button').onclick=async()=>{try{const r=await api('publish',{...request(),plan_only:true});$('pub-plan').querySelector('p').textContent=r.images+' clean master'+(r.images===1?'':'s')+' → '+r.outputs+' independently protected output'+(r.outputs===1?'':'s')+'. '+r.duplicate_renders_avoided+' duplicate size'+(r.duplicate_renders_avoided===1?'':'s')+' skipped. Originals remain unchanged. Preview changed no files.';}catch(e){error(e,'publish');}};
  $('pub-start').onclick=()=>launch('publish',request());
  $('pub-execute').onclick=()=>launch('execute-model',{vae_directories:models(),device:$('pub-device').value});
  $('pub-resume').onclick=()=>{if(current)launch('publication/'+current+'/resume',settings());};
  $('pub-batches').onchange=()=>{current=$('pub-batches').value;loadBatch(true);};
  $('pub-download').onclick=async()=>{if(!batch)return;try{
    const response=await fetch('/api/publication/'+batch.id+'/pack',{headers:requestHeaders,cache:'no-store'});
    if(!response.ok){const r=await response.json();throw new Error(r.code||'DOWNLOAD_FAILED');}
    const url=URL.createObjectURL(await response.blob()),link=el('a');link.href=url;link.download='RIPOSTE-'+String(batch.sequence).padStart(2,'0')+'.zip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){error(e,'publish');}};
  $('pub-review-close').onclick=closeReview;
  $('pub-review-dialog').addEventListener('close',()=>{if(!$('pub-review-dialog').open)closeReview();});
  $('pub-review-view').onchange=renderReview;
  $('pub-review-fit').onclick=()=>{native=false;$('pub-review-pair').classList.remove('native');$('pub-review-fit').classList.add('selected');$('pub-review-native').classList.remove('selected');};
  $('pub-review-native').onclick=()=>{native=true;$('pub-review-pair').classList.add('native');$('pub-review-fit').classList.remove('selected');$('pub-review-native').classList.add('selected');};
  $('pub-review-difference').onclick=()=>{difference=!difference;$('pub-review-difference').classList.toggle('selected',difference);renderReview();};
  $('pub-review-quality').onchange=$('pub-review-ack').onchange=disabled;
  $('pub-review-accept').onclick=()=>decision(true);$('pub-review-reject').onclick=()=>decision(false);
  $('pub-workshop').onclick=async()=>{
    const target=review;if(!target||target.pending||busyJob||!$('pub-review-dialog').open)return;
    target.pending=true;disabled();
    try{
      const t=await api('publication/'+target.batchID+'/workshop/'+target.item.id,{});
      if(review!==target)return;
      state.selected=state.images.find(x=>x.id===t.image_id);state.trial=t;state.trials.unshift(t);state.transport='identity';$('transport-view').value='identity';closeReview();setView('lab');toast('The workshop is inspecting the exact publishing output. It did not regenerate the image.');
    }catch(e){if(review===target)error(e,'publish');}
    finally{target.pending=false;if(review===target)disabled();}
  };
  return {onState,activate,chooseCurrent,completed,request,budgetChanged:disabled};
})();
