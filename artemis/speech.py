"""Local Vosk command transcription; no audio saved to disk or sent to a server."""
import json
import time

import numpy as np
from vosk import KaldiRecognizer

from .config import (
    MAX_COMMAND_SECONDS, MIC_RMS_THRESHOLD, SAMPLE_RATE,
    SILENCE_AFTER_SPEECH_SECONDS, WAIT_FOR_SPEECH_SECONDS,
)


def _rms(frame: bytes) -> float:
    pcm = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
    return float(np.sqrt(np.mean(pcm * pcm))) if pcm.size else 0.0


def listen_for_command(microphone, speech_model) -> str:
    """Listen after wake word until Vosk endpoint, silence, or timeout."""
    recognizer = KaldiRecognizer(speech_model, SAMPLE_RATE)
    start = time.monotonic()
    heard_audio = False
    last_voice = start

    while time.monotonic() - start < MAX_COMMAND_SECONDS:
        frame = microphone.read(timeout=0.3)
        if frame is None:
            continue
        now = time.monotonic()
        if _rms(frame) >= MIC_RMS_THRESHOLD:
            heard_audio = True
            last_voice = now

        if recognizer.AcceptWaveform(frame):
            result = json.loads(recognizer.Result())
            phrase = result.get("text", "").strip()
            if phrase:
                return phrase

        if heard_audio and now - last_voice >= SILENCE_AFTER_SPEECH_SECONDS:
            break
        if not heard_audio and now - start >= WAIT_FOR_SPEECH_SECONDS:
            break

    return json.loads(recognizer.FinalResult()).get("text", "").strip()
