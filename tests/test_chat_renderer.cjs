const assert=require('node:assert/strict');
const {createArtemisReplyRenderer}=require('../app/desktop/web/chat-renderer.js');
let callback=null,writes=0,scrolls=0,text='';
const frames={request(fn){assert.equal(callback,null);callback=fn;return 1;},cancel(){callback=null;}};
const element={set textContent(value){writes++;text=value;}};
const container={scrollHeight:1000,clientHeight:400,_top:600,
  get scrollTop(){return this._top;},set scrollTop(value){scrolls++;this._top=value;}};
const renderer=createArtemisReplyRenderer(element,container,null,frames);
for(let i=1;i<=500;i++)renderer.update('x'.repeat(i));
assert.equal(writes,0);
let paint=callback;callback=null;paint();
assert.equal(writes,1);assert.equal(text.length,500);assert.equal(scrolls,1);
container._top=100;renderer.update('more');
paint=callback;callback=null;paint();
assert.equal(scrolls,1,'Reading older messages must not jump to the bottom');
renderer.update('complete');renderer.finish();
assert.equal(text,'complete');assert.equal(callback,null);
renderer.update('stale fragment');assert.equal(text,'complete');
// Finishing on cancellation/error must flush once and prevent delayed overwrites.
const preview={textContent:''};
const stopped=createArtemisReplyRenderer(element,container,preview,frames);
stopped.update('partial');stopped.finish();
assert.equal(preview.textContent,'partial');assert.equal(callback,null);
console.log('PASS: 500 fragments coalesced into one paint, scroll position preserved, final/error flush and no stale callbacks');
