"""ARTEMIS offline voice feedback.

Piper voice: models/voices/en_GB-alba-medium.onnx (+ .onnx.json).
No temporary audio files. If Piper is unavailable, retain Windows SAPI5 fallback.
"""
from __future__ import annotations

import io
import wave
from pathlib import Path

VOICE_MODEL = Path(__file__).resolve().parents[1] / 'models' / 'voices' / 'en_GB-alba-medium.onnx'


class Speaker:
    def __init__(self, enabled=True):
        self.engine = None
        self.piper = None
        self._piper_config_cls = None
        if not enabled:
            return

        if VOICE_MODEL.is_file() and VOICE_MODEL.with_suffix('.onnx.json').is_file():
            try:
                from piper import PiperVoice, SynthesisConfig
                self.piper = PiperVoice.load(str(VOICE_MODEL), use_cuda=False)
                self._piper_config_cls = SynthesisConfig
                print('[Voice] Piper: British English Alba (offline).')
                return
            except Exception as exc:
                print(f'[Voice] Piper unavailable ({type(exc).__name__}: {exc}); using Windows voice.')
        else:
            print('[Voice] Piper voice files absent; using Windows voice.')

        try:
            import pyttsx3
            self.engine = pyttsx3.init(driverName='sapi5')
            self.engine.setProperty('rate', 175)
        except Exception as exc:
            print(f'[Speech disabled: {type(exc).__name__}: {exc}]')

    def say(self, message: str):
        print(f'ARTEMIS: {message}')
        if self.piper is not None:
            try:
                import winsound
                audio = io.BytesIO()
                config = self._piper_config_cls(length_scale=1.12)
                with wave.open(audio, 'wb') as wav:
                    self.piper.synthesize_wav(message, wav, syn_config=config)
                winsound.PlaySound(audio.getvalue(), winsound.SND_MEMORY | winsound.SND_SYNC)
                return
            except Exception as exc:
                print(f'[Piper TTS error: {type(exc).__name__}: {exc}]')
                # Do not silently repeat a command action; only spoken feedback failed.
                return
        if self.engine is not None:
            try:
                self.engine.say(message)
                self.engine.runAndWait()
            except Exception as exc:
                print(f'[TTS error: {type(exc).__name__}; falling back to text]')
                self.engine = None
