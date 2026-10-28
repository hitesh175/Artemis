"""Synthetic playback only: never open a speaker or microphone."""
from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'))
sys.path.insert(0,str(ROOT/'app/desktop'))
from artemis import voice
from speech_output import SpeechOutput
from performance_log import PERFORMANCE

cancel=threading.Event();writes=[];aborts=[];opened=[]
class Stream:
    def __init__(self,**kwargs):opened.append(kwargs)
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def write(self,audio):writes.append(len(audio));cancel.set()
    def abort(self):aborts.append(True)
with patch.dict(sys.modules,{'sounddevice':SimpleNamespace(OutputStream=Stream)}):
    voice._play(np.ones(8192),24000,cancel)
    assert writes==[1024] and aborts==[True]
    assert opened[0]['channels']==1
    voice._play(np.ones(8192),24000,cancel)
    assert len(opened)==1,'Already cancelled speech must not open a stream'
    cancel.clear();writes.clear();aborts.clear()
    voice._play(np.ones((8192,2)),24000,cancel)
    assert opened[-1]['channels']==2 and aborts==[True]

# Cancellation during synthesis suppresses both playback and fallback.
speaker=voice.Speaker(enabled=False)
cancel.clear()
def create(*args,**kwargs):cancel.set();return np.ones(8192),24000
speaker.kokoro=SimpleNamespace(create=create)
with patch.object(voice,'_play') as play,patch.object(speaker,'_enable_piper_fallback') as fallback:
    speaker.say('A long response',cancel_event=cancel)
    play.assert_not_called();fallback.assert_not_called()

def wait_idle(output):
    deadline=time.monotonic()+2
    while output.status()['playing'] and time.monotonic()<deadline:time.sleep(.005)
    assert not output.status()['playing'],output.status()

entered=threading.Event();release=threading.Event()
def say(text,cancel_event):
    entered.set();release.wait(2)
    assert cancel_event.is_set()
output=SpeechOutput();output.speaker=SimpleNamespace(kokoro=object(),say=say)
assert output.speak('test cancellation')['ok']
assert entered.wait(2)
assert output.stop()['stopping']
assert not output.speak('overlap')['ok'],'Stopped synthesis must finish before another worker starts'
release.set();wait_idle(output)
assert not output.status()['error']
# Re-enable and start a fresh turn with a new cancellation token.
fresh=[]
output.speaker=SimpleNamespace(kokoro=object(),say=lambda text,cancel_event:fresh.append(cancel_event.is_set()))
assert output.speak('new reply')['ok'];wait_idle(output)
assert fresh==[False]
entered.clear();release.clear()
output.speaker=SimpleNamespace(kokoro=object(),say=say)
assert output.speak('quiet interruption')['ok'];assert entered.wait(2)
assert output.set_enabled(False)['stopping']
release.set();wait_idle(output)
assert not output.speak('muted')['ok']
assert output.stop()['ok']
records=PERFORMANCE.snapshot()['recent']
assert any(record['stage']=='speech' and record['outcome']=='cancelled' for record in records)
assert any(record['stage']=='speech' and record['outcome']=='completed' for record in records)
print('PASS: owned-stream abort, mono/stereo cancellation, synthesis suppression, worker isolation, retry and mute interruption')
