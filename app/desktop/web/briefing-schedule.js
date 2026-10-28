'use strict';
(()=>{
  const enabled=document.getElementById('schedule-briefing-enabled');
  const at=document.getElementById('schedule-briefing-time');
  const save=document.getElementById('save-briefing-schedule');
  const status=document.getElementById('briefing-schedule-status');
  const notice=document.getElementById('scheduled-briefing-notice');
  let checking=false,saving=false,loaded=false,last='';
  async function check(){
    const api=window.pywebview?.api;
    if(!loaded||checking||saving||!api?.check_scheduled_briefing)return;
    checking=true;
    save.disabled=true;
    try{
      const result=await api.check_scheduled_briefing();
      if(!result.ok)throw Error(result.error);
      status.textContent=result.enabled?'Enabled at '+result.time+' in the computer local timezone. Visual notices only.':'Scheduled briefings are off.';
      const pending=result.pending;
      const fingerprint=JSON.stringify(pending);
      if(fingerprint===last)return;
      last=fingerprint;notice.replaceChildren();notice.hidden=!pending;
      if(pending){
        const details=document.createElement('details');
        const title=document.createElement('summary');title.textContent='Daily briefing ready · '+pending.date;
        const content=document.createElement('p');content.textContent=pending.reply;
        const dismiss=document.createElement('button');dismiss.textContent='Dismiss briefing';
        dismiss.addEventListener('click',async()=>{
          dismiss.disabled=true;
          try{
            const response=await api.dismiss_scheduled_briefing(pending.date);
            if(!response.ok)throw Error(response.error||'This briefing changed. Refresh to see the latest.');
            last='';void check();
          }catch(error){status.textContent=error.message;dismiss.disabled=false;}
        });
        details.append(title,content,dismiss);notice.appendChild(details);
      }
    }catch(error){status.textContent=error.message;}
    finally{checking=false;if(loaded&&!saving)save.disabled=false;}
  }
  async function load(){
    try{
      const result=await window.pywebview.api.get_briefing_schedule();
      if(!result.ok)throw Error(result.error);
      enabled.checked=result.enabled;at.value=result.time;save.disabled=false;loaded=true;
      status.textContent=result.enabled?'Enabled at '+result.time+' in the computer local timezone.':'Scheduled briefings are off.';
      void check();
    }catch(error){status.textContent=error.message;}
  }
  save.addEventListener('click',async()=>{
    if(saving||checking)return;
    saving=true;save.disabled=true;
    try{
      const result=await window.pywebview.api.set_briefing_schedule(enabled.checked,at.value);
      if(!result.ok)throw Error(result.error);
      status.textContent=result.enabled?'Enabled at '+result.time+'. Briefings are visual and require Artemis to be open.':'Scheduled briefings are off.';
    }catch(error){status.textContent=error.message;}
    finally{saving=false;save.disabled=false;void check();}
  });
  window.addEventListener('pywebviewready',()=>void load());
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)void check();});
  setInterval(check,30000);
})();
