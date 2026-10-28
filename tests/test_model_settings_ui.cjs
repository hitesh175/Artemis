const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Element{
  constructor(){this.children=[];this.events={};this.disabled=false;this.textContent='';this.value='';}
  addEventListener(name,handler){this.events[name]=handler;}
  replaceChildren(){this.children=[];}
  appendChild(child){this.children.push(child);}
}
(async()=>{
  const nodes=Object.fromEntries(['chat-model','model-status','refresh-models','save-model'].map(id=>[id,new Element()]));
  const events={};let selected='artemis',offline=false,saves=0;
  const api={async get_ollama_models(){return offline?{ok:false,error:'Ollama unavailable'}:{ok:true,selected,models:['artemis:latest','example:small']};},
    async select_ollama_model(name){saves++;selected=name;return {ok:true,selected};}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/desktop/web/model-settings.js'),'utf8'),
    {document:{getElementById:id=>nodes[id],createElement:()=>new Element()},window:{pywebview:{api},addEventListener:(name,handler)=>events[name]=handler}});
  const flush=()=>new Promise(resolve=>setImmediate(resolve));
  events.pywebviewready();await flush();
  assert.equal(saves,0,'Loading the selector must not change the saved model');
  assert.equal(nodes['chat-model'].value,'artemis');
  assert.equal(nodes['chat-model'].children[0].disabled,false,'Default latest-tag alias should be available');
  nodes['chat-model'].value='example:small';
  await nodes['save-model'].events.click();
  assert.equal(selected,'example:small');
  assert.match(nodes['model-status'].textContent,/Saved: example:small/);
  offline=true;nodes['refresh-models'].events.click();await flush();
  assert.equal(nodes['save-model'].disabled,true);
  assert.equal(selected,'example:small');
  assert.equal(nodes['model-status'].textContent,'Ollama unavailable');
  console.log('PASS: explicit model selection, latest alias, startup preservation and offline controls');
})().catch(error=>{console.error(error);process.exitCode=1;});
