from pathlib import Path
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import Mock,patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'app'));sys.path.insert(0,str(ROOT/'app/desktop'))
from voice_warmup import VoiceWarmup
from whisper_input import WhisperInput
from artemis.voice import Speaker

entered=threading.Event();release=threading.Event()
def prepare():entered.set();release.wait(2);return 'base.en'
recognizer=Mock();recognizer.prepare.side_effect=prepare
speech=Mock();speech.prepare.return_value.prime.return_value='Kokoro'
job=VoiceWarmup(recognizer,speech)
assert job.status()['state']=='idle'
assert job.start()['ok'];assert entered.wait(2)
assert not job.start()['ok']
release.set()
deadline=time.monotonic()+3
while job.busy() and time.monotonic()<deadline:time.sleep(.01)
assert job.status()['state']=='ready'
recognizer.start.assert_not_called();speech.speak.assert_not_called()
snapshot=job.status();snapshot['results'][0]['ready']=False
assert job.status()['results'][0]['ready']
recognizer.prepare.side_effect=RuntimeError('Not cached')
assert job.start()['ok']
deadline=time.monotonic()+3
while job.busy() and time.monotonic()<deadline:time.sleep(.01)
assert job.status()['state']=='error' and job.status()['results'][1]['ready']

loader=Mock(return_value=object())
with patch.dict(sys.modules,{'faster_whisper':SimpleNamespace(WhisperModel=loader)}),patch.dict('os.environ',{'ARTEMIS_WHISPER_ALLOW_DOWNLOAD':'1'}):
    voice=WhisperInput();voice.prepare()
    assert loader.call_args.kwargs['local_files_only'] is True
    assert voice._thread is None
speaker=Speaker(enabled=False);speaker.kokoro=SimpleNamespace(create=Mock())
with patch('artemis.voice._play') as play:
    assert speaker.prime()=='Kokoro'
    play.assert_not_called()
print('PASS: explicit warm-up, overlap prevention, partial errors, no capture/playback, local-only loading and status isolation')
