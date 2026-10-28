"""Local push-to-talk transcription for ARTEMIS Desktop V2.

Short speech gets a different decode configuration than long recordings.
Windows app controls and audio capture behavior are unchanged.
"""
import os
import threading
import time
from speech_endpoint import SpeechEndpoint


class WhisperInput:
    def __init__(self):
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._cancel = threading.Event()
        self._auto_stop = False
        self._thread = None
        self._model = None
        self._model_name = None
        self._status = {'state': 'idle', 'text': '', 'error': '', 'revision': 0, 'level': 0.0}

    def _update(self, state, text='', error=''):
        if self._auto_stop:
            print('[Hands-free recognition]',state, error or '',flush=True)
        with self._lock:
            self._status = {
                'state': state, 'text': text, 'error': error,
                'revision': self._status['revision'] + 1,
                'level': 0.0,
                'automatic': self._auto_stop,
            }

    def status(self):
        with self._lock:
            return dict(self._status)

    def start(self, auto_stop=False):
        with self._lock:
            if self._thread and self._thread.is_alive():
                return {'ok': False, 'error': 'Recording or transcription already in progress'}
            self._stop = threading.Event()
            self._cancel.clear()
            self._auto_stop = bool(auto_stop)
            self._status = {
                'state': 'listening', 'text': '', 'error': '',
                'revision': self._status['revision'] + 1,
                'level': 0.0,
                'automatic': self._auto_stop,
            }
            self._thread = threading.Thread(target=self._run, args=(self._stop,), daemon=True)
            self._thread.start()
        return {'ok': True}

    def stop(self):
        with self._lock:
            if not self._thread or not self._thread.is_alive():
                return {'ok': False, 'error': 'No active microphone session'}
            if self._status['state'] != 'listening':
                return {'ok': False, 'error': 'Microphone is not recording'}
            self._stop.set()
        return {'ok': True}

    def cancel(self):
        self._cancel.set()
        self._stop.set()
        self._update('idle')
        return {'ok': True}

    def _load_model(self):
        from faster_whisper import WhisperModel
        name = os.environ.get('ARTEMIS_WHISPER_MODEL', 'base.en').strip() or 'base.en'
        if name not in ('base.en', 'small.en', 'medium.en'):
            raise ValueError('ARTEMIS_WHISPER_MODEL must be base.en, small.en or medium.en')
        if self._model is None or self._model_name != name:
            allow_download = os.environ.get('ARTEMIS_WHISPER_ALLOW_DOWNLOAD', '0') == '1'
            # CPU int8 is deliberately kept as the known-working default.
            # CPU medium may be slow; GPU selection is a separate compatibility step.
            device = os.environ.get('ARTEMIS_WHISPER_DEVICE', 'cpu').strip().lower()
            if device not in ('cpu', 'cuda'):
                raise ValueError('ARTEMIS_WHISPER_DEVICE must be cpu or cuda')
            compute_type = 'float16' if device == 'cuda' else 'int8'
            try:
                self._model = WhisperModel(name, device=device, compute_type=compute_type,
                                           local_files_only=not allow_download)
            except Exception as exc:
                if not allow_download:
                    raise RuntimeError(
                        f"Whisper model '{name}' isn't available locally (or couldn't load): {exc}. "
                        'Use the included enable_small_whisper.ps1 once to download small.en, '
                        'or unset ARTEMIS_WHISPER_MODEL to use the cached base.en model.'
                    ) from exc
                raise
            self._model_name = name
        return self._model

    def _run(self, stop):
        try:
            if self._cancel.is_set():
                return
            import queue
            import numpy as np
            import sounddevice as sd
            chunks = []
            from collections import deque
            preroll = deque(maxlen=4)
            endpoint = SpeechEndpoint() if self._auto_stop else None
            timed_out = False
            q = queue.Queue(maxsize=120)
            rate = 16000

            def callback(indata, frames, timing, status):
                try:
                    q.put_nowait(indata[:, 0].copy())
                except queue.Full:
                    pass

            with sd.InputStream(samplerate=rate, channels=1, dtype='float32',
                                blocksize=1600, callback=callback):
                start_time = time.monotonic()
                while not stop.is_set() and time.monotonic() - start_time < 45:
                    try:
                        chunk = q.get(timeout=.15)
                        if endpoint is None:
                            chunks.append(chunk)
                        # Reuse captured audio; never open a second microphone stream.
                        rms = float(np.sqrt(np.mean(chunk * chunk)))
                        if endpoint is not None:
                            was_started = endpoint.started
                            preroll.append(chunk)
                            decision = endpoint.feed(rms, len(chunk) / rate)
                            if endpoint.started:
                                if not was_started:
                                    chunks.extend(preroll)
                                else:
                                    chunks.append(chunk)
                            if decision != 'continue':
                                timed_out = decision == 'timeout'
                                break
                        level = min(1.0, max(0.0, (rms - .003) * 15.0))
                        with self._lock:
                            if self._status['state'] == 'listening':
                                self._status['level'] = level
                    except queue.Empty:
                        pass
                while True:
                    try:
                        extra = q.get_nowait()
                        if endpoint is None:
                            chunks.append(extra)
                    except queue.Empty:
                        break

            if self._cancel.is_set():
                return
            if timed_out:
                # Silence is a waiting state, not a broken microphone or model.
                self._update('waiting')
                return
            if endpoint is not None and not endpoint.started:
                self._update('waiting')
                return
            if not chunks:
                self._update('error', error='No microphone audio captured')
                return
            audio = np.concatenate(chunks).astype(np.float32, copy=False)
            duration = len(audio) / rate
            if duration < .45 or float(np.max(np.abs(audio))) < .01:
                self._update('error', error='No clear speech detected; try again')
                return

            # For very short utterances, aggressive VAD risks discarding words.
            # A small end pad avoids truncating the last phoneme after Stop is clicked.
            audio = np.pad(audio, (0, int(rate * 0.18)))
            self._update('transcribing')
            model = self._load_model()
            short = duration < 4.0
            segments, _ = model.transcribe(
                audio, language='en', beam_size=5,
                best_of=5, temperature=0,
                vad_filter=not short,
                condition_on_previous_text=False,
                without_timestamps=True,
                # A balanced context, rather than a list dominated by app names.
                initial_prompt=(
                    'A natural English conversation with Artemis, a desktop AI assistant. '
                    'Common questions include: How are you? What can you do? '
                    'Application names include Spotify, Discord and Notepad.'
                ),
            )
            transcript = ' '.join(seg.text.strip() for seg in segments).strip()
            if self._cancel.is_set():
                return
            if transcript:
                self._update('done', text=transcript)
            else:
                self._update('error', error='Whisper could not identify speech')
        except Exception as exc:
            if not self._cancel.is_set():
                self._update('error', error=f'Microphone/Whisper failed: {exc}')
