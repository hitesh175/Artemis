/* Artemis's local reply protocol: display text only, never HTML. */
'use strict';
async function readArtemisStream(response, onText) {
  if (!response.ok) {
    const error = await response.json();
    throw Error(error.error || 'Request failed');
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '', answer = '', completed = false;
  try {
    while (!completed) {
      const {value, done} = await reader.read();
      buffer += decoder.decode(value, {stream: !done});
      let end;
      while ((end = buffer.indexOf('\n')) >= 0) {
        const line = buffer.slice(0, end); buffer = buffer.slice(end + 1);
        if (!line.trim()) continue;
        const event = JSON.parse(line);
        if (event.error) throw Error(event.error);
        if (event.delta !== undefined) {
          if (typeof event.delta !== 'string') throw Error('Invalid reply fragment');
          answer += event.delta;
          onText(answer);
        }
        if (event.done === true) { completed = true; break; }
      }
      if (done && !completed) throw Error('Reply ended early. Please try again.');
    }
    if (!answer.trim()) throw Error('The model returned an empty reply.');
    return {reply: answer};
  } finally {
    try { await reader.cancel(); } catch (_) { /* Already closed or cancelled. */ }
    reader.releaseLock();
  }
}
if (typeof module !== 'undefined') module.exports = {readArtemisStream};
