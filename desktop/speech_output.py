"""Nonblocking local Kokoro Isabella TTS, with existing Artemis Piper fallback.
Speech only for displayed Ollama replies; it does not execute OS commands.
"""
import sys
import threading
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

class SpeechOutput:
    def __init__(self):
        self.lock = threading.RLock()
        self.enabled = True
        self.playing = False
        self.error = ''
        self.revision = 0
        self.speaker = None

    def status(self):
        with self.lock:
            return {'enabled': self.enabled, 'playing': self.playing,
                    'error': self.error, 'revision': self.revision}

    def set_enabled(self, enabled):
        with self.lock:
            self.enabled = bool(enabled)
            self.revision += 1
            return {'ok': True, **self.status()}

    def speak(self, text):
        if not isinstance(text, str) or not text.strip() or len(text)>5000:
            return {'ok': False, 'error': 'Invalid speech text'}
        with self.lock:
            if not self.enabled:
                return {'ok': False, 'error': 'Speech output is muted'}
            if self.playing:
                return {'ok': False, 'error': 'Isabella is already speaking'}
            self.playing = True
            self.error = ''
            self.revision += 1
        threading.Thread(target=self._run, args=(text,), daemon=True).start()
        return {'ok': True}

    def clear_error(self):
        with self.lock:
            if not self.playing and self.error:
                self.error = ''
                self.revision += 1

    def _run(self, text):
        try:
            if self.speaker is None:
                from artemis.voice import Speaker
                self.speaker = Speaker(enabled=True)
            if getattr(self.speaker, 'kokoro', None) is None and getattr(self.speaker, 'piper', None) is None:
                raise RuntimeError('No offline speech engine available. Check voice_test models or Piper fallback.')
            self.speaker.say(text)
        except Exception as exc:
            with self.lock:
                self.error = str(exc)
                # Recreate the engine on an explicit retry after a failed initialization/playback.
                self.speaker = None
            print('[ARTEMIS Desktop speech]', exc, flush=True)
        finally:
            with self.lock:
                self.playing = False
                self.revision += 1
