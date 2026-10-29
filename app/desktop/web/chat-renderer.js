/* Coalesce stream fragments into one paint; keep reading position when scrolled up. */
'use strict';
function createArtemisReplyRenderer(element, container, preview, frames={
  request: callback=>requestAnimationFrame(callback), cancel: id=>cancelAnimationFrame(id)
}) {
  let queued=null, latest='', disposed=false;
  function paint() {
    queued=null;
    if(disposed)return;
    const follow=container.scrollHeight-container.clientHeight-container.scrollTop<64;
    element.textContent=latest;
    if(preview)preview.textContent=latest;
    if(follow)container.scrollTop=container.scrollHeight;
  }
  return {
    update(text) {
      if(disposed)return;
      latest=text;
      if(queued===null)queued=frames.request(paint);
    },
    finish() {
      if(queued!==null){frames.cancel(queued);paint();}
      disposed=true;
    }
  };
}
let artemisScrollFrame=null;
function scrollArtemisChatToEnd() {
  if(artemisScrollFrame!==null)return;
  artemisScrollFrame=requestAnimationFrame(()=>{
    artemisScrollFrame=null;
    const messages=document.getElementById('messages');
    messages.scrollTop=messages.scrollHeight;
  });
}
if(typeof module!=='undefined')module.exports={createArtemisReplyRenderer};
