"""One-shot OFFLINE faster-whisper command recognition after the wake word.

Audio is buffered only in RAM for the active command, never written to a file.
The wake-word detector stays responsible for always-on listening.
"""
import time

import numpy as np

from .config import (
    MAX_COMMAND_SECONDS, MIC_RMS_THRESHOLD,
    SILENCE_AFTER_SPEECH_SECONDS, WAIT_FOR_SPEECH_SECONDS,
)


def listen_for_whisper_command(microphone, model):
    """Collect up to one spoken command and run local Whisper transcription."""
    start = time.monotonic()
    last_voice = start
    heard_voice = False
    chunks = []

    while time.monotonic() - start < MAX_COMMAND_SECONDS:
        chunk = microphone.read(timeout=0.3)
        if chunk is None:
            continue
        now = time.monotonic()
        pcm = np.frombuffer(chunk, dtype=np.int16)
        if pcm.size == 0:
            continue
        rms = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)))
        if rms >= MIC_RMS_THRESHOLD:
            heard_voice = True
            last_voice = now
        chunks.append(pcm.copy())
        if heard_voice and now - last_voice >= SILENCE_AFTER_SPEECH_SECONDS:
            break
        if not heard_voice and now - start >= WAIT_FOR_SPEECH_SECONDS:
            break

    if not heard_voice:
        return ""
    audio = np.concatenate(chunks).astype(np.float32) / 32768.0
    print("[Transcribing locally with Whisper...]", flush=True)
    # A language hint avoids time-consuming language detection for short commands.
    segments, _ = model.transcribe(
        audio, language="en", beam_size=5, vad_filter=False,
        condition_on_previous_text=False, without_timestamps=True,
    )
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text
