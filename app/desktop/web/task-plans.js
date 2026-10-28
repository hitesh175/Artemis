'use strict';
const activeArtemisTaskPlans=new Set();
window.hasRunningTaskPlan=()=>activeArtemisTaskPlans.size>0;
window.renderTaskPlan=(host,current)=>{
  const plan=current.task_plan;
  if(!plan)return;
  const controls=document.createElement('div');
  let requesting=false;
  async function act(method){
    if(requesting && method!=='cancel_task_plan')return;
    if(method!=='cancel_task_plan')requesting=true;
    if(method==='run_task_plan')activeArtemisTaskPlans.add(plan.token);
    for(const button of controls.querySelectorAll('button')){
      if(button.dataset.action!=='cancel_task_plan')button.disabled=true;
    }
    try{
      await window.ArtemisHandsfree?.stop('Task plan is under manual control.');
      const result=await window.pywebview.api[method](plan.token);
      if(!result.task_plan){activeArtemisTaskPlans.delete(plan.token);throw Error(result.reply||'Task plan unavailable.');}
      if(result.task_plan.revision<current.task_plan.revision)return;
      if(['completed','failed','cancelled','expired'].includes(result.task_plan.phase))activeArtemisTaskPlans.delete(plan.token);
      window.updateTaskPlanHistory?.(current.reply,result.reply);
      current=result;
      host.textContent=result.reply;
      if(method!=='cancel_task_plan' && result.task_plan.phase==='running'){
        host.appendChild(document.createTextNode('\nA run is already in progress.'));
      }
      window.renderTaskPlan(host,result);
    }catch(error){
      const note=document.createElement('p');note.textContent=error.message;host.appendChild(note);
      // A lost response must not turn a possibly executed plan into a new run.
    }
  }
  function button(label,method){
    const node=document.createElement('button');node.className='app-confirm';node.textContent=label;node.dataset.action=method;
    if(method==='cancel_task_plan'&&plan.cancelling)node.disabled=true;
    node.addEventListener('click',()=>void act(method));controls.appendChild(node);
  }
  if(plan.phase==='preview')button('Run these steps','run_task_plan');
  if(plan.phase==='needs_confirmation')button('Open '+plan.app_name+' and finish','confirm_task_app');
  if(['preview','running','needs_confirmation'].includes(plan.phase))button(plan.cancelling?'Stopping after current step…':'Cancel plan','cancel_task_plan');
  host.appendChild(controls);
};
