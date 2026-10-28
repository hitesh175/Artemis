/* Visual reminders remain visible until acknowledged; never start audio. */
'use strict';
(()=>{
  const inbox=document.getElementById('reminder-inbox');
  const status=document.getElementById('reminder-status');
  let checking=false,last='';
  async function check(){
    const api=window.pywebview?.api;
    if(!api?.due_reminders||checking)return;
    checking=true;
    try{
      const result=await api.due_reminders();
      if(!result.ok)throw Error(result.error||'Could not check reminders.');
      status.textContent='Reminders checked. Artemis must be open to show due reminders.';
      const fingerprint=JSON.stringify(result.reminders);
      if(fingerprint===last)return;
      last=fingerprint;inbox.replaceChildren();inbox.hidden=!result.reminders.length;
      for(const reminder of result.reminders){
        const row=document.createElement('div');
        const text=document.createElement('p');
        text.textContent=`${reminder.overdue?'Overdue reminder':'Reminder'} ${reminder.id}: ${reminder.text} · Due ${reminder.due_local}`;
        const dismiss=document.createElement('button');dismiss.textContent='Dismiss';
        dismiss.setAttribute('aria-label',`Dismiss reminder ${reminder.id}`);
        dismiss.addEventListener('click',async()=>{
          dismiss.disabled=true;
          try{
            const result=await api.dismiss_reminder(reminder.id);
            if(!result.ok)throw Error(result.error||'Reminder is no longer active.');
            last='';void check();
          }catch(error){status.textContent=error.message;dismiss.disabled=false;}
        });
        row.append(text,dismiss);inbox.appendChild(row);
      }
    }catch(error){status.textContent=error.message;}
    finally{checking=false;}
  }
  window.addEventListener('pywebviewready',check);
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)void check();});
  document.getElementById('check-reminders').addEventListener('click',()=>void check());
  setInterval(check,5000);void check();
})();
