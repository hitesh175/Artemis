const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm'),path=require('node:path');
class Element{
  constructor(){this.children=[];this.events={};this.dataset={};this.disabled=false;this._text='';}
  set textContent(value){this._text=value;this.children=[];}
  get textContent(){return this._text;}
  appendChild(node){this.children.push(node);}
  addEventListener(name,handler){this.events[name]=handler;}
  querySelectorAll(){return this.children.filter(child=>child.events.click);}
}
(async()=>{
  let calls=0,resolveRun;
  const changes=[];
  const api={run_task_plan:()=>{calls++;return new Promise(resolve=>resolveRun=resolve);}};
  const context={window:{pywebview:{api},ArtemisHandsfree:{stop:async()=>{}},updateTaskPlanHistory:(before,after)=>changes.push([before,after])},
    document:{createElement:()=>new Element(),createTextNode:text=>({textContent:text})},Set};
  vm.runInNewContext(fs.readFileSync(path.join(__dirname,'../app/desktop/web/task-plans.js'),'utf8'),context);
  const host=new Element();host.textContent='Preview';
  context.window.renderTaskPlan(host,{reply:'Preview',task_plan:{token:'opaque-plan',phase:'preview',revision:1}});
  assert.equal(calls,0,'Rendering a plan must not run it');
  const controls=host.children[0];const run=controls.children[0];
  run.events.click();run.events.click();await new Promise(resolve=>setImmediate(resolve));
  assert.equal(calls,1,'Double clicks must not start another execution');
  assert(context.window.hasRunningTaskPlan());
  resolveRun({reply:'Finished',task_plan:{token:'opaque-plan',phase:'completed',revision:2}});
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(host.textContent,'Finished');assert(!context.window.hasRunningTaskPlan());
  assert.deepEqual(changes,[['Preview','Finished']]);
  assert.equal(host.children[0].children.length,0,'Completed plans have no run controls');
  api.run_task_plan=async()=>({ok:false,reply:'Plan no longer available'});
  const expired=new Element();
  context.window.renderTaskPlan(expired,{reply:'Old preview',task_plan:{token:'expired-plan',phase:'preview',revision:1}});
  expired.children[0].children[0].events.click();await new Promise(resolve=>setImmediate(resolve));
  assert(!context.window.hasRunningTaskPlan(),'An unavailable plan must not block clearing chat');
  console.log('PASS: reviewed-only UI execution, double-click protection, active-plan tracking and saved result updates');
})().catch(error=>{console.error(error);process.exitCode=1;});
