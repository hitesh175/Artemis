'use strict';
(()=>{
 let mode='full',busy=false;
 const app=document.querySelector('.app'),el=id=>document.getElementById(id);
 function apply(result){
  mode=result.mode;app.dataset.layout=mode;
  el('mini-pin').setAttribute('aria-pressed',String(result.onTop));
  el('mini-pin').textContent=result.onTop?'Pinned':'Pin';
  if(mode==='mini')closePanels();
  if(mode==='chat')originalOpen('chat');
  if(mode==='full')closePanels();
  syncFullscreenButton(false);
 }
 async function change(next){
  if(busy)return;busy=true;
  try{
   const api=window.pywebview?.api;
   if(!api?.set_mini_mode)throw Error('Mini Artemis requires the desktop window.');
   const result=await api.set_mini_mode(next);
   if(!result?.ok)throw Error(result?.error||'Could not change layout');
   apply(result);
  }catch(err){popup(err.message)}finally{busy=false}
 }
 const originalOpen=openPanel;
 openPanel=function(name){
  if(mode==='mini'&&name==='chat'){void change('chat');return;}
  originalOpen(name);
 };
 el('mini-open').addEventListener('click',()=>change('mini'));
 el('mini-full').addEventListener('click',()=>change('full'));
 el('mini-collapse').addEventListener('click',()=>change('mini'));
 el('mini-icon-open').addEventListener('click',()=>change('chat'));
 el('mini-chat-open').addEventListener('click',()=>change('chat'));
 el('chat-close').addEventListener('click',()=>{if(mode==='chat')void change('mini')});
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&mode==='chat')void change('mini')});
 el('mini-pin').addEventListener('click',async()=>{
  try{
   const result=await window.pywebview.api.set_mini_top(el('mini-pin').getAttribute('aria-pressed')!=='true');
   if(!result?.ok)throw Error(result?.error||'Pin failed');
   el('mini-pin').setAttribute('aria-pressed',String(result.onTop));el('mini-pin').textContent=result.onTop?'Pinned':'Pin';
  }catch(err){popup(err.message)}
 });
 el('mini-quiet').addEventListener('click',()=>el('quiet-toggle').click());
 function quietLabel(){el('mini-quiet').textContent=el('quiet-toggle').textContent;el('mini-quiet').disabled=el('quiet-toggle').disabled;}
 new MutationObserver(quietLabel).observe(el('quiet-toggle'),{childList:true,attributes:true,characterData:true,subtree:true});quietLabel();
})();
