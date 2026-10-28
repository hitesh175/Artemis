'use strict';
(()=>{
  const select=document.getElementById('chat-model');
  const status=document.getElementById('model-status');
  const refresh=document.getElementById('refresh-models');
  const save=document.getElementById('save-model');
  let loading=false;
  async function load(){
    if(loading)return;
    loading=true;refresh.disabled=true;save.disabled=true;select.disabled=true;
    try{
      const api=window.pywebview?.api;
      if(!api?.get_ollama_models)throw Error('Open the updated desktop app to choose a model.');
      const result=await api.get_ollama_models();
      if(!result.ok)throw Error(result.error);
      select.replaceChildren();
      const names=[...result.models];
      if(!names.includes(result.selected))names.unshift(result.selected);
      for(const name of names){
        const option=document.createElement('option');option.value=name;
        const installed=result.models.includes(name)||result.models.includes(name+':latest');
        option.textContent=name+(installed?'':' (not installed)');
        option.disabled=!installed;select.appendChild(option);
      }
      select.value=result.selected;save.disabled=false;select.disabled=false;
      status.textContent='Selected: '+result.selected+'. Changes apply to the next chat request.';
    }catch(error){status.textContent=error.message;}
    finally{loading=false;refresh.disabled=false;}
  }
  refresh.addEventListener('click',()=>void load());
  save.addEventListener('click',async()=>{
    if(loading)return;
    loading=true;save.disabled=true;refresh.disabled=true;select.disabled=true;
    try{
      const result=await window.pywebview.api.select_ollama_model(select.value);
      if(!result.ok)throw Error(result.error);
      status.textContent='Saved: '+result.selected+'. The next chat request will use this model.';
    }catch(error){status.textContent=error.message;}
    finally{loading=false;save.disabled=false;refresh.disabled=false;select.disabled=false;}
  });
  window.addEventListener('pywebviewready',()=>void load());
})();
