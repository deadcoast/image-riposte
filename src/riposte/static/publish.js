/* The primary product path. The workshop is an optional exact-output handoff. */
'use strict';
window.RipostePublish = (() => {
  const selected = new Set();
  let sourceKey='', batchesKey='', batch=null, current='', fetching=false;
  let review=null, difference=false, native=false;
  const models=()=>$('pub-models').value.split(/\r?\n/).map(s=>s.trim()).filter(Boolean);
  const edges=()=>[...document.querySelectorAll('.pub-sizes input:checked')].map(x=>Number(x.value));
  function settings(){return {vae_directories:models(),device:$('pub-device').value,pipeline_directory:$('pub-inpaint').value.trim(),temporal_directory:$('pub-video').value.trim()};}
  function request(){return {...settings(),image_ids:[...selected],edges:edges(),epsilon:Number($('pub-epsilon').value),steps:Number($('pub-steps').value),restarts:Number($('pub-restarts').value),seed:7,preserve_white:$('pub-white').checked,rms_fraction:Number($('pub-rms').value),delta_e76_p95:Number($('pub-colour').value)};}
  function disabled(){
    $('pub-selected-count').textContent=selected.size+' SELECTED';
    $('pub-start').disabled=!!busyJob||!selected.size||!models().length||models().length>4||!edges().length;
    $('pub-plan-button').disabled=!!busyJob||!selected.size||!edges().length;
    $('pub-execute').disabled=!!busyJob||!models().length||models().length>4;
    $('pub-resume').hidden=!batch||!(batch.counts.PENDING+batch.counts.BLOCKED);
    $('pub-resume').disabled=!!busyJob||!models().length;
    $('pub-download').disabled=!!busyJob||!batch?.counts.ACCEPTED;
    $('pub-review-accept').disabled=!!busyJob||!review||!$('pub-review-quality').checked||!$('pub-review-ack').checked;
    $('pub-review-reject').disabled=!!busyJob||!review;
    $('pub-workshop').disabled=!!busyJob||!review;
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
      else picture.textContent=item.status==='BLOCKED'?(messages[item.code]||item.code.replaceAll('_',' ')):'WAITING FOR PROTECTION';
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
    catch(e){error(e);}finally{fetching=false;}
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
    try{state.audit=await api('audit');}catch(e){error(e);}
    renderAuditBadge();
  }
  async function openReview(item,batchID){
    review={item,batchID};difference=false;native=false;
    $('pub-review-title').textContent=item.relative;$('pub-review-view').value='identity';$('pub-review-quality').checked=false;$('pub-review-ack').checked=false;
    $('pub-review-pair').classList.remove('native');$('pub-review-fit').classList.add('selected');$('pub-review-native').classList.remove('selected');$('pub-review-difference').classList.remove('selected');
    if(!$('pub-review-dialog').open)$('pub-review-dialog').showModal();renderReview();disabled();
  }
  function renderReview(){
    if(!review)return;const {item,batchID}=review,view=$('pub-review-view').value;
    const path='publication/'+batchID+'/image/'+item.id+'/';
    loadImage($('pub-review-clean'),path+'clean?view='+view);loadImage($('pub-review-candidate'),path+(difference?'difference':'candidate')+'?view='+view);
    $('pub-review-candidate-label').textContent=difference?'ABSOLUTE DIFFERENCE ×12':view==='identity'?'CANDIDATE · ACTUAL EXPORT PIXELS':'CANDIDATE · SAME TRANSPORT TRANSFORM';
    const row=item.transport?.rows.find(r=>r.transform===view),area=$('pub-review-metrics');area.replaceChildren();
    const metrics=view==='identity'?[[item.quality.max_channel_delta_255,'PEAK CHANGE / 255'],[item.quality.worst_tile_rmse_255.toFixed(2),'WORST LOCAL RMS'],[item.quality.delta_e76_p95.toFixed(2),'COLOUR ΔE76 / P95'],['PASS','NUMERIC QUALITY ONLY']]:[[row?.rmse_255.toFixed(3)||'—','RESIDUAL RMS / 255'],[row?.max_channel_delta_255??'—','POST-TRANSPORT PEAK Δ'],['UNVERIFIED','AI RESISTANCE']];
    for(const [value,label] of metrics){const box=el('div');box.append(el('strong','',String(value)),el('span','',label));area.append(box);}
    $('pub-review-help').textContent=view==='identity'?'Compare line work, flat areas and colour. These are the exact baseline and candidate PNG pixels; numeric quality passing does not replace your judgment.':'Both images received the same real transformation. Remaining pixel differences are not proof of AI resistance. Approval always applies to the original publishing PNG, not this stress-test preview.';
  }
  async function decision(accepted){
    if(!review)return;try{
      const result=await api('publication/'+review.batchID+'/review',{item_ids:[review.item.id],decision:accepted?'ACCEPTED':'REJECTED',visual_accepted:$('pub-review-quality').checked,acknowledge_unverified:$('pub-review-ack').checked});
      if(current===result.id){batch=result;renderBatch();}$('pub-review-dialog').close();toast(accepted?'This exact PNG is approved for the publishing pack. AI resistance remains unverified.':'This image is excluded from the publishing pack.');
    }catch(e){error(e);}
  }
  $('pub-select-all').onclick=()=>{for(const row of state.images)selected.add(row.id);renderSources(true);};$('pub-clear').onclick=()=>{selected.clear();renderSources(true);};
  for(const id of ['pub-models','pub-device','pub-steps','pub-restarts','pub-inpaint','pub-video','pub-rms','pub-colour','pub-white'])$(id).addEventListener('input',disabled);
  for(const input of document.querySelectorAll('.pub-sizes input'))input.onchange=disabled;
  $('pub-epsilon').oninput=()=>{$('pub-epsilon-value').textContent=$('pub-epsilon').value+' / 255';};
  $('pub-plan-button').onclick=async()=>{try{const r=await api('publish',{...request(),plan_only:true});$('pub-plan').querySelector('p').textContent=r.images+' clean master'+(r.images===1?'':'s')+' → '+r.outputs+' independently protected output'+(r.outputs===1?'':'s')+'. '+r.duplicate_renders_avoided+' duplicate size'+(r.duplicate_renders_avoided===1?'':'s')+' skipped. Originals remain unchanged. Preview changed no files.';}catch(e){error(e);}};
  $('pub-start').onclick=()=>launch('publish',request());
  $('pub-execute').onclick=()=>launch('execute-model',{vae_directories:models(),device:$('pub-device').value});
  $('pub-resume').onclick=()=>{if(current)launch('publication/'+current+'/resume',settings());};
  $('pub-batches').onchange=()=>{current=$('pub-batches').value;loadBatch(true);};
  $('pub-download').onclick=async()=>{if(!batch)return;try{
    const response=await fetch('/api/publication/'+batch.id+'/pack',{headers:requestHeaders,cache:'no-store'});
    if(!response.ok){const r=await response.json();throw new Error(r.code||'DOWNLOAD_FAILED');}
    const url=URL.createObjectURL(await response.blob()),link=el('a');link.href=url;link.download='RIPOSTE-'+String(batch.sequence).padStart(2,'0')+'.zip';document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),10000);
  }catch(e){error(e);}};
  $('pub-review-close').onclick=()=>$('pub-review-dialog').close();$('pub-review-view').onchange=renderReview;
  $('pub-review-fit').onclick=()=>{native=false;$('pub-review-pair').classList.remove('native');$('pub-review-fit').classList.add('selected');$('pub-review-native').classList.remove('selected');};
  $('pub-review-native').onclick=()=>{native=true;$('pub-review-pair').classList.add('native');$('pub-review-fit').classList.remove('selected');$('pub-review-native').classList.add('selected');};
  $('pub-review-difference').onclick=()=>{difference=!difference;$('pub-review-difference').classList.toggle('selected',difference);renderReview();};
  $('pub-review-quality').onchange=$('pub-review-ack').onchange=disabled;
  $('pub-review-accept').onclick=()=>decision(true);$('pub-review-reject').onclick=()=>decision(false);
  $('pub-workshop').onclick=async()=>{if(!review)return;try{const t=await api('publication/'+review.batchID+'/workshop/'+review.item.id,{});state.selected=state.images.find(x=>x.id===t.image_id);state.trial=t;state.trials.unshift(t);state.transport='identity';$('transport-view').value='identity';$('pub-review-dialog').close();setView('lab');toast('The workshop is inspecting the exact publishing output. It did not regenerate the image.');}catch(e){error(e);}};
  return {onState,activate,chooseCurrent,completed};
})();
