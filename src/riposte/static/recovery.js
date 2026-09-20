'use strict';
// One packaged catalog is also consumed by riposte.recovery. Presentation only.
window.RiposteRecovery = (() => {
  const safeCode = value => typeof value==='string' && value.length<=100 && /^[A-Z]/.test(value) && !/[^A-Z0-9_]/.test(value) ? value : 'OPERATION_FAILED';
  const fallback = {version:1,aliases:{},entries:{OPERATION_FAILED:{title:'Operation needs attention.',action:'Guidance is unavailable. Keep files and recovery records intact. Check the operation status before trying again; changes are never retried automatically.'}}};
  let catalog = fallback;
  const ready = (async () => {
    const abort = new AbortController(), timer = setTimeout(()=>abort.abort(),2000);
    try {
      const response=await fetch('/static/recovery-catalog.json',{cache:'no-store',signal:abort.signal});
      if(!response.ok)throw Error('catalog unavailable');
      const value=await response.json();
      if(value.version!==1||!value.entries?.OPERATION_FAILED||!value.aliases||!Object.values(value.aliases).every(v=>typeof v==='string'))throw Error('catalog schema');
      for(const [code,entry] of Object.entries(value.entries))if(safeCode(code)!==code||!entry||!['title','action'].every(k=>typeof entry[k]==='string'&&entry[k])||!['error','info'].includes(entry.level||'error')||!Object.values(entry.operations||{}).every(v=>typeof v==='string'&&v))throw Error('catalog entry');
      catalog=value;
    } catch { /* A broken bundle must not prevent error reporting or app startup. */ }
    finally {clearTimeout(timer);}
  })();
  function lookup(value,operation='') {
    const code=safeCode(value),entry=Object.hasOwn(catalog.entries,code)?catalog.entries[code]:catalog.entries.OPERATION_FAILED;
    const family=catalog.aliases[String(operation).split('/')[0].toLowerCase()]||'general';
    return {code,title:entry.title,action:entry.operations?.[family]||entry.action,level:entry.level||'error'};
  }
  function text(code,operation='') {const item=lookup(code,operation);return `${item.title} Next action: ${item.action} Code: ${item.code}`;}
  return {ready,safeCode,lookup,text};
})();
