/* Independent read-only comparison; all paths are rendered as text. */
'use strict';
window.RiposteDuplicates = (() => {
  const labels=['DUPLICATE','MAYBE DUPLICATE','CLOSELY RELATED'];
  const memberRequests=new WeakMap();
  let scan=null, jobId=null, starting=false, revision=0, detailRevision=0, offset=0, selected=null, timer;
  const status=text=>{$('dup-status').textContent=text;};
  const human=value=>String(value).replaceAll('_',' ').toLowerCase();
  function updateDisabled(){
    $('dup-scan').disabled=starting||!!busyJob||!!jobId;
    for(const input of $('dup-form').querySelectorAll('input'))input.disabled=starting||!!jobId;
    $('dup-videos').disabled=starting||!!jobId||!$('dup-visual').checked;
    $('dup-cancel').hidden=!jobId;
    $('dup-json').disabled=$('dup-csv').disabled=!scan;
  }
  function clearDetail(){
    detailRevision++;selected=null;
    for(const img of $('dup-detail').querySelectorAll('img'))clearImage(img);
    $('dup-detail').replaceChildren(el('p','','Select a finding to inspect both files and the matching evidence.'));
  }
  function coverage(result){
    const body=$('dup-coverage-body');body.replaceChildren();
    for(const [name,value] of Object.entries(result.counts))body.append(el('p','',human(name)+': '+value));
    for(const [name,value] of Object.entries(result.coverage))body.append(el('p','',human(name)+': '+value));
    for(const [code,count] of Object.entries(result.issues.counts))body.append(el('p','amber',human(code)+' · '+count));
    for(const issue of result.issues.examples)body.append(el('p','duplicate-path',JSON.stringify(issue)));
    if(result.issues.omitted_examples)body.append(el('p','amber',result.issues.omitted_examples+' additional issue examples omitted; counts include them.'));
    $('dup-coverage').open=result.checkpoint!=='COMPLETE';
  }
  async function results(){
    if(!scan)return;
    const current=++revision, id=scan.scan_id;
    clearDetail();$('dup-list').replaceChildren(el('p','','Loading findings…'));
    $('dup-prev').disabled=$('dup-next').disabled=true;
    const confidence=Number($('dup-confidence').value);
    if(!Number.isFinite(confidence)||confidence<0||confidence>100){$('dup-list').replaceChildren(el('p','amber','Enter a minimum score from 0 to 100.'));return;}
    const query=new URLSearchParams({label:$('dup-label').value,search:$('dup-search').value,media:$('dup-media').value,
      min_confidence:String(confidence),order:$('dup-order').value,offset:String(offset),limit:'30'});
    try{
      const page=await api('duplicates/'+id+'/findings?'+query);
      if(current!==revision||id!==scan?.scan_id)return;
      offset=page.offset;$('dup-list').replaceChildren();
      $('dup-page').textContent=page.total?`${offset+1}–${offset+page.rows.length} of ${page.total} findings`:'0 findings';
      $('dup-prev').disabled=offset===0;$('dup-next').disabled=offset+page.rows.length>=page.total;
      for(const row of page.rows){
        const button=el('button','duplicate-row');button.type='button';button.dataset.finding=row.id;
        button.setAttribute('aria-pressed','false');
        const heading=el('span','duplicate-row-heading');heading.append(el('strong','',row.label),el('span','duplicate-score',String(row.confidence)+' / 100'));
        button.append(heading,el('span','duplicate-path',row.left_path),el('span','duplicate-path',row.right_path),el('small','',row.member_count+' files · '+human(row.basis)));
        button.onclick=()=>detail(row);$('dup-list').append(button);
      }
      if(!page.rows.length)$('dup-list').append(el('p','duplicate-empty','No findings match these filters. Scan coverage lists any skipped files and limits.'));
    }catch(e){if(current===revision){$('dup-list').replaceChildren(el('p','amber','Findings unavailable. Run a new scan to rebuild this session’s report.'));error(e);}}
  }
  async function preview(container,source,id,stamp=null){
    container.replaceChildren();container.append(el('p','duplicate-path',source.relative));
    container.append(el('small','',`${source.bytes.toLocaleString()} bytes · ${source.width||'?'} × ${source.height||'?'} · ${source.media}`));
    if(!['image','video'].includes(source.media)){container.append(el('p','','No image preview for this file type. Equality was checked from file contents.'));return;}
    const img=el('img','duplicate-image');img.alt=source.relative;const note=el('p','', 'Verifying source and loading preview…');container.append(img,note);
    const path='duplicates/'+id+'/preview/'+source.id+(stamp===null?'':'?timestamp='+encodeURIComponent(stamp));
    const loaded=await loadImage(img,path,{fresh:true});
    if(!img.isConnected){clearImage(img);return;}
    note.textContent=loaded?(source.media==='video'?'Sampled video frame. Audio is not compared.':'Verified source · display thumbnail'):'Preview unavailable or source changed. Rescan before relying on this finding.';
  }
  async function members(group,container,side,current,id,start=0){
    const request={};memberRequests.set(container,request);
    try{
      const data=start===0?group:await api(`duplicates/${id}/groups/${group.id}?offset=${start}&limit=50`);
      if(current!==detailRevision||memberRequests.get(container)!==request)return;
      container.replaceChildren(el('h3','',`${side} · ${data.count} file${data.count===1?'':'s'}`));
      const list=el('ul','duplicate-members');
      for(const source of data.members){const item=el('li');const choose=el('button','duplicate-member',source.relative);choose.type='button';choose.onclick=()=>{
        if(current!==detailRevision)return;
        const panel=$('dup-detail').querySelector('[data-side="'+side+'"]');
        for(const img of panel.querySelectorAll('img'))clearImage(img);
        preview(panel,source,id);
      };item.append(choose,el('small','',source.bytes+' bytes · SHA-256 '+source.sha256));list.append(item);}
      container.append(list);
      const controls=el('div','duplicate-controls');
      controls.append(el('span','',`${data.offset+1}–${data.offset+data.members.length} of ${data.count}`));
      for(const [title,step] of [['Previous members',-50],['Next members',50]]){
        const button=el('button','secondary',title);button.disabled=step<0?data.offset===0:data.offset+data.members.length>=data.count;
        button.onclick=()=>members(group,container,side,current,id,data.offset+step);controls.append(button);
      }container.append(controls);
    }catch(e){if(current===detailRevision){container.replaceChildren(el('p','amber','Member list unavailable. Rescan and retry.'));error(e);}}
  }
  async function detail(row){
    clearDetail();selected=row.id;const current=detailRevision,id=scan.scan_id;
    for(const button of $('dup-list').querySelectorAll('button'))button.setAttribute('aria-pressed',String(button.dataset.finding===selected));
    $('dup-detail').replaceChildren(el('p','','Loading matching evidence…'));
    try{
      const data=await api(`duplicates/${id}/findings/${row.id}`);
      if(current!==detailRevision||id!==scan?.scan_id)return;
      const root=$('dup-detail');root.replaceChildren(el('h2','',row.label),el('p','duplicate-score',row.confidence+' / 100 · '+human(row.basis)));
      const pair=el('div','duplicate-pair'),left=el('figure'),right=el('figure');left.dataset.side='Left';right.dataset.side='Right';pair.append(left,right);root.append(pair);
      const a=data.left.members.find(source=>source.id===row.left_source)||data.left.representative_record||data.left.members[0];
      const other=data.right||data.left;const b=other.members.find(source=>source.id===row.right_source)||other.members.find(source=>source.id!==a.id)||other.members[0];
      preview(left,a,id,data.finding.left_time??null);preview(right,b,id,data.finding.right_time??null);
      root.append(el('p','duplicate-policy',data.confidence_policy));
      const evidence=el('details');evidence.open=true;evidence.append(el('summary','','Matching evidence'));
      const values=el('dl','duplicate-signals');
      const signal=(key,value)=>{
        if(value&&typeof value==='object'&&!Array.isArray(value)){for(const [name,entry] of Object.entries(value))signal(name,entry);return;}
        values.append(el('dt','',human(key)),el('dd','',value===null?'Not applicable':Array.isArray(value)?value.join(', '):String(value)));
      };
      for(const [key,value] of Object.entries(data.finding)){
        if(['id','left','right','label','confidence','confidence_kind'].includes(key))continue;
        signal(key,value);
      }evidence.append(values);root.append(evidence);
      const leftMembers=el('section');root.append(leftMembers);members(data.left,leftMembers,'Left',current,id);
      if(data.right){const rightMembers=el('section');root.append(rightMembers);members(data.right,rightMembers,'Right',current,id);}
    }catch(e){if(current===detailRevision){$('dup-detail').replaceChildren(el('p','amber','Finding unavailable. Run a new scan.'));error(e);}}
  }
  async function exportReport(format){
    if(!scan)return;const id=scan.scan_id;
    try{
      const response=await fetch(`/api/duplicates/${id}/export?format=${format}`,{headers:requestHeaders,cache:'no-store'});
      if(!response.ok)throw Error('DUPLICATE_SCAN_EXPIRED');
      const url=URL.createObjectURL(await response.blob()),anchor=el('a');anchor.href=url;anchor.download=`riposte-duplicates-${id.slice(0,12)}.${format}`;
      document.body.append(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
    }catch(e){status('Export unavailable. Rescan to rebuild the report.');error(e);}
  }
  $('dup-form').onsubmit=async event=>{
    event.preventDefault();if(starting||busyJob||jobId)return;
    $('dup-settings-error').hidden=true;
    for(const input of $('dup-form').querySelectorAll('input[type=number]')){
      const value=Number(input.value),invalid=!input.value||!Number.isInteger(value)||value<Number(input.min)||value>Number(input.max);
      input.setAttribute('aria-invalid',String(invalid));input.setAttribute('aria-describedby','dup-settings-error');
      if(invalid){$('dup-settings-error').textContent='Enter a whole number between '+Number(input.min).toLocaleString()+' and '+Number(input.max).toLocaleString()+' for '+input.parentElement.firstChild.textContent.trim().toLowerCase()+'.';$('dup-settings-error').hidden=false;input.closest('details').open=true;input.focus();return;}
    }
    starting=true;updateDisabled();status('Starting read-only scan. Existing results, if any, describe the previous scan.');
    try{
      const answer=await api('duplicates',{visual:$('dup-visual').checked,videos:$('dup-videos').checked,include_float:$('dup-float').checked,
        max_files:Number($('dup-max-files').value),max_visual:Number($('dup-max-visual').value),max_pairs:Number($('dup-max-pairs').value)});
      jobId=answer.job_id;busyJob=jobId;status('Scanning files and comparing content. Progress and cancellation are available below.');
    }catch(e){status('Scan could not start. Check the settings and retry.');error(e);}
    finally{starting=false;updateDisabled();refresh();}
  };
  $('dup-cancel').onclick=async()=>{if(!jobId)return;try{await api('jobs/'+jobId+'/cancel',{});status('Stop requested. Waiting for the current safe checkpoint.');}catch(e){error(e);}};
  $('dup-visual').onchange=updateDisabled;
  for(const id of ['dup-label','dup-media','dup-confidence','dup-order'])$(id).onchange=()=>{offset=0;results();};
  $('dup-search').oninput=()=>{clearTimeout(timer);revision++;clearDetail();timer=setTimeout(()=>{offset=0;results();},180);};
  $('dup-prev').onclick=()=>{offset=Math.max(0,offset-30);results();};$('dup-next').onclick=()=>{offset+=30;results();};
  $('dup-json').onclick=()=>exportReport('json');$('dup-csv').onclick=()=>exportReport('csv');
  function completed(job){
    if(job.id!==jobId&&job.result?.mode!=='DUPLICATE_SCAN')return false;
    if(jobId&&job.id!==jobId)return true;
    jobId=null;updateDisabled();
    if(!['done','incomplete'].includes(job.state)){status(job.state==='cancelled'?'Scan cancelled. No files changed; any displayed results are from the previous scan.':'Scan failed: '+human(job.code)+'. Any displayed results are from the previous scan.');return true;}
    scan=job.result;offset=0;revision++;clearDetail();$('dup-results').hidden=false;$('dup-root').textContent=scan.root;
    $('dup-counts').replaceChildren();for(const label of labels){const block=el('div');block.append(el('strong','',String(scan.counts[label]||0)),el('span','',label),el('small','muted',label==='DUPLICATE'?'Exact groups':'Pair relationships'));$('dup-counts').append(block);}
    coverage(scan);status(scan.checkpoint==='COMPLETE'?'Scan complete within the recorded coverage. No files changed.':'Scan incomplete. Findings cover the successfully compared files; review skipped files and limits.');results();return true;
  }
  updateDisabled();return {updateDisabled,completed,deferCompletion:()=>starting};
})();
