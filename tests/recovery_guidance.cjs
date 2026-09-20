'use strict';
const fs=require('node:fs'),path=require('node:path'),vm=require('node:vm');
const dir=path.join(__dirname,'../src/riposte/static');
const vectors=JSON.parse(fs.readFileSync(0,'utf8'));
async function run(available){
  const context=vm.createContext({window:{},AbortController,setTimeout,clearTimeout,
    fetch:async()=>{if(!available)throw Error('C:\\private\\raw-network-error');return {ok:true,json:async()=>JSON.parse(fs.readFileSync(path.join(dir,'recovery-catalog.json'),'utf8'))};}});
  vm.runInContext(fs.readFileSync(path.join(dir,'recovery.js'),'utf8'),context);
  const recovery=context.window.RiposteRecovery;await recovery.ready;return recovery;
}
(async()=>{const normal=await run(true),fallback=await run(false);process.stdout.write(JSON.stringify({normal:vectors.map(v=>normal.lookup(v.code,v.operation)),fallback:fallback.lookup('WORKSPACE_LOCKED','sort')}));})().catch(e=>{console.error(e);process.exitCode=1;});
