'use strict';
document.getElementById('find-apps').addEventListener('click',async()=>{
 const button=document.getElementById('find-apps'),list=document.getElementById('installed-apps');
 button.disabled=true;list.textContent='Finding installed apps…';
 try{
  const result=await window.pywebview?.api?.list_installed_apps();
  if(!result?.ok)throw Error(result?.error||'Use the Artemis desktop app.');
  list.replaceChildren();
  for(const name of result.apps){const item=document.createElement('div');item.textContent=name;list.appendChild(item)}
 }catch(err){list.textContent=err.message}finally{button.disabled=false}
});
