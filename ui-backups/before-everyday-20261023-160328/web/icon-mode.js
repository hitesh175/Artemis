'use strict';
window.setArtemisVisualMode=function(mode){
 const app=document.querySelector('.app');
 if(!app)return;
 const known=['idle','listening','thinking','transcribing','speaking','error'];
 app.dataset.mode=known.includes(mode)?mode:'idle';
 if(mode!=='listening')app.style.setProperty('--voice-level','0');
 const mark=document.querySelector('.icon-mark');
 if(mark)mark.setAttribute('aria-label','Artemis · '+(mode==='idle'?'ready':mode));
};
window.setArtemisVisualMode('idle');
window.setArtemisVoiceLevel=function(level){
 const app=document.querySelector('.app');
 const v=Number(level);
 const safe=Number.isFinite(v)?Math.max(0,Math.min(1,v)):0;
 app.style.setProperty('--voice-level',app.dataset.mode==='listening'?String(safe):'0');
};
function syncIconMotion(){
 const app=document.querySelector('.app');
 const value=Number(document.getElementById('animation-speed').value)/100;
 app.classList.toggle('icon-motion-off',document.getElementById('reduce-motion').checked||value===0);
 if(value>0){
  app.style.setProperty('--trace-duration',(8/value)+'s');
  app.style.setProperty('--orbit-duration',(6/value)+'s');
  app.style.setProperty('--pulse-duration',(2.2/value)+'s');
 }
}
document.getElementById('animation-speed').addEventListener('input',syncIconMotion);
document.getElementById('reduce-motion').addEventListener('change',()=>queueMicrotask(syncIconMotion));
