"""ARTEMIS configuration: Stage 2 offline wake phrase settings."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VOSK_PATH = PROJECT_ROOT / "models" / "vosk-model-small-en-us-0.15"
SAMPLE_RATE = 16_000
FRAME_SAMPLES = 1_280  # 80 ms of 16 kHz mono PCM

# Default: transcript-based offline trigger, no custom trained model required.
WAKE_PHRASE = "Hey Artemis"
WAKE_ALIASES = ("hey artemis",)

# Optional original openWakeWord fallback (--wake-mode jarvis).
WAKE_MODEL = "hey_jarvis_v0.1"
WAKE_SCORE_KEYWORD = "jarvis"
WAKE_THRESHOLD = 0.55

MAX_COMMAND_SECONDS = 8.0
WAIT_FOR_SPEECH_SECONDS = 4.0
SILENCE_AFTER_SPEECH_SECONDS = 1.2
MIC_RMS_THRESHOLD = 350
