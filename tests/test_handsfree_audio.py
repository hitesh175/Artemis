"""Synthetic audio only. Never loads models or opens a real microphone."""
import sys,threading
from pathlib import Path
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1].joinpath('app/desktop').resolve()))
from speech_endpoint import SpeechEndpoint
from whisper_input import WhisperInput
e=SpeechEndpoint()
assert all(e.feed(.001,.1)=='continue' for _ in range(5))
assert all(e.feed(.04,.1)=='continue' for _ in range(8))
assert e.started
assert all(e.feed(.001,.1)=='continue' for _ in range(11))
assert e.feed(.001,.11)=='done'
e=SpeechEndpoint()
for _ in range(101):decision=e.feed(.001,.1)
assert decision=='timeout'
e=SpeechEndpoint();e.feed(.1,.1)
for _ in range(20):decision=e.feed(.001,.1)
assert not e.started,'A brief click must not count as an utterance'

blocks=[]
class Stream:
    def __init__(self,**kw):self.callback=kw['callback']
    def __enter__(self):
        for value in blocks:self.callback(np.full((1600,1),value,dtype=np.float32),1600,None,None)
        return self
    def __exit__(self,*args):pass
sys.modules['sounddevice']=SimpleNamespace(InputStream=Stream)
w=WhisperInput();w._auto_stop=True;w._update('listening')
calls=[]
def transcribe(audio,**kw):calls.append(len(audio));return ([SimpleNamespace(text='Synthetic hands-free turn')],None)
w._load_model=lambda:SimpleNamespace(transcribe=transcribe)
blocks[:]=[.001]*5+[.04]*8+[.001]*14
w._run(threading.Event())
assert w.status()['state']=='done',w.status()
assert w.status()['automatic'] is True and w.status()['level']==0
assert len(calls)==1
w=WhisperInput();w._auto_stop=True;w._update('listening')
w._load_model=lambda:(_ for _ in ()).throw(AssertionError('Silence must not reach Whisper'))
blocks[:]=[.001]*105
w._run(threading.Event())
assert w.status()['state']=='waiting',w.status()
assert not w.status()['error'],w.status()
w.cancel();assert w.status()['state']=='idle'
print('PASS: pause endpoint, click rejection, silence timeout, one transcription, cancellation; synthetic audio only')

