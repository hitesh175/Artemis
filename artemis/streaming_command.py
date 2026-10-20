"""Capture a whole command including buffered audio from the wake phrase.

All raw audio remains in RAM. The phrase is removed from the transcribed text
before passing to the existing strict command interpreter.
"""
from collections import deque
import re
import time
import numpy as np

from .config import SAMPLE_RATE, MIC_RMS_THRESHOLD

PRE_ROLL_SECONDS = 2.8
MAX_AFTER_WAKE_SECONDS = 9.0
WAIT_AFTER_WAKE_SECONDS = 3.4
SILENCE_SECONDS = 0.9
# Limited stop after wake ensures no indefinitely open mic capture.

class RecentAudio:
    def __init__(self, seconds=PRE_ROLL_SECONDS):
        self.frames = deque()
        self.samples = 0
        self.limit = int(seconds * SAMPLE_RATE)

    def append(self, frame):
        if not frame:
            return
        chunk = np.frombuffer(frame, dtype=np.int16).copy()
        self.frames.append(chunk)
        self.samples += len(chunk)
        while len(self.frames) > 1 and self.samples - len(self.frames[0]) >= self.limit:
            self.samples -= len(self.frames.popleft())

    def snapshot(self):
        return [part.copy() for part in self.frames]

    def clear(self):
        self.frames.clear()
        self.samples = 0


def remove_wake_phrase(text):
    """Only strip the initial wake phrase; never rewrite command intent."""
    value = text.strip()
    value = re.sub(r'^\s*(?:hey[\s,!.:-]*)?artemis\b[\s,!.:-]*', '', value, flags=re.I)
    return value.strip()


def _rms(chunk):
    x = np.frombuffer(chunk, dtype=np.int16)
    if not x.size:
        return 0.0
    return float(np.sqrt(np.mean(x.astype(np.float32) ** 2)))


def capture_whisper(microphone, model, initial_frames, *, clock=time.monotonic):
    """Transcribe pre-roll + speech following wake, with a silence endpoint.

    Command spoken in the pre-roll survives. For pause-and-command mode we wait
    for speech and capture until silence. The VAD here is RMS-based and is only
    an endpoint heuristic; Whisper is still the authoritative transcription.
    """
    chunks = [np.array(c, dtype=np.int16, copy=True) for c in initial_frames]
    t0 = clock()
    last_voice = None
    after_wake_heard_voice = False
    while clock() - t0 < MAX_AFTER_WAKE_SECONDS:
        frame = microphone.read(timeout=0.2)
        if frame is None:
            if after_wake_heard_voice and clock() - last_voice >= SILENCE_SECONDS:
                break
            if not after_wake_heard_voice and clock() - t0 >= WAIT_AFTER_WAKE_SECONDS:
                break
            continue
        pcm = np.frombuffer(frame, dtype=np.int16).copy()
        if not pcm.size:
            continue
        chunks.append(pcm)
        now = clock()
        if _rms(frame) >= MIC_RMS_THRESHOLD:
            after_wake_heard_voice = True
            last_voice = now
        elif after_wake_heard_voice and now - last_voice >= SILENCE_SECONDS:
            break
        elif not after_wake_heard_voice and now - t0 >= WAIT_AFTER_WAKE_SECONDS:
            break

    if not chunks:
        return ""
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    print('[Transcribing locally with Whisper...]', flush=True)
    segments, _ = model.transcribe(
        audio, language='en', beam_size=5, vad_filter=False,
        condition_on_previous_text=False, without_timestamps=True,
    )
    raw = ' '.join(seg.text.strip() for seg in segments).strip()
    print(f'[Heard] {raw}', flush=True)
    return remove_wake_phrase(raw)
