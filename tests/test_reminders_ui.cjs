const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const vm=require('node:vm');
class Element {
  constructor(){this.children=[];this.events={};this.textContent='';this.hidden=true;this.replacements=0;}
  replaceChildren(){this.children=[];this.replacements++;}
  append(...children){this.children.push(...children);}
  appendChild(child){this.children.push(child);}
  setAttribute(){}
  addEventListener(name,handler){this.events[name]=handler;}
}
(async()=>{
  const elements=Object.fromEntries(['reminder-inbox','reminder-status','check-reminders'].map(id=>[id,new Element()]));
  let reminders=[{id:1,text:'<script>literal reminder</script>',due_local:'2026-10-28T09:00+01:00',overdue:true}];
  let failure=false,calls=0;
  const api={
    async due_reminders(){calls++;return failure?{ok:false,error:'Database unavailable'}:{ok:true,reminders};},
    async dismiss_reminder(id){assert.equal(id,1);reminders=[];return {ok:true};}
  };
  const context={window:{pywebview:{api},addEventListener(){}},
    document:{getElementById:id=>elements[id],createElement:()=>new Element(),addEventListener(){}},setInterval(){}};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/desktop/web/reminders.js'),'utf8'),context);
  const flush=()=>new Promise(resolve=>setImmediate(resolve));
  await flush();
  const inbox=elements['reminder-inbox'];
  assert.equal(inbox.hidden,false);
  assert.match(inbox.children[0].children[0].textContent,/Overdue reminder 1: <script>/);
  assert.equal(inbox.children[0].children[0].children.length,0,'Reminder must render as text');
  const count=inbox.replacements;
  elements['check-reminders'].events.click();await flush();
  assert.equal(inbox.replacements,count,'Unchanged polling must preserve focused controls');
  await inbox.children[0].children[1].events.click();await flush();
  assert.equal(inbox.hidden,true);
  failure=true;elements['check-reminders'].events.click();await flush();
  assert.equal(elements['reminder-status'].textContent,'Database unavailable');
  assert(calls>=4);
  console.log('PASS: visual overdue inbox, inert text, stable polling, dismissal and service errors');
})().catch(error=>{console.error(error);process.exitCode=1;});
