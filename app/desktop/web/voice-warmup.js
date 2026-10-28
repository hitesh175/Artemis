'use strict';
(()=>{
  const button=document.getElementById('warm-voice-models');
  const status=document.getElementById('voice-warmup-status');
  let watching=false;
  async function poll(){
    if(!watching)return;
    try{
      const result=await window.pywebview.api.voice_warmup_status();
      if(result.state==='loading')status.textContent='Preparing '+result.stage+' silently…';
      else{
        watching=false;button.disabled=false;
        status.textContent=result.results.map(step=>step.component+': '+(step.ready?'ready ('+step.model+', '+step.seconds+' s)':step.error)).join('\n')+
          '\nTotal: '+result.seconds+' s. No microphone or playback was used.';
      }
    }catch(error){watching=false;button.disabled=false;status.textContent=error.message;}
  }
  button.addEventListener('click',async()=>{
    button.disabled=true;
    try{
      const api=window.pywebview?.api;
      if(!api?.warm_voice_models)throw Error('Open the updated desktop app to prepare voice models.');
      const result=await api.warm_voice_models();
      if(!result.ok)throw Error(result.error);
      watching=true;void poll();
    }catch(error){button.disabled=false;status.textContent=error.message;}
  });
  setInterval(poll,500);
})();
