"""True local keyword spotting: normal conversations are NOT transcribed here.

The model consumes microphone audio in memory and outputs only keyword matches.
It is not speaker authentication and can still false-trigger on similar phrases.
"""
from pathlib import Path
from unittest import result
import numpy as np

from .config import PROJECT_ROOT, SAMPLE_RATE
from .wakeword import WakeHit

KWS_FOLDER = PROJECT_ROOT / 'models' / 'sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01'
WEIGHTS = 'epoch-12-avg-2-chunk-16-left-64.int8.onnx'


def paths(model_dir=KWS_FOLDER):
    directory = Path(model_dir)
    return dict(
        tokens=str(directory / 'tokens.txt'),
        encoder=str(directory / ('encoder-' + WEIGHTS)),
        decoder=str(directory / ('decoder-' + WEIGHTS)),
        joiner=str(directory / ('joiner-' + WEIGHTS)),
        keywords_file=str(directory / 'artemis_keywords.txt'),
    )


class ArtemisKeywordDetector:
    """Sherpa-ONNX streaming keyword spotter for 'HEY ARTEMIS'."""
    def __init__(self, model_dir=KWS_FOLDER, *, num_threads=2):
        try:
            import sherpa_onnx
        except ImportError as exc:
            raise RuntimeError(
                'sherpa-onnx is missing. Run: .venv\\Scripts\\python.exe -m pip '
                'install sherpa-onnx'
            ) from exc
        required = paths(model_dir)
        missing = [name for name, path in required.items() if not Path(path).is_file()]
        if missing:
            raise RuntimeError(
                'Missing keyword-spotting files: ' + ', '.join(missing)
                + '. Run: .venv\\Scripts\\python.exe setup_keyword_model.py'
            )
        self.spotter = sherpa_onnx.KeywordSpotter(
            **required,
            num_threads=num_threads,
            provider='cpu',
            keywords_threshold=0.25,
        )
        self.stream = self.spotter.create_stream()

    def reset(self):
        self.spotter.reset_stream(self.stream)

    def process(self, frame: bytes):
        pcm = np.frombuffer(frame, dtype=np.int16)
        if pcm.size == 0:
            return None
        samples = pcm.astype(np.float32) / 32768.0
        self.stream.accept_waveform(SAMPLE_RATE, samples)
        while self.spotter.is_ready(self.stream):
            self.spotter.decode_stream(self.stream)
            result = self.spotter.get_result(self.stream)
            if result:
                print(f"[Keyword detector result] {result!r}")
            # Keyword spotter returns a phrase or an empty result, not a transcript.
            if result and 'HEY ARTEMIS' in str(result).upper().replace('_', ' '):
                self.reset()
                return WakeHit('Hey Artemis')
        return None
