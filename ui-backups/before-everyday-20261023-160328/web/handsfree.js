'use strict';
// Opt-in per launch. No automatic microphone startup after a restart.
window.ArtemisHandsfree={enabled:false};
(()=>{
 const hf=window.ArtemisHandsfree;
 let checking=false,nextTurn=0;
 const toggle=document.getElementById('handsfree-toggle');
 const hint=document.getElementById('handsfree-hint');
 function show(){toggle.setAttribute('aria-pressed',String(hf.enabled));toggle.textContent=hf.enabled?'Stop hands-free':'Start hands-free';}
 hf.stop=async(message)=>{
  hf.enabled=false;show();hint.textContent=message||'Hands-free is off. Start it when you are ready to speak.';
  if(voiceActive){voiceUi(false);if(!busy)setState('idle');}
  try{await window.pywebview?.api?.set_handsfree(false)}catch(err){console.error(err)}
 };
 toggle.addEventListener('click',async()=>{
  if(hf.enabled){await hf.stop();return}
  if(window.ArtemisSession?.quiet!==false){popup('Quiet mode is on. Hands-free stays off.');return}
  if(voiceActive){popup('Finish the current recording first.');return}
  try{
   const result=await window.pywebview?.api?.set_handsfree(true);
   if(!result?.ok)throw Error(result?.error||'Desktop bridge unavailable');
   if(window.ArtemisSession?.quiet!==false){await hf.stop();return}
   hf.enabled=true;nextTurn=0;show();hint.textContent='Listening automatically between replies. Pause for about 1.2 seconds to send.';
   await tick();
  }catch(err){popup(err.message)}
 });
 async function tick(){
  if(!hf.enabled||checking)return;
  if(window.ArtemisSession?.quiet!==false){await hf.stop('Paused by Quiet mode.');return}
  if(busy||Date.now()<nextTurn)return;
  checking=true;
  try{
   const api=window.pywebview.api;
   const [voice,speech]=await Promise.all([api.voice_status(),api.speech_status()]);
   if(!hf.enabled||window.ArtemisSession?.quiet!==false||busy)return;
   if(speech.error){await hf.stop('Paused: '+speech.error);return}
   if(speech.playing){nextTurn=Date.now()+650;return}
   if(voice.state==='error'){await hf.stop('Paused: '+(voice.error||'Recognition needs attention.'));return}
   if(voice.state==='listening'||voice.state==='transcribing')return;
   // The existing poller must consume the transcript before a new turn starts.
   if(voice.state==='done'&&voice.revision!==voiceRevision)return;
   const result=await api.start_handsfree_turn();
   if(!result?.ok){
    if(result?.error?.includes('already in progress')){nextTurn=Date.now()+600;return}
    throw Error(result?.error||'Could not start listening');
   }
   if(!hf.enabled||window.ArtemisSession?.quiet!==false){await api.set_handsfree(false);return}
   voiceUi(true);$('headline').textContent='Listening…';$('subhead').textContent='Pause to send. Stop hands-free at any time.';$('status-label').textContent='LISTENING';
  }catch(err){await hf.stop('Paused: '+err.message)}finally{checking=false}
 }
 setInterval(tick,650);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&hf.enabled)void hf.stop('Hands-free stopped.');});
 show();
})();
