'use strict';
// Opt-in per launch. No automatic microphone startup after a restart.
window.ArtemisHandsfree={enabled:false};
(()=>{
 const hf=window.ArtemisHandsfree;
 let checking=false,nextTurn=0,changing=false;
 const toggle=document.getElementById('handsfree-toggle');
 const hint=document.getElementById('handsfree-hint');
 const header=document.getElementById('handsfree-header'),mini=document.getElementById('handsfree-mini');
 let phase='Off';
 function show(){toggle.setAttribute('aria-pressed',String(hf.enabled));toggle.textContent=hf.enabled?'Stop hands-free':'Start hands-free';for(const b of [header,mini])if(b){b.textContent='Hands-free · '+phase;b.title=hint.textContent;b.setAttribute('aria-pressed',String(hf.enabled));}}
 function status(value){phase=value;show();}
 hf.stop=async(message)=>{
  hf.enabled=false;hint.textContent=message||'Hands-free is off. Start it when you are ready to speak.';status(message?.startsWith('Paused:')?'Paused':'Off');
  if(voiceActive){voiceUi(false);if(!busy)setState('idle');}
  try{await window.pywebview?.api?.set_handsfree(false)}catch(err){console.error(err)}
 };
 async function toggleMode(){
  if(hf.enabled){await hf.stop();return}
  if(changing)return;
  if(window.ArtemisSession?.quiet!==false){popup('Quiet mode is on. Hands-free stays off.');return}
  if(voiceActive){popup('Finish the current recording first.');return}
  changing=true;
  try{
   const result=await window.pywebview?.api?.set_handsfree(true);
   if(!result?.ok)throw Error(result?.error||'Desktop bridge unavailable');
   if(window.ArtemisSession?.quiet!==false){await hf.stop();return}
   hf.enabled=true;nextTurn=0;hint.textContent='Listening automatically between replies. Pause for about 1.2 seconds to send.';status('Starting');
   await tick();
  }catch(err){hint.textContent=err.message;status('Paused');popup(err.message)}finally{changing=false}
 }
 for(const button of [toggle,header,mini])if(button)button.addEventListener('click',toggleMode);
 async function tick(){
  if(!hf.enabled||checking)return;
  if(window.ArtemisSession?.quiet!==false){await hf.stop('Paused by Quiet mode.');return}
  if(busy){status('Replying');return}
  if(Date.now()<nextTurn)return;
  checking=true;
  try{
   const api=window.pywebview.api;
   const [voice,speech]=await Promise.all([api.voice_status(),api.speech_status()]);
   if(!hf.enabled||window.ArtemisSession?.quiet!==false||busy)return;
   if(speech.error){await hf.stop('Paused: '+speech.error);return}
   if(speech.playing){status('Speaking');nextTurn=Date.now()+650;return}
   if(voice.state==='error'){await hf.stop('Paused: '+(voice.error||'Recognition needs attention.'));return}
   if(voice.state==='listening'||voice.state==='transcribing'){status(voice.state==='listening'?'Listening':'Transcribing');return}
   // The existing poller must consume the transcript before a new turn starts.
   if(voice.state==='done'&&voice.revision!==voiceRevision)return;
   const result=await api.start_handsfree_turn();
   if(!result?.ok){
    if(result?.error?.includes('already in progress')){nextTurn=Date.now()+600;return}
    throw Error(result?.error||'Could not start listening');
   }
   if(!hf.enabled||window.ArtemisSession?.quiet!==false){await api.set_handsfree(false);return}
   status('Listening');voiceUi(true);$('headline').textContent='Listening…';$('subhead').textContent='Pause to send. Stop hands-free at any time.';$('status-label').textContent='LISTENING';
  }catch(err){await hf.stop('Paused: '+err.message)}finally{checking=false}
 }
 setInterval(tick,650);
 document.addEventListener('keydown',event=>{if(event.key==='Escape'&&hf.enabled)void hf.stop('Hands-free stopped.');});
 show();
})();
