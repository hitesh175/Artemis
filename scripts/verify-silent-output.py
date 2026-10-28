"""Verify the installed output driver with zero-valued samples; no microphone."""
from pathlib import Path
import sys
import threading
import time
import numpy as np

sys.path.insert(0,str(Path(r'C:\Users\kanag\Desktop\Artemis')))
from artemis.voice import _play

cancel=threading.Event()
timer=threading.Timer(.2,cancel.set)
start=time.monotonic()
timer.start()
try:
    _play(np.zeros(24000*3,dtype=np.float32),24000,cancel)
finally:
    timer.cancel()
elapsed=time.monotonic()-start
assert cancel.is_set(),'Silent playback finished without cancellation'
assert elapsed<3,'Silent playback did not stop within the test limit'
print(f'PASS: installed audio output opened and stopped silently in {elapsed:.2f}s; no microphone or speech used')
