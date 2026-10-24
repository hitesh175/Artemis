'use strict';
// Native file storage survives changing localhost ports and private WebView sessions.
window.ArtemisSession={quiet:true,ready:false};
(()=>{
 const session=window.ArtemisSession;
 let prefs={quiet:true,speechEnabled:true,speed:100,scale:100,reduceMotion:false,autoSend:true};
 let savedHistory=[],saving=Promise.resolve(),revision=0;
 const byId=id=>document.getElementById(id);
 function note(text){const el=byId('save-status');if(el)el.textContent=text;}
 function showQuiet(){
  session.quiet=prefs.quiet;
  byId('quiet-toggle').textContent=prefs.quiet?'Quiet mode · ON':'Quiet mode · OFF';
  byId('quiet-toggle').setAttribute('aria-pressed',String(prefs.quiet));
  byId('quiet-setting').checked=prefs.quiet;
  byId('voice-button').disabled=prefs.quiet;
  byId('voice-button').title=prefs.quiet?'Quiet mode: use text chat':'Record with Whisper';
 }
 function save(){
  if(!session.ready)return Promise.resolve(false);
  const data=JSON.parse(JSON.stringify({preferences:prefs,history:savedHistory}));
  const version=++revision;
  note('Saving…');
  saving=saving.catch(()=>{}).then(async()=>{
   try{
    const result=await window.pywebview.api.save_desktop_state(data);
    if(!result?.ok)throw Error(result?.error||'Save failed');
    if(version===revision)note('Saved on this device');
    return true;
   }catch(err){note('Not saved · '+err.message);return false;}
  });
  return saving;
 }
 session.flush=()=>saving;
 session.saveHistory=messages=>{savedHistory=messages.slice(-100);return save();};
 session.setSpeechPreference=enabled=>{prefs.speechEnabled=Boolean(enabled);return save();};
 async function quiet(value){
  prefs.quiet=Boolean(value);showQuiet();
  // Guard the browser immediately, then persist and apply the native mute.
  if(prefs.quiet){
   await window.ArtemisHandsfree?.stop('Paused by Quiet mode.');
   const api=window.pywebview?.api;
   if(api?.set_speech_enabled)await api.set_speech_enabled(false).catch(()=>{});
   openPanel('chat');
  }
  await save();
 }
 async function init(){
  if(session.ready||session.loading)return;
  const api=window.pywebview?.api;
  if(!api?.load_desktop_state){note('Desktop storage unavailable');return;}
  session.loading=true;
  try{
   const result=await api.load_desktop_state();
   if(!result?.ok)throw Error(result?.error||'Could not load saved state');
   prefs={...prefs,...result.preferences};savedHistory=result.history||[];
   history=savedHistory.slice();
   if(history.length){byId('messages').replaceChildren();for(const item of history)bubble(item.role,item.content);}
   byId('animation-speed').value=prefs.speed;
   byId('orb-scale').value=prefs.scale;
   byId('reduce-motion').checked=prefs.reduceMotion;
   byId('auto-send-voice').checked=prefs.autoSend;
   speed=prefs.reduceMotion?0:prefs.speed/100;
   byId('speed-value').textContent=speed.toFixed(1)+'×';
   document.documentElement.style.setProperty('--orb-scale',String(prefs.scale/100));
   byId('scale-value').textContent=prefs.scale+'%';
   if(typeof syncIconMotion==='function')syncIconMotion();
   speechOn=!prefs.quiet&&prefs.speechEnabled;updateSpeechButton();showQuiet();
   session.ready=true;note('Saved on this device');
   if(prefs.quiet)openPanel('chat');
  }catch(err){note('Could not restore · '+err.message);}
  finally{session.loading=false;byId('chat-input').disabled=!session.ready;byId('send').disabled=!session.ready;byId('quiet-toggle').disabled=!session.ready;byId('quiet-setting').disabled=!session.ready;}
 }
 byId('voice-button').disabled=true;
 byId('quiet-toggle').disabled=true;byId('quiet-setting').disabled=true;
 byId('chat-input').disabled=true;byId('send').disabled=true;
 byId('quiet-toggle').addEventListener('click',()=>quiet(!prefs.quiet));
 byId('quiet-setting').addEventListener('change',e=>quiet(e.target.checked));
 for(const id of ['animation-speed','orb-scale','reduce-motion','auto-send-voice'])byId(id).addEventListener('change',()=>{
  prefs.speed=Number(byId('animation-speed').value);prefs.scale=Number(byId('orb-scale').value);
  prefs.reduceMotion=byId('reduce-motion').checked;prefs.autoSend=byId('auto-send-voice').checked;save();
 });
 window.addEventListener('pywebviewready',init);init();
})();

