"""Nonblocking local Kokoro Isabella TTS, with existing Artemis Piper fallback.
Speech only for displayed Ollama replies; it does not execute OS commands.
"""
import sys
import threading
import time
from performance_log import PERFORMANCE
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
        self._cancel = threading.Event()
        self._speaker_lock = threading.Lock()

    def status(self):
        with self.lock:
            return {'enabled': self.enabled, 'playing': self.playing,
                    'stopping': self.playing and self._cancel.is_set(),
                    'error': self.error, 'revision': self.revision}

    def set_enabled(self, enabled):
        with self.lock:
            self.enabled = bool(enabled)
            if not self.enabled:self.stop()
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
            self._cancel = threading.Event()
            cancel = self._cancel
            self.error = ''
            self.revision += 1
        threading.Thread(target=self._run, args=(text,cancel), daemon=True).start()
        return {'ok': True}

    def clear_error(self):
        with self.lock:
            if not self.playing and self.error:
                self.error = ''
                self.revision += 1

    def stop(self):
        with self.lock:
            self._cancel.set()
            self.revision += 1
            return {'ok':True, **self.status()}

    def prepare(self):
        with self._speaker_lock:
            if self.speaker is None:
                from artemis.voice import Speaker
                self.speaker=Speaker(enabled=True)
            if getattr(self.speaker,'kokoro',None) is None and getattr(self.speaker,'piper',None) is None:
                self.speaker=None
                raise RuntimeError('No cached offline speech engine is available.')
            return self.speaker

    def _run(self, text, cancel):
        started=time.perf_counter();load_started=started;load_seconds=0;timings={};failed=False
        try:
            if cancel.is_set():return
            self.prepare()
            load_seconds=time.perf_counter()-load_started
            if cancel.is_set():return
            timings=self.speaker.say(text,cancel_event=cancel) or {}
        except Exception as exc:
            failed=True
            with self.lock:
                self.error = '' if cancel.is_set() else str(exc)
                # Recreate the engine on an explicit retry after a failed initialization/playback.
                self.speaker = None
            print('[ARTEMIS Desktop speech]', exc, flush=True)
        finally:
            PERFORMANCE.record('speech','cancelled' if cancel.is_set() else 'error' if failed else 'completed',
                               time.perf_counter()-started,model_load_seconds=load_seconds,**timings)
            with self.lock:
                self.playing = False
                self.revision += 1
