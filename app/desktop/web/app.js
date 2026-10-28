'use strict';
const $=id=>document.getElementById(id);
let speed=1,time=0,frameLast=performance.now(),shaderState=0,gl,program,uniforms,lastDraw=0;
const nativeQt = false; // WebView2 successfully supports the real WebGL2 material.
if(nativeQt) document.documentElement.classList.add('qt-embedded');
const stateInfo={idle:[0,'Ready when you are.','Your private AI companion, always close at hand.','READY'],thinking:[.35,'Thinking…','Working on your reply.','THINKING'],speaking:[.55,'Artemis is here.','Your response is ready in chat.','READY'],error:[.95,'Connection needs attention.','Please check your local Ollama service.','ERROR']};
function setState(name){window.setArtemisVisualMode?.(name);let s=stateInfo[name]||stateInfo.idle;shaderState=s[0];$('headline').textContent=s[1];$('subhead').textContent=s[2];$('status-label').textContent=s[3];$('status-dot').style.background=name==='error'?'#e997a5':'#99e4cb'}
function popup(msg){$('toast').textContent=msg;$('toast').hidden=false;clearTimeout(popup.timer);popup.timer=setTimeout(()=>$('toast').hidden=true,4300)}
function compile(type,src){const sh=gl.createShader(type);gl.shaderSource(sh,src);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(sh));return sh}
$('orb').addEventListener('webglcontextlost',e=>{e.preventDefault();gl=null;showFallback('Graphics context lost');popup('Animation paused after a graphics interruption. Other controls remain available.');});
function initGlass(){if(document.querySelector(".icon-stage"))return;try{const canvas=$('orb');gl=canvas.getContext('webgl2',{alpha:true,antialias:true,premultipliedAlpha:false,powerPreference:'high-performance'});if(!gl)throw Error('WebGL2 is not available');program=gl.createProgram();gl.attachShader(program,compile(gl.VERTEX_SHADER,vertexSource));gl.attachShader(program,compile(gl.FRAGMENT_SHADER,fragmentSource));gl.linkProgram(program);if(!gl.getProgramParameter(program,gl.LINK_STATUS))throw Error(gl.getProgramInfoLog(program));gl.useProgram(program);const verts=new Float32Array([-1,-1,1,-1,-1,1,-1,1,1,-1,1,1]);const buf=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buf);gl.bufferData(gl.ARRAY_BUFFER,verts,gl.STATIC_DRAW);const a=gl.getAttribLocation(program,'a');gl.enableVertexAttribArray(a);gl.vertexAttribPointer(a,2,gl.FLOAT,false,0,0);uniforms={};for(const n of ['res','t','crystal','water','motion','state'])uniforms[n]=gl.getUniformLocation(program,n);gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);requestAnimationFrame(render)}catch(err){showFallback('Browser graphics fallback');console.error(err)}}
function showFallback(reason){const canvas=$('orb');canvas.style.display='none';const el=$('orb-fallback');el.hidden=false;el.setAttribute('aria-label',reason);const check=new Image();check.onload=()=>{el.style.backgroundImage='url(\"/assets/orb_native_fallback.png\")'};check.onerror=()=>{el.style.backgroundImage='none';el.style.color='#eaf3ff';el.style.fontSize='14px';el.textContent='Artemis visual asset could not load. Please reinstall the desktop/assets folder.';console.error('Missing local orb fallback artwork')};check.src='/assets/orb_native_fallback.png';}
function render(now){if(!gl||document.hidden){frameLast=now;requestAnimationFrame(render);return;}if(now-lastDraw<1000/30){requestAnimationFrame(render);return;}lastDraw=now;let dt=Math.min((now-frameLast)/1000,.05);frameLast=now;time+=dt*speed;const canvas=$('orb');let ratio=Math.min(devicePixelRatio||1,1,900/Math.max(1,canvas.clientWidth),600/Math.max(1,canvas.clientHeight)),w=Math.max(1,Math.round(canvas.clientWidth*ratio)),h=Math.max(1,Math.round(canvas.clientHeight*ratio));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}gl.viewport(0,0,w,h);gl.clearColor(0,0,0,0);gl.clear(gl.COLOR_BUFFER_BIT);gl.uniform2f(uniforms.res,w,h);gl.uniform1f(uniforms.t,time);gl.uniform1f(uniforms.crystal,.5);gl.uniform1f(uniforms.water,.5);gl.uniform1f(uniforms.motion,speed);gl.uniform1f(uniforms.state,shaderState);gl.drawArrays(gl.TRIANGLES,0,6);requestAnimationFrame(render)}
const panels={chat:$('chat-panel'),settings:$('settings-panel')};function openPanel(name){Object.entries(panels).forEach(([n,el])=>{let active=n===name;el.classList.toggle('open',active);el.setAttribute('aria-hidden',String(!active))});$('veil').hidden=false;if(name==='chat')$('chat-input').focus()}
function closePanels(){Object.values(panels).forEach(el=>{el.classList.remove('open');el.setAttribute('aria-hidden','true')});$('veil').hidden=true}
$('chat-open').addEventListener('click',()=>openPanel('chat'));
let fullscreenBusy=false;
async function setArtemisFullscreen(value){
  if(fullscreenBusy)return;
  fullscreenBusy=true;
  try{
    const api=window.pywebview?.api;
    if(api?.set_fullscreen){
      const result=await api.set_fullscreen(value);
      if(!result?.ok) throw Error(result?.error||'Native fullscreen failed');
      syncFullscreenButton(Boolean(result.fullscreen));
    } else if(!window.pywebview){
      if(value && !document.fullscreenElement)await document.documentElement.requestFullscreen();
      if(!value && document.fullscreenElement)await document.exitFullscreen();
      syncFullscreenButton(Boolean(document.fullscreenElement));
    } else popup('Native window bridge not ready.');
  } catch(err){popup('Fullscreen: '+err.message)}
  finally{fullscreenBusy=false}
}
function syncFullscreenButton(yes){
  const b=$('expand-button');
  b.setAttribute('aria-label',yes?'Exit fullscreen':'Enter fullscreen');
  b.title=yes?'Exit fullscreen':'Fullscreen';
}
async function toggleArtemisFullscreen(){
  const api=window.pywebview?.api;
  if(api?.get_fullscreen){
    const result=await api.get_fullscreen();
    if(result?.ok){await setArtemisFullscreen(!result.fullscreen);return}
  }
  await setArtemisFullscreen(!document.fullscreenElement);
}
$('expand-button').addEventListener('click',toggleArtemisFullscreen);
document.addEventListener('keydown',async e=>{
  if(e.key==='F11'){e.preventDefault();await toggleArtemisFullscreen()}
  else if(e.key==='Escape'){
    closePanels();
    const api=window.pywebview?.api;
    if(api?.get_fullscreen){
      const state=await api.get_fullscreen();
      if(state?.fullscreen){e.preventDefault();await setArtemisFullscreen(false)}
    }else if(document.fullscreenElement){e.preventDefault();await setArtemisFullscreen(false)}
  }
});
// Quiet keyboard shortcuts for accessible navigation; no changes to voice or WebGL.
document.addEventListener('keydown',e=>{
  if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){
    e.preventDefault();openPanel('chat');$('chat-input').focus();
  }
});
$('settings-open').addEventListener('click',()=>openPanel('settings'));
$('chat-close').addEventListener('click',closePanels);
$('settings-close').addEventListener('click',closePanels);
$('veil').addEventListener('click',closePanels);
let voiceRevision=0, voicePolling=false, voiceActive=false;
function voiceUi(active){window.setArtemisVisualMode?.(active?"listening":"transcribing");voiceActive=active;const b=$('voice-button');b.classList.toggle('recording',active);b.title=active?'Stop recording and transcribe':'Record with Whisper';b.setAttribute('aria-label',active?'Stop recording':'Start voice recognition')}
async function voicePoll(){
  if(voicePolling)return;voicePolling=true;
  try{
    const api=window.pywebview?.api;
    if(!api?.voice_status)return;
    const v=await api.voice_status();
    // Meter changes independently of transcription-state revisions.
    window.setArtemisVoiceLevel?.(v.state==='listening'?v.level:0);
    if(v.revision===voiceRevision)return;
    voiceRevision=v.revision;
    if(v.state==='listening'){voiceUi(true);$('headline').textContent='Listening…';$('subhead').textContent='Click the microphone again to transcribe.';$('status-label').textContent='LISTENING';shaderState=.18}
    if(v.state==='transcribing'){voiceUi(false);setState('thinking');$('subhead').textContent='Whisper is transcribing locally…';window.setArtemisVisualMode?.('transcribing')}
    if(v.state==='done'){
      voiceUi(false);setState('idle');
      const transcript=(v.text||'').trim();
      if(transcript&&$('last-heard')){$('last-heard').hidden=false;$('last-heard').textContent='Heard: '+transcript;}
      if(!transcript){popup('No clear speech recognized. Please try again.');}
      else{
        if(($('auto-send-voice')?.checked||window.ArtemisHandsfree?.enabled)&&(!v.automatic||window.ArtemisHandsfree?.enabled)&&window.ArtemisSession?.quiet===false){
          if(!busy){
            // Stay on the voice workspace; do not reveal the chat drawer.
            closePanels();
            $('headline').textContent='You said';
            $('subhead').textContent=transcript;
            await sendArtemisMessage(transcript, true);
          }else{
            // Never discard speech when a previous response is in progress.
            $('chat-input').value=transcript;
            popup('Artemis is still responding. Your words are saved in Chat.');
          }
        }else{
          $('chat-input').value=transcript;
          openPanel('chat');
          popup('Transcript ready. Review and press Send.');
        }
      }
    }
    if(v.state==='error'){voiceUi(false);setState('error');popup(v.error||'Speech recognition failed')}
    if(v.state==='waiting'&&window.ArtemisHandsfree?.enabled){voiceUi(false);setState('idle');$('headline').textContent='Ready to listen.';$('subhead').textContent='Hands-free is waiting for your next words.';$('status-label').textContent='WAITING'}
  }catch(e){console.error('Voice status',e)}finally{voicePolling=false}
}
setInterval(voicePoll,350);
$('voice-button').addEventListener('click',async()=>{
  if(window.ArtemisHandsfree?.enabled){await window.ArtemisHandsfree.stop('Hands-free stopped.');voiceUi(false);setState('idle');return}
  if(window.ArtemisSession?.quiet!==false){popup('Quiet mode is on. Use text chat.');return}
  const api=window.pywebview?.api;
  if(!api?.start_listening){popup('Microphone requires the Windows Artemis desktop window.');return}
  try{
    const result=voiceActive?await api.stop_listening():await api.start_listening();
    if(!result?.ok)popup(result?.error||'Microphone unavailable');
    else if(!voiceActive){voiceUi(true);$('headline').textContent='Listening…';$('subhead').textContent='Click the microphone again to transcribe.'}
    else{voiceUi(false);$('headline').textContent='Transcribing…'}
  }catch(err){popup('Microphone: '+err.message)}
});
let speechOn=true,speechRevision=-1;
function updateSpeechButton(){const b=$('sound-button');b.style.opacity=speechOn?'1':'.42';b.title=speechOn?'Mute Isabella':'Unmute Isabella';b.setAttribute('aria-label',b.title)}
async function speechPoll(){
  const api=window.pywebview?.api;
  if(!api?.speech_status)return;
  try{
    const v=await api.speech_status();
    speechOn=Boolean(v.enabled);updateSpeechButton();
    if(v.revision!==speechRevision){
      speechRevision=v.revision;
      if(v.error)popup('Voice: '+v.error);
      if(v.playing){setState('speaking');$('headline').textContent='Speaking…';$('subhead').textContent=history.length ? history[history.length-1].content : 'Isabella is answering.'; $('status-label').textContent='SPEAKING'}
      else if(!busy && !$('voice-button').classList.contains('recording'))setState('idle');
    }
  }catch(err){console.error('Speech status',err)}
}
setInterval(speechPoll,300);
$('sound-button').addEventListener('click',async()=>{
  if(window.ArtemisSession?.quiet!==false){popup('Quiet mode keeps Isabella muted.');return}
  const api=window.pywebview?.api;
  if(!api?.set_speech_enabled){popup('Voice playback needs the Windows WebView2 app.');return}
  try{const result=await api.set_speech_enabled(!speechOn);if(!result?.ok)throw Error(result?.error||'Voice toggle failed');speechOn=result.enabled;window.ArtemisSession?.setSpeechPreference(speechOn);updateSpeechButton();popup(speechOn?'Isabella enabled':'Isabella muted (current audio may finish).')}
  catch(err){popup('Voice: '+err.message)}
});
updateSpeechButton();
$('animation-speed').addEventListener('input',e=>{speed=Number(e.target.value)/100;$('speed-value').textContent=speed.toFixed(1)+'×'});
$('orb-scale').addEventListener('input',e=>{let v=Number(e.target.value);document.documentElement.style.setProperty('--orb-scale',(v/100).toString());$('scale-value').textContent=v+'%'});
$('reduce-motion').addEventListener('change',e=>{if(e.target.checked){speed=0;$('animation-speed').value=0;$('speed-value').textContent='0.0×'}else{$('animation-speed').value=100;speed=1;$('speed-value').textContent='1.0×'}});
let history=[],busy=false;
let activeReply=null;
$('index-documents').addEventListener('click',async()=>{
  const button=$('index-documents');button.disabled=true;
  try{
    const api=window.pywebview?.api;
    if(!api?.choose_documents)throw Error('Open the updated desktop app to select documents.');
    const result=await api.choose_documents();
    $('document-status').textContent=result.reply;
  }catch(err){$('document-status').textContent='Could not add documents: '+err.message;}
  finally{button.disabled=false;}
});
$('stop-reply').addEventListener('click',()=>activeReply?.abort());
$('check-services').addEventListener('click',async()=>{
  const button=$('check-services');button.disabled=true;
  $('service-status').textContent='Checking…';
  try{
    const response=await fetch('/api/diagnostics',{signal:AbortSignal.timeout(5000)});
    if(!response.ok)throw Error('Service check failed');
    const status=await response.json();
    const api=window.pywebview?.api;
    const voice=await api?.voice_status?.(),speech=await api?.speech_status?.();
    $('service-status').textContent=`Ollama: ${status.ollama}. Model: ${status.model}. Recognition: ${voice?.state||'desktop app required'}. Speech: ${speech?.error|| (speech ? (speech.playing?'playing':speech.enabled?'enabled':'muted'):'desktop app required')}. Audio devices have not been tested.`;
  }catch(err){$('service-status').textContent='Could not check services: '+err.message;}
  finally{button.disabled=false;}
});
function bubble(role,content){let el=document.createElement('div');el.className='bubble '+role;el.textContent=content;let welcome=$('messages').querySelector('.welcome');if(welcome)welcome.remove();$('messages').appendChild(el);$('messages').scrollTop=$('messages').scrollHeight;return el}
async function sendArtemisMessage(msg, fromVoice=false){
  msg=String(msg||'').trim();
  if(!msg||busy)return;
  busy=true;$('send').disabled=true;
  const prev=history.slice();
  bubble('user',msg);
  const pending=bubble('assistant','Thinking…');
  setState('thinking');
  if(fromVoice){$('headline').textContent='Thinking…';$('subhead').textContent='Artemis is preparing your reply.';}
  try{
    const commandApi=window.pywebview?.api;
    const local=await (commandApi?.handle_command
      ? commandApi.handle_command(msg)
      : commandApi?.handle_app_command?.(msg));
    const toolText=msg.toLowerCase().replace(/’/g,"'").replace(/\s+/g,' ').trim().replace(/^(?:hey\s+)?artemis[,!:. ]+/,'').replace(/^(?:(?:can|could|would) you (?:please )?|please )/,'').replace(/^whether(?=\s+(?:today|tomorrow)\b)/,'weather');
    if(/^(?:search documents\b|list documents\b|remove document\b)/.test(toolText)&&local?.handled!==true){
      throw Error('Document commands require the updated desktop app.');
    }
    if(/^(?:remember that\b|forget memory\b|update memory\b|show memories\b|list memories\b|find memories about\b)/.test(toolText)&&local?.handled!==true){
      throw Error('Personal memory requires the updated desktop app. This request has not been saved or changed.');
    }
    const weatherRequest=(/\b(?:weather|forecast)\b/.test(toolText)&&!(/\b(?:explain|code|work|works|history|documentary|video|movie|app|api|meaning|definition)\b/.test(toolText)))||/^(?:will it rain|is it raining|do i need (?:an? )?umbrella|should i take (?:an? )?umbrella)/.test(toolText);
    if(weatherRequest&&local?.handled!==true){
      throw Error('The desktop weather service did not handle this request. Close all Artemis windows and reopen Artemis.exe, then ask again.');
    }
    if(/^(?:(?:hey\s+)?artemis[,!:. ]+)?(?:(?:can|could|would) you (?:please )?|please )?(?:open|launch|start)\s+/i.test(msg)&&local?.handled!==true){
      throw Error('The desktop app launcher did not handle this request. Close all Artemis windows and reopen Artemis.exe, then try “open Spotify”.');
    }
    let data;
    if(local?.handled){data=local;}
    else{
      const controller=new AbortController();activeReply=controller;
      let timedOut=false;
      const timer=setTimeout(()=>{timedOut=true;controller.abort();},115000);
      $('stop-reply').hidden=false;
      let response;
      try{
        response=await fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:msg,history:prev.slice(-2),stream:true}),signal:controller.signal});
        data=await readArtemisStream(response,text=>{
          pending.textContent=text;
          if(fromVoice)$('subhead').textContent=text;
          $('messages').scrollTop=$('messages').scrollHeight;
        });
        if(controller.signal.aborted)throw new DOMException('Stopped','AbortError');
      }catch(err){
        if(controller.signal.aborted && timedOut)throw Error('The reply took too long. Please try again.');
        throw err;
      }finally{clearTimeout(timer);activeReply=null;$('stop-reply').hidden=true;}
    }
    pending.textContent=data.reply;
    if(!local?.handled && data.sources?.length){
      const references=document.createElement('details');
      const label=document.createElement('summary');label.textContent='Reference excerpts supplied to the model';references.appendChild(label);
      for(const source of data.sources){
        const excerpt=document.createElement('p');
        excerpt.textContent=`[Document ${source.document_id}, ${source.locator || 'line '+source.line_start}] ${source.path}\nIndexed ${source.indexed_at}\n${source.text}`;
        references.appendChild(excerpt);
      }
      pending.appendChild(references);
    }
    if(data.weather_choices){
      for(const choice of data.weather_choices){
        const button=document.createElement('button');button.className='app-confirm';button.textContent='Use '+choice.name;
        button.addEventListener('click',async()=>{
          button.disabled=true;
          try{const result=await window.pywebview.api.select_weather_location(choice.token);bubble('assistant',result.reply);history.push({role:'assistant',content:result.reply});history=history.slice(-100);void window.ArtemisSession?.saveHistory(history);}catch(err){bubble('assistant',err.message)}
        });pending.appendChild(document.createElement('br'));pending.appendChild(button);
      }
      if(fromVoice)openPanel('chat');
    }
    if(data.confirmation){
      const button=document.createElement('button');
      button.className='app-confirm';button.textContent='Open '+data.confirmation.name;
      button.addEventListener('click',async()=>{
        button.disabled=true;
        try{
          const result=await window.pywebview.api.confirm_app_launch(data.confirmation.token);
          bubble('assistant',result.reply);
          history.push({role:'assistant',content:result.reply});history=history.slice(-100);
          void window.ArtemisSession?.saveHistory(history);
        }catch(err){bubble('assistant','App launch failed: '+err.message)}
      });
      pending.appendChild(document.createElement('br'));pending.appendChild(button);
      if(fromVoice)openPanel('chat');
    }
    history.push({role:'user',content:msg},{role:'assistant',content:data.reply});
    history=history.slice(-100);
    void window.ArtemisSession?.saveHistory(history);
    setState('idle');
    if(fromVoice){$('headline').textContent='Artemis';$('subhead').textContent=data.reply;}
    if(speechOn&&window.ArtemisSession?.quiet===false){
      const api=window.pywebview?.api;
      if(api?.speak_reply){
        try{
          const result=await api.speak_reply(data.spoken_reply ?? data.reply);
          if(!result?.ok&&result?.error!=='Speech output is muted')popup('Voice: '+result.error);
        }catch(err){popup('Voice playback: '+err.message);}
      }
    }
  }catch(err){
    if(err.name==='AbortError'){
      pending.textContent='Reply stopped.';
      if(window.ArtemisHandsfree?.enabled)await window.ArtemisHandsfree.stop('Reply stopped.');
      setState('idle');
      if(fromVoice)$('subhead').textContent='Reply stopped.';
      return;
    }
    pending.textContent='Could not connect: '+err.message;
    if(window.ArtemisHandsfree?.enabled)await window.ArtemisHandsfree.stop('Paused: reply failed.');
    setState('error');
    if(fromVoice)$('subhead').textContent='Could not connect: '+err.message;
  }finally{
    busy=false;$('send').disabled=false;
    $('messages').scrollTop=$('messages').scrollHeight;
  }
}
$('chat-form').addEventListener('submit',e=>{
  e.preventDefault();
  const msg=$('chat-input').value.trim();
  if(!msg||busy)return;
  $('chat-input').value='';
  void sendArtemisMessage(msg,false);
});
$('clear-chat').addEventListener('click',()=>{if(busy){popup('Wait for the current reply before clearing.');return}history=[];void window.ArtemisSession?.saveHistory(history);$('messages').innerHTML='<div class="welcome"><img src="/assets/lunar_a.png" alt=""><h3>Start a new conversation</h3><p>Connected to your local Ollama model when it is running.</p></div>';setState('idle')});
document.addEventListener('fullscreenchange',()=>syncFullscreenButton(Boolean(document.fullscreenElement)));
window.addEventListener('pywebviewready',()=>{window.pywebview?.api?.get_fullscreen?.().then(v=>syncFullscreenButton(Boolean(v.fullscreen))).catch(()=>{});});
setState('idle');initGlass();



