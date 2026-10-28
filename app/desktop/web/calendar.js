'use strict';
(()=>{
  const button=document.getElementById('import-calendar');
  const status=document.getElementById('calendar-status');
  button.addEventListener('click',async()=>{
    button.disabled=true;
    try{
      const api=window.pywebview?.api;
      if(!api?.choose_calendar)throw Error('Open the updated desktop app to import a calendar.');
      const result=await api.choose_calendar();
      status.textContent=result.reply;
    }catch(error){status.textContent='Calendar import failed: '+error.message;}
    finally{button.disabled=false;}
  });
})();
