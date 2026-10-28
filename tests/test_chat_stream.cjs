const assert = require('node:assert/strict');
const {readArtemisStream} = require('../app/desktop/web/chat-stream.js');
function response(parts) {
  return {ok:true, body:new ReadableStream({start(controller) {
    for (const part of parts) controller.enqueue(part);
    controller.close();
  }})};
}
(async()=>{
  const bytes=new TextEncoder().encode('{"delta":"Héllo"}\n{"delta":" world"}\n{"done":true}\n');
  const updates=[];
  assert.equal((await readArtemisStream(response([...bytes].map(b=>Uint8Array.of(b))),text=>updates.push(text))).reply,'Héllo world');
  assert.deepEqual(updates,['Héllo','Héllo world']);
  const referenced = await readArtemisStream(response([new TextEncoder().encode('{"delta":"Answer"}\n{"done":true,"sources":[{"document_id":1,"line_start":2}]}\n')]),()=>{});
  assert.equal(referenced.sources[0].document_id,1);
  for(const body of ['{"delta":"partial"}\n','{"error":"failed"}\n','{"done":true}\n','invalid\n']) {
    await assert.rejects(()=>readArtemisStream(response([new TextEncoder().encode(body)]),()=>{}));
  }
  const controller=new AbortController();controller.abort();
  const aborted={ok:true,body:new ReadableStream({start(c){c.error(new DOMException('Stopped','AbortError'));}})};
  await assert.rejects(()=>readArtemisStream(aborted,()=>{}),{name:'AbortError'});
  console.log('PASS: fragmented UTF-8, incremental updates, stream failure, early EOF and cancellation');
})().catch(error=>{console.error(error);process.exitCode=1;});
