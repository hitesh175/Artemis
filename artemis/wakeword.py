"""Offline phrase-based wake detection for ARTEMIS Stage 2.

Stage 2 uses Vosk transcription for the exact phrase 'Hey Artemis', not a
purpose-trained wake-word neural network. Expect accuracy/power trade-offs.
"""
import json
import re
from dataclasses import dataclass

import numpy as np

from .config import SAMPLE_RATE, WAKE_ALIASES, WAKE_THRESHOLD, WAKE_SCORE_KEYWORD, WAKE_MODEL


def normalize(text: str) -> str:
    """Lowercase words with normalized whitespace; punctuation is ignored."""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", text.lower())).strip()


def get_command_after_wake(text: str, phrases=WAKE_ALIASES) -> str | None:
    """Return the command tail (possibly empty) when a wake phrase starts speech.

    Returns None when no phrase matches. Requires a word boundary after the
    phrase; does not accept 'hey artemisian' or a wake phrase mid-conversation.
    """
    heard = normalize(text)
    for phrase in sorted((normalize(x) for x in phrases), key=len, reverse=True):
        if heard == phrase:
            return ""
        if heard.startswith(phrase + " "):
            return heard[len(phrase):].strip()
    return None


@dataclass(frozen=True)
class WakeHit:
    phrase: str
    command_tail: str = ""


class VoskPhraseDetector:
    """Listen for 'Hey Artemis' using locally generated STT hypotheses."""

    def __init__(self, model, debug=False):
        from vosk import KaldiRecognizer
        self.model = model
        self.debug = debug
        self._last_partial = ""
        self._recognizer = KaldiRecognizer(model, SAMPLE_RATE)

    def reset(self):
        from vosk import KaldiRecognizer
        self._recognizer = KaldiRecognizer(self.model, SAMPLE_RATE)
        self._last_partial = ""

    def process(self, frame: bytes) -> WakeHit | None:
        if self._recognizer.AcceptWaveform(frame):
            result = json.loads(self._recognizer.Result()).get("text", "").strip()
            if self.debug and result:
                print(f"[Wake debug: final transcript] {result}")
            tail = get_command_after_wake(result)
            if tail is not None:
                return WakeHit("Hey Artemis", tail)
            return None

        partial = json.loads(self._recognizer.PartialResult()).get("partial", "").strip()
        if self.debug and partial and partial != self._last_partial:
            print(f"[Wake debug: partial] {partial}")
        self._last_partial = partial

        # Partial STT frequently revises words. Only wake on the *entire*
        # exact phrase, not a partial with an extra command, which might be cut.
        if normalize(partial) in {normalize(phrase) for phrase in WAKE_ALIASES}:
            return WakeHit("Hey Artemis")
        return None


class JarvisDetector:
    """Optional existing trained wake-word model for quick fallback."""

    def __init__(self, debug=False):
        from openwakeword.model import Model
        self.debug = debug
        try:
            self._model = Model(wakeword_models=[WAKE_MODEL], inference_framework="onnx")
        except Exception as exc:
            raise RuntimeError(
                "Optional 'Hey Jarvis' model is unavailable. "
                "Run: .venv\\Scripts\\python.exe setup_models.py --include-jarvis"
            ) from exc

    def reset(self):
        self._model.reset()

    def process(self, frame: bytes) -> WakeHit | None:
        scores = self._model.predict(np.frombuffer(frame, dtype=np.int16))
        confidence = max(
            (float(value) for key, value in scores.items() if WAKE_SCORE_KEYWORD in key.lower()),
            default=0.0,
        )
        if confidence >= WAKE_THRESHOLD:
            return WakeHit("Hey Jarvis")
        return None
