/* One owner for overlay focus and Settings navigation. */
'use strict';
window.ArtemisPanels=(()=>{
 const panels=[...document.querySelectorAll('.sidepanel')];
 const backgrounds=[...document.querySelectorAll('.topbar,.center')];
 const previous=new Map();let active=null,opener=null;
 const visible=e=>e&&e.isConnected&&!e.disabled&&!e.closest('[hidden],[inert]')&&e.getClientRects().length>0;
 const focusable=()=>active?[...active.querySelectorAll('button,input,select,summary,a[href],[tabindex="0"]')].filter(visible):[];
 function open(name){
  const next=document.getElementById(name+'-panel');if(!next)return;
  if(!active){opener=visible(document.activeElement)&&document.activeElement!==document.body?document.activeElement:document.getElementById(name==='chat'?'chat-open':'settings-open');}
  active=next;
  const compactChat=document.querySelector('.app').dataset.layout==='chat';
  next.setAttribute('role',compactChat?'region':'dialog');
  if(compactChat)next.removeAttribute('aria-modal');else next.setAttribute('aria-modal','true');
  panels.forEach(panel=>{const yes=panel===next;panel.inert=!yes;panel.classList.toggle('open',yes);panel.setAttribute('aria-hidden',String(!yes));});
  backgrounds.forEach(el=>{if(!previous.has(el))previous.set(el,el.inert);el.inert=true;});
  document.body.classList.add('panel-open');document.getElementById('veil').hidden=false;
  const target=name==='chat'?document.getElementById('chat-input'):next.querySelector('h2');
  (visible(target)?target:focusable()[0])?.focus({preventScroll:true});
 }
 function close(){
  const hadPanel=Boolean(active);active=null;
  panels.forEach(panel=>{panel.inert=true;panel.classList.remove('open');panel.setAttribute('aria-hidden','true');});
  previous.forEach((value,el)=>{el.inert=value;});previous.clear();
  document.body.classList.remove('panel-open');document.getElementById('veil').hidden=true;
  if(hadPanel){const fallback=['mini-icon-open','mini-chat-open','chat-open','settings-open'].map(id=>document.getElementById(id)).find(visible);(visible(opener)?opener:fallback)?.focus({preventScroll:true});}opener=null;
 }
 panels.forEach(panel=>{panel.inert=true;panel.setAttribute('role','dialog');panel.setAttribute('aria-modal','true');const title=panel.querySelector('h2');title.id=panel.id+'-title';title.tabIndex=-1;panel.setAttribute('aria-labelledby',title.id);});
 document.addEventListener('keydown',event=>{
  if(event.key!=='Tab'||!active||document.querySelector('.app').dataset.layout==='chat')return;
  const items=focusable();if(!items.length){event.preventDefault();active.querySelector('h2').focus();return;}
  const index=items.indexOf(document.activeElement);
  if(index===-1||(!event.shiftKey&&index===items.length-1)||(event.shiftKey&&index===0)){
   event.preventDefault();items[event.shiftKey?items.length-1:0].focus();
  }
 });
 const groups={General:['quiet-mode','appearance'],Voice:['hands-free-conversation','conversation','voice-preparation'],Daily:['calendar','scheduled-daily-briefing','daily-briefing'],Tools:['everyday','open-apps','task-plans','reminders'],Knowledge:['documents','personal-memory'],System:['performance','service-status','local-intelligence']};
 const picker=document.getElementById('settings-category');
 const sections=[...document.querySelectorAll('.settings-section')];
 function category(name){
  if(!groups[name])return;
  picker.value=name;
  sections.forEach(section=>{section.hidden=!groups[name].some(id=>section.getAttribute('aria-labelledby')==='setting-'+id);});
  document.querySelector('.settings-content').scrollTop=0;
 }
 picker.addEventListener('change',()=>category(picker.value));category('General');
 window.showArtemisSettingsSection=id=>{const group=Object.keys(groups).find(name=>groups[name].some(key=>id==='setting-'+key));if(group)category(group);};
 return {open,close};
})();
