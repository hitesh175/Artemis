"""Offline openWakeWord listener for a locally trained Hey Artemis ONNX model.

No network calls and no audio writes. Uses the same 16kHz/16-bit 80ms
microphone buffers as the existing Artemis pipeline.
"""
from pathlib import Path

import numpy as np

from .config import PROJECT_ROOT
from .wakeword import WakeHit

MODEL_PATH = PROJECT_ROOT / "models" / "wakewords" / "hey_artemis.onnx"
DEFAULT_THRESHOLD = 0.50


def validate_model_path(path):
    """Provide an actionable error when the trained model is not installed."""
    model_path = Path(path)
    if not model_path.is_file():
        raise RuntimeError(
            f"Custom wake-word model is missing: {model_path}\n"
            "Train/download hey_artemis.onnx in Colab, then place it at that path. "
            "If Colab exported hey_artemis.onnx.data, copy that file beside it too."
        )
    if model_path.suffix.lower() != ".onnx":
        raise ValueError("Use an .onnx openWakeWord classifier, not a ZIP or .tflite file")
    return model_path


class ArtemisOpenWakeWordDetector:
    """A restricted, 16kHz, single-model detector; no STT during standby."""

    def __init__(self, model_path=MODEL_PATH, threshold=DEFAULT_THRESHOLD):
        self.model_path = validate_model_path(model_path)
        if not (0.05 <= float(threshold) <= 0.95):
            raise ValueError("Wake threshold must be between 0.05 and 0.95")
        self.threshold = float(threshold)
        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise RuntimeError(
                "openwakeword is missing from Artemis .venv. "
                "Run: .\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt"
            ) from exc
        try:
            self._model = Model(wakeword_models=[str(self.model_path)], inference_framework="onnx")
        except Exception as exc:
            raise RuntimeError(
                "The custom ONNX model could not be loaded. Check that it is a trained "
                "openWakeWord model, and that any .onnx.data sidecar is alongside it."
            ) from exc
        self.last_score = 0.0
        self.top_score = 0.0

    def process(self, frame: bytes):
        if not frame:
            return None
        pcm = np.frombuffer(frame, dtype=np.int16)
        if pcm.size == 0:
            return None
        # One 80 ms frame = 1280 samples at 16 kHz, consistent with Artemis mic.
        scores = self._model.predict(pcm)
        # Only one explicitly supplied custom model is loaded. The map contains
        # that model's score under its filename stem.
        self.last_score = max((float(v) for v in scores.values()), default=0.0)
        self.top_score = max(self.last_score, self.top_score)
        if self.last_score >= self.threshold:
            return WakeHit("Hey Artemis")
        return None

    def reset(self):
        self._model.reset()
        self.last_score = 0.0
        self.top_score = 0.0
