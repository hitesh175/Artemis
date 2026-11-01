/* Announce completed replies once; never replay history or streamed fragments. */
'use strict';
window.ArtemisChatAccessibility=(()=>{
 const messages=document.getElementById('messages'),notice=document.getElementById('chat-announcement');
 let timer=null;
 function start(){clearTimeout(timer);notice.textContent='';messages.setAttribute('aria-busy','true');}
 function finish(text){
  messages.setAttribute('aria-busy','false');clearTimeout(timer);
  notice.textContent='';
  timer=setTimeout(()=>{notice.textContent='Artemis: '+String(text);},80);
 }
 return {start,finish};
})();
