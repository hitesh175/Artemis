"""Single 16 kHz audio input stream shared by wake-word and speech recognition."""
from queue import Empty, Full, Queue
import sys

import sounddevice as sd

from .config import FRAME_SAMPLES, SAMPLE_RATE


class Microphone:
    def __init__(self, device=None):
        self.device = device
        # Limit buffered audio to ~4 seconds in memory.
        self.frames = Queue(maxsize=50)
        self.stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[Microphone warning] {status}", file=sys.stderr)
        raw = bytes(indata)
        try:
            self.frames.put_nowait(raw)
        except Full:
            # Drop stale audio rather than buffering conversations indefinitely.
            try:
                self.frames.get_nowait()
                self.frames.put_nowait(raw)
            except (Empty, Full):
                pass

    def __enter__(self):
        self.stream = sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=FRAME_SAMPLES,
            device=self.device,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )
        self.stream.start()
        return self

    def read(self, timeout=1):
        try:
            return self.frames.get(timeout=timeout)
        except Empty:
            return None

    def flush(self):
        while True:
            try:
                self.frames.get_nowait()
            except Empty:
                return

    def __exit__(self, exc_type, exc, traceback):
        if self.stream is not None:
            self.stream.stop()
            self.stream.close()
