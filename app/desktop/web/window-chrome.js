'use strict';
(()=>{
 let pending=false;
 async function action(name){
  if(pending)return;pending=true;
  try{
   const api=window.pywebview?.api;
   if(!api?.window_action)throw Error('Window controls require the desktop app.');
   if(name==='close'&&window.ArtemisSession?.flush){
    await Promise.race([window.ArtemisSession.flush(),new Promise(resolve=>setTimeout(resolve,2500))]);
   }
   const result=await api.window_action(name);
   if(!result?.ok)throw Error(result?.error||'Window action failed');
   if(name==='maximize'){
    const b=document.getElementById('window-maximize');
    b.title=result.maximized?'Restore window':'Maximize window';
    b.setAttribute('aria-label',b.title);
   }
  }catch(err){popup(err.message)}finally{pending=false}
 }
 for(const name of ['minimize','maximize','close'])document.getElementById('window-'+name).addEventListener('click',()=>action(name));
 document.getElementById('window-drag').addEventListener('dblclick',()=>{
  const mode=document.querySelector('.app').dataset.layout;
  if(!mode||mode==='full')void action('maximize');
 });
})();
