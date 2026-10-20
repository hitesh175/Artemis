"""Common 16 kHz float32 microphone capture, used by GUI and diagnostics.

Audio stays in memory; no disk writes. Callback copies each chunk before reuse.
"""
import threading
import numpy as np
import sounddevice as sd

RATE = 16000

class MicCapture:
    def __init__(self, device=None):
        self.device = device
        self._chunks = []
        self._notices = []
        self._lock = threading.Lock()
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        with self._lock:
            if status:
                self._notices.append(str(status))
            self._chunks.append(indata[:, 0].copy())

    def __enter__(self):
        self._stream = sd.InputStream(samplerate=RATE, device=self.device,
                                      channels=1, dtype='float32', blocksize=1600,
                                      callback=self._callback)
        self._stream.start()
        return self

    def __exit__(self, exc_type, exc, tb):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def result(self):
        with self._lock:
            chunks = list(self._chunks)
            notices = list(self._notices)
        if not chunks:
            return np.empty(0, dtype=np.float32), notices
        return np.concatenate(chunks).astype(np.float32, copy=False), notices


def metrics(audio):
    if not len(audio):
        return 0.0, 0.0, 0.0
    return (len(audio)/RATE, float(np.max(np.abs(audio))),
            float(np.sqrt(np.mean(np.square(audio)))))


def transcribe(audio, model_name='base.en'):
    # Same Whisper options as the previously working Stage 5b terminal test.
    from faster_whisper import WhisperModel
    model = WhisperModel(model_name, device='cpu', compute_type='int8',
                         local_files_only=True)
    segments, _ = model.transcribe(audio, language='en', beam_size=5,
                                   vad_filter=True,
                                   condition_on_previous_text=False,
                                   without_timestamps=True)
    return ' '.join(s.text.strip() for s in segments).strip()
