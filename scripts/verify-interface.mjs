/* Run against the isolated verify-fresh-install preview on localhost:9222. */
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
const page=(await (await fetch('http://127.0.0.1:9222/json/list')).json()).find(p=>p.type==='page'&&p.url.startsWith('http://127.0.0.1:'));
assert(page,'Start the isolated native preview with the local DevTools port first.');
const socket=new WebSocket(page.webSocketDebuggerUrl);await new Promise((resolve,reject)=>{socket.addEventListener('open',resolve,{once:true});socket.addEventListener('error',reject,{once:true});});
let id=0;const pending=new Map();socket.onmessage=({data})=>{const m=JSON.parse(data),p=pending.get(m.id);if(p){pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}};
const call=(method,params={})=>new Promise((resolve,reject)=>{const n=++id;pending.set(n,{resolve,reject});socket.send(JSON.stringify({id:n,method,params}));});
const evaluate=async expression=>{const r=await call('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});assert(!r.exceptionDetails,JSON.stringify(r.exceptionDetails));return r.result.value;};
const tab=async shift=>{for(const type of ['keyDown','keyUp'])await call('Input.dispatchKeyEvent',{type,key:'Tab',code:'Tab',windowsVirtualKeyCode:9,modifiers:shift?8:0});};
const result={passed:false};
try{
 await evaluate("closePanels();document.getElementById('settings-open').focus();document.getElementById('settings-open').click();true");
 assert.equal(await evaluate('document.activeElement.id'),'settings-panel-title');
 await evaluate("document.getElementById('settings-close').focus();true");await tab(true);
 assert(await evaluate("document.getElementById('settings-panel').contains(document.activeElement)"),'Focus escaped Settings');
 assert(await evaluate("document.querySelector('.topbar').inert"));
 await evaluate('closePanels();true');assert.equal(await evaluate('document.activeElement.id'),'settings-open');
 result.focus='opening, boundary trapping, background inertness and opener restoration passed';
 result.groups=await evaluate(`(()=>{const groups={};for(const option of document.getElementById('settings-category').options){document.getElementById('settings-category').value=option.value;document.getElementById('settings-category').dispatchEvent(new Event('change'));groups[option.value]=[...document.querySelectorAll('.settings-section')].filter(e=>!e.hidden).map(e=>e.getAttribute('aria-labelledby'));}showArtemisSettingsSection('setting-quiet-mode');return groups;})()`);
 result.sliders=await evaluate("['animation-speed','orb-scale'].map(id=>{const e=document.getElementById(id),r=e.getBoundingClientRect(),label=e.closest('label').getBoundingClientRect();return {id,width:r.width,labelWidth:label.width,belowLabel:r.y>label.y}})");
 for(const slider of result.sliders){assert(slider.width>slider.labelWidth*.9&&slider.belowLabel,'Appearance slider lost its full-width row');}
 assert.equal(new Set(Object.values(result.groups).flat()).size,17,'Some settings are missing');assert.equal(Object.values(result.groups).flat().length,17,'Settings overlap categories');
 result.viewports=[];
 for(const [width,height] of [[1100,800],[800,600],[500,640],[320,480],[260,260]]){
  await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
  await evaluate("closePanels();document.querySelector('.app').scrollTop=0;true");
  const check=await evaluate(`(()=>{const ids=['chat-open','sound-button','settings-open','quiet-toggle','handsfree-header'];return {width:innerWidth,height:innerHeight,clipped:ids.filter(id=>{const r=document.getElementById(id).getBoundingClientRect();return r.x<-.5||r.y<-.5||r.right>innerWidth+.5||r.bottom>innerHeight+.5;})}})()`);
  result.viewports.push(check);assert.deepEqual(check.clipped,[],`Clipped controls at ${width}x${height}`);
 }
 await call('Emulation.clearDeviceMetricsOverride');
 await evaluate("openPanel('chat');true");
 await evaluate("(async()=>{await sendArtemisMessage('calculate 25 * 4');return true;})()");
 await new Promise(r=>setTimeout(r,150));
 result.announcement=await evaluate("({text:document.getElementById('chat-announcement').textContent,busy:document.getElementById('messages').getAttribute('aria-busy'),role:document.getElementById('messages').getAttribute('role')})");
 assert.match(result.announcement.text,/25 \* 4 = 100/);assert.equal(result.announcement.busy,'false');assert.equal(result.announcement.role,'log');
 await evaluate("showArtemisSettingsSection('setting-everyday');openPanel('settings');true");
 result.placeholder=await evaluate("(()=>{const e=document.getElementById('weather-city');return {color:getComputedStyle(e,'::placeholder').color,background:getComputedStyle(e).backgroundColor}})()");
 assert.equal(result.placeholder.color,'rgb(159, 178, 200)');
 const layout=async expected=>{for(let n=0;n<50;n++){if(await evaluate('document.querySelector(".app").dataset.layout')===expected)return;await new Promise(r=>setTimeout(r,100));}throw Error('Native layout did not change to '+expected);};
 await evaluate("closePanels();document.getElementById('mini-open').click();true");await layout('mini');
 await evaluate("document.getElementById('mini-icon-open').click();true");await layout('chat');
 assert(await evaluate("!document.getElementById('mini-full').closest('[inert]')"),'Full control is disabled in Mini chat');
 await evaluate("document.getElementById('mini-full').click();true");await layout('full');
 result.mini='native Mini, compact chat, and Full round trip passed';
 result.passed=true;console.log(JSON.stringify(result,null,2));
}finally{
 await call('Emulation.clearDeviceMetricsOverride');await evaluate("showArtemisSettingsSection('setting-quiet-mode');openPanel('settings');true");socket.close();
 await fs.mkdir('output/design-audit',{recursive:true});await fs.writeFile('output/design-audit/interface-verification.json',JSON.stringify(result,null,2));
}
