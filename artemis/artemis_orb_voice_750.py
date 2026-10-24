"""ARTEMIS Stage 7.2.3: Ollama conversation + approved app control + hands-free planet.
Audio stays in memory; no automatic wake-word activation.
"""
from __future__ import annotations
import sys, time, threading, collections, re
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (QApplication, QLabel, QPushButton, QCheckBox,
                               QVBoxLayout, QHBoxLayout, QWidget)
from artemis_orb_planet_634 import PlanetOrb
from artemis_app_resolver_723 import discover_apps, match_app, parse_open_request, launch_shortcut

_WHISPER_MODEL = None
_WHISPER_LOCK = threading.Lock()

def whisper_model():
    global _WHISPER_MODEL
    with _WHISPER_LOCK:
        if _WHISPER_MODEL is None:
            from faster_whisper import WhisperModel
            t0 = time.perf_counter()
            _WHISPER_MODEL = WhisperModel('base.en', device='cpu', compute_type='int8', local_files_only=True)
            print(f'[ARTEMIS] Whisper initialized in {time.perf_counter()-t0:.2f}s', flush=True)
        return _WHISPER_MODEL


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))



def approved_command(text, permitted):
    from artemis.commands import interpret, execute
    from artemis.streaming_command import remove_wake_phrase
    text = remove_wake_phrase(text).strip()
    if not text:
        return 'No command detected.'
    app_name = parse_open_request(text)
    if app_name:
        apps = discover_apps()
        match = match_app(app_name, apps)
        if match.kind == 'exact':
            if not permitted:
                return f'Preview: open {match.app.name} (installed app found).'
            try:
                launch_shortcut(match.app)
                return f'Opening {match.app.name}.'
            except Exception as exc:
                return f'Could not open {match.app.name}: {exc}'
        if match.kind == 'confirm':
            # UI handles this without executing anything automatically.
            return f'CONFIRM_APP:{match.app.name}::' + (f'APPID={match.app.app_id}' if match.app.app_id else str(match.app.shortcut))
        # Do not send recognized app-opening requests to the old hardcoded
        # interpreter: its generic "try Help" response is misleading.
        # Still allow built-in approved commands (e.g. Notepad).
        builtin = interpret(text)
        if builtin.name != 'unknown':
            if not permitted:
                return f'Preview: {builtin.name.replace("_", " ")}.'
            result, _ = execute(builtin)
            return result
        return f'I understood open {app_name}, but could not find it in installed Windows apps.'
    intent = interpret(text)
    if intent.name == 'unknown':
        return 'I heard you, but could not identify an approved command or installed app.'
    if not permitted:
        suffix = f' — {intent.target}' if intent.target else ''
        return f'Preview: {intent.name.replace("_", " ")}{suffix}.'
    result, _ = execute(intent)
    return result


def clean_ai_reply(text):
    """Drop leaked reasoning, never speak it; fail closed on unfinished tags."""
    import re
    text = re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL | re.IGNORECASE)
    if '</think>' in text.lower():
        text = re.split(r'</think>', text, flags=re.IGNORECASE)[-1]
    if '<think>' in text.lower():
        text = re.split(r'<think>', text, flags=re.IGNORECASE)[0]
    return text.strip()


def respond_to_user(text, permitted, history):
    """Approved local application requests use the existing trusted resolver.
    All other speech goes to the Ollama conversational model (no tool privileges).
    """
    from artemis.streaming_command import remove_wake_phrase
    normalized = remove_wake_phrase(text).strip()
    app_target = parse_open_request(normalized)
    if app_target:
        print(f'[ARTEMIS] Windows app request: {app_target!r}', flush=True)
        return approved_command(normalized, permitted)
    # Existing simple builtins retain their fixed, audited behavior.
    if re.fullmatch(r'(?i)\s*(?:help|what (?:can you do|commands)|list commands)\s*[?.!]*', normalized):
        return approved_command('help', permitted)
    import json, urllib.request, urllib.error
    system = (
        'You are Artemis, a personal offline-first Windows desktop AI assistant. '
        'You are not the Greek goddess, and you are not named Qwen. '
        'Talk naturally, warmly and concisely: usually one to three sentences. Do not use emojis, markdown, lists or stage directions. '
        'You can chat and answer general questions. Windows app control is handled by '
        'a separate trusted controller, not by you. Do not claim to have opened, '
        'closed or modified anything unless the controller reported success. '
        'Never reveal internal reasoning or produce <think> tags. '
        'If asked to execute actions you cannot perform, explain that limitation.'
    )
    messages = [{'role':'system','content':system}]
    messages += history[-12:]
    messages.append({'role':'user','content':normalized})
    body = json.dumps({'model':'artemis','messages':messages,'stream':False,
                       'think':False,'options':{'num_predict':160}}).encode('utf-8')
    req = urllib.request.Request('http://127.0.0.1:11434/api/chat', data=body,
                                 headers={'Content-Type':'application/json'}, method='POST')
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            result = json.load(resp)
    except urllib.error.URLError as exc:
        return 'The local AI brain is unavailable. Please check that Ollama is running.'
    answer = clean_ai_reply(result.get('message',{}).get('content',''))
    return answer or 'I could not generate a clean reply. Could you try again?'


class ListenWorker(QObject):
    """Waits for speech, captures pre-roll, ends on trailing silence.

    Single mic owner; mic closes before transcription or TTS. All processing
    lives on a worker QThread, not the Qt GUI thread.
    """
    level = Signal(float)
    status = Signal(str)
    state = Signal(str)
    result = Signal(str, str)
    failed = Signal(str)
    finished = Signal()
    cancelled = Signal()

    def __init__(self, permitted, history):
        super().__init__()
        self.stop = threading.Event()
        self.finish_utterance = threading.Event()
        self.permitted = permitted
        self.history = history

    @Slot()
    def run(self):
        try:
            import sounddevice as sd
            import queue
            rate = 16000
            block = 1600  # 100 ms
            q = queue.Queue(maxsize=25)
            def cb(indata, frames, timing, status):
                data = indata[:, 0].copy()
                try:
                    q.put_nowait(data)
                except queue.Full:
                    try:
                        q.get_nowait()
                        q.put_nowait(data)
                    except queue.Empty:
                        pass

            self.state.emit('Listening')
            self.status.emit('Waiting for your voice…')
            pre = collections.deque(maxlen=4)  # 400 ms preceding activation
            captured = []
            started = False
            active_blocks = 0
            quiet_blocks = 0
            ambient = []
            threshold = .008
            begin = time.monotonic()
            last_status = begin
            with sd.InputStream(samplerate=rate, channels=1, dtype='float32',
                                blocksize=block, callback=cb):
                while not self.stop.is_set():
                    try:
                        data = q.get(timeout=.2)
                    except queue.Empty:
                        continue
                    if self.finish_utterance.is_set() and not started:
                        break
                    rms = float(np.sqrt(np.mean(data * data)))
                    peak = float(np.max(np.abs(data)))
                    self.level.emit(min(1.0, rms*15.0))
                    if time.monotonic()-begin < .7:
                        ambient.append(rms)
                        pre.append(data)
                        continue
                    if not started and time.monotonic()-begin > 25:
                        self.status.emit('No speech detected; restarting microphone…')
                        break
                    if not started:
                        if ambient:
                            threshold = max(.005, min(.035, float(np.median(ambient))*2.0))
                        if rms > threshold and peak > .009:
                            active_blocks += 1
                        else:
                            active_blocks = 0
                        if active_blocks >= 2:  # 200 ms confirms onset
                            started = True
                            captured.extend(pre)
                            captured.append(data)
                            self.status.emit('Hearing you… pause, or click Finish sentence')
                        else:
                            pre.append(data)
                    else:
                        captured.append(data)
                        quiet_blocks = quiet_blocks + 1 if rms < max(threshold*1.15, .007) else 0
                        if self.finish_utterance.is_set():
                            break
                        if quiet_blocks >= 12:  # about 1.2 seconds quiet
                            break
                        if len(captured) * block / rate >= 12:
                            break
            if self.stop.is_set():
                self.cancelled.emit()
                return
            if not started or not captured:
                self.cancelled.emit()
                return
            audio = np.concatenate(captured).astype(np.float32, copy=False)
            duration = len(audio) / rate
            peak = float(np.max(np.abs(audio)))
            if duration < .5 or peak < .012:
                self.cancelled.emit()
                return
            self.state.emit('Thinking')
            self.status.emit(f'Transcribing locally ({duration:.1f} s)…')
            model = whisper_model()
            parts, _ = model.transcribe(audio, language='en', beam_size=5,
                vad_filter=True, condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt='Windows desktop voice assistant. Application names: Notepad, Spotify, Discord, Calculator, Visual Studio Code.')
            heard = ' '.join(part.text.strip() for part in parts).strip()
            if self.stop.is_set():
                self.cancelled.emit()
                return
            if not heard:
                self.cancelled.emit()
                return
            self.state.emit('Thinking')
            reply = respond_to_user(heard, self.permitted, self.history)
            self.result.emit(heard, reply)
        except Exception as exc:
            self.failed.emit(f'{type(exc).__name__}: {exc}')
        finally:
            self.finished.emit()


class TalkWorker(QObject):
    finished = Signal()
    failed = Signal(str)

    def __init__(self, reply):
        super().__init__()
        self.reply = reply

    @Slot()
    def run(self):
        try:
            from artemis.voice_fast_750 import Speaker
            voice = Speaker(enabled=True)
            if getattr(voice, 'piper', None) is None and getattr(voice, 'engine', None) is None:
                raise RuntimeError('No speech engine available. Install pyttsx3 or configure Piper.')
            voice.say(self.reply)
        except Exception as exc:
            self.failed.emit(f'Speech unavailable: {exc}')
        finally:
            self.finished.emit()


class VoiceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ARTEMIS Stage 7.5 — Responsive Conversation')
        self.resize(840, 720)
        self.setMinimumSize(600, 570)
        self.setStyleSheet('''
          QWidget { background:#0E1119; color:#E2E6EF; font-family:'Segoe UI'; }
          QLabel#title { color:#93A2B8; font-size:15px; font-weight:bold; }
          QLabel#state { font-size:25px; font-weight:600; }
          QLabel#text { color:#A9B4C7; font-size:14px; }
          QPushButton { background:#253246; border:1px solid #3D4C65;
               border-radius:18px; padding:12px 20px; font-size:14px; }
          QPushButton:hover { background:#354962; }
          QPushButton:disabled { color:#798396; background:#1B2533; }
          QCheckBox { color:#A9B4C7; padding:7px; }
        ''')
        outer = QVBoxLayout(self)
        outer.setContentsMargins(32,22,32,24)
        heading = QLabel('A R T E M I S', objectName='title')
        heading.setAlignment(Qt.AlignCenter)
        outer.addWidget(heading)
        self.orb = PlanetOrb()
        outer.addWidget(self.orb,1)
        self.activity = QLabel('Idle', objectName='state')
        self.activity.setAlignment(Qt.AlignCenter)
        outer.addWidget(self.activity)
        self.subtitle = QLabel('Start conversation to listen automatically.', objectName='text')
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setWordWrap(True)
        self.subtitle.setMinimumHeight(48)
        outer.addWidget(self.subtitle)
        checks = QHBoxLayout()
        self.permitted = QCheckBox('Allow approved commands')
        self.tts = QCheckBox('Speak responses')
        self.tts.setChecked(True)  # Voice mode should speak by default
        checks.addStretch(); checks.addWidget(self.permitted)
        checks.addWidget(self.tts); checks.addStretch()
        outer.addLayout(checks)
        control = QHBoxLayout()
        self.button = QPushButton('🎙  Start conversation')
        self.button.clicked.connect(self.toggle_session)
        control.addStretch(); control.addWidget(self.button); control.addStretch()
        outer.addLayout(control)
        self.confirm_button = QPushButton('Confirm suggested app')
        self.confirm_button.setVisible(False)
        self.confirm_button.clicked.connect(self.confirm_launch)
        outer.addWidget(self.confirm_button, alignment=Qt.AlignCenter)
        self.pending_app = None
        self.history = []
        hint = QLabel('Local Ollama brain • conversation stays in RAM • Stop conversation to mute', objectName='text')
        hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(hint)
        self.session = False
        self.listening_thread = None
        self.listening_worker = None
        self.speaking_thread = None
        self.speaking_worker = None
        self.pending_reply = None
        self.speech_failed = False
        self.closing_requested = False
        self.rearm = QTimer(self)
        self.rearm.setSingleShot(True)
        self.rearm.timeout.connect(self.arm_listening)
        threading.Thread(target=self._warm_voice, daemon=True, name='artemis-voice-warmup').start()

    @staticmethod
    def _warm_voice():
        """Warm synthesis in the background; never opens audio output during startup."""
        try:
            from artemis.voice_fast_750 import Speaker, _LOAD_LOCK, _CACHE, KOKORO_VOICE
            sp = Speaker(enabled=True)
            if sp.kokoro is None:
                return
            # Precompute common app acknowledgements; keep activation responsive.
            with _LOAD_LOCK:
                for message in ('Opening Spotify.', 'Opening Discord.', 'Opening Notepad.'):
                    audio, rate = sp.kokoro.create(message, voice=KOKORO_VOICE, speed=1.04, lang='en-gb')
                    _CACHE[(message, KOKORO_VOICE)] = (audio, rate)
            print('[ARTEMIS] Isabella preloaded; common app acknowledgements cached.', flush=True)
        except Exception as exc:
            print(f'[ARTEMIS] Optional voice warmup skipped: {exc}', flush=True)

    def show_state(self, value):
        self.orb.set_state(value)
        self.activity.setText(value)

    def confirm_launch(self):
        app = self.pending_app
        self.pending_app = None
        self.confirm_button.setVisible(False)
        if not app:
            return
        if not self.permitted.isChecked():
            self.subtitle.setText(f'Preview: would open {app.name}. Enable approved commands to launch.')
            return
        try:
            launch_shortcut(app)
            self.subtitle.setText(f'Opening {app.name}.')
        except Exception as exc:
            self.show_state('Error')
            self.subtitle.setText(f'Could not launch: {exc}')

    def toggle_session(self):
        if self.session:
            if self.listening_worker is not None and self.listening_thread is not None and self.listening_thread.isRunning():
                self.listening_worker.finish_utterance.set()
                self.button.setEnabled(False)
                self.button.setText('Processing sentence…')
                return
            self.end_session()
        else:
            self.session = True
            self.permitted.setEnabled(False)
            self.button.setText('■  Stop conversation')
            self.arm_listening()

    def end_session(self):
        self.session = False
        self.pending_app = None
        self.confirm_button.setVisible(False)
        self.rearm.stop()
        self.button.setText('🎙  Start conversation')
        self.button.setEnabled(True)
        if self.listening_worker:
            self.listening_worker.stop.set()
        self.subtitle.setText('Conversation stopped. Microphone will close.')
        self.show_state('Sleep')
        if self.listening_thread is None and self.speaking_thread is None:
            self.permitted.setEnabled(True)

    def arm_listening(self):
        if not self.session or self.listening_thread or self.speaking_thread or self.closing_requested:
            return
        self.button.setEnabled(True)
        self.button.setText('✓  Finish sentence')
        self.show_state('Listening')
        self.subtitle.setText('Listening… speak, then pause naturally. Click Finish sentence if needed.')
        th = QThread(self)
        wk = ListenWorker(self.permitted.isChecked(), list(self.history))
        wk.moveToThread(th)
        self.listening_thread = th
        self.listening_worker = wk
        th.started.connect(wk.run)
        wk.level.connect(self.orb.set_audio_level)
        wk.state.connect(self.show_state)
        wk.status.connect(self.subtitle.setText)
        wk.result.connect(self.on_result)
        wk.failed.connect(self.on_speech_error)
        wk.cancelled.connect(self.on_cancelled)
        wk.finished.connect(th.quit)
        wk.finished.connect(wk.deleteLater)
        th.finished.connect(th.deleteLater)
        th.finished.connect(self.on_listening_finished)
        th.start()

    @Slot(str,str)
    def on_result(self, heard, reply):
        if not reply.startswith('CONFIRM_APP:'):
            self.history.extend([{'role':'user','content':heard}, {'role':'assistant','content':reply}])
            self.history = self.history[-16:]
        if reply.startswith('CONFIRM_APP:'):
            from artemis_app_resolver_723 import Candidate
            try:
                title, path = reply[len('CONFIRM_APP:'):].split('::', 1)
                if path.startswith('APPID='):
                    self.pending_app = Candidate(title, Path(), path[6:])
                else:
                    self.pending_app = Candidate(title, Path(path))
                self.confirm_button.setText(f'Confirm: open {title}')
                self.confirm_button.setVisible(True)
                self.subtitle.setText(f'You: {heard}\nDid you mean {title}? Click to confirm.')
                reply = ''  # Do not speak the internal confirmation token
            except ValueError:
                reply = 'App match was invalid.'
        else:
            self.pending_app = None
            self.confirm_button.setVisible(False)
            self.subtitle.setText(f'You: {heard}\nArtemis: {reply}')
        # IMPORTANT: wait until microphone stream has closed before beginning TTS.
        self.pending_reply = reply if (reply and self.session and self.tts.isChecked()) else None
        if not self.pending_reply and self.session:
            self.show_state('Idle')

    @Slot(str)
    def on_error(self, error):
        if self.session:
            self.show_state('Error')
            self.subtitle.setText(error)

    @Slot()
    def on_cancelled(self):
        if self.session:
            self.subtitle.setText('No clear speech detected. Listening again…')

    @Slot()
    def on_listening_finished(self):
        self.button.setEnabled(True)
        self.button.setText('■  Stop conversation')
        self.listening_thread = None
        self.listening_worker = None
        if self.closing_requested:
            self.close()
            return
        if not self.session:
            self.permitted.setEnabled(True)
            return
        if self.pending_reply is not None:
            reply = self.pending_reply
            self.pending_reply = None
            self.start_talking(reply)
        else:
            self.rearm.start(800)

    def start_talking(self, reply):
        if not self.session or self.speaking_thread:
            return
        self.speech_failed = False
        self.show_state('Speaking')
        th = QThread(self)
        wk = TalkWorker(reply)
        wk.moveToThread(th)
        self.speaking_thread = th
        self.speaking_worker = wk
        th.started.connect(wk.run)
        wk.failed.connect(self.on_speech_error)
        wk.finished.connect(th.quit)
        wk.finished.connect(wk.deleteLater)
        th.finished.connect(th.deleteLater)
        th.finished.connect(self.on_speaking_finished)
        th.start()

    @Slot(str)
    def on_speech_error(self, error):
        self.speech_failed = True
        self.show_state('Error')
        self.subtitle.setText(error)
        print('[ARTEMIS TTS]', error, flush=True)

    @Slot()
    def on_speaking_finished(self):
        self.speaking_thread = None
        self.speaking_worker = None
        if self.closing_requested:
            self.close()
            return
        if self.session:
            if not self.speech_failed:
                self.show_state('Idle')
            self.rearm.start(900 if self.speech_failed else 350)  # pause before mic resumes
        else:
            self.permitted.setEnabled(True)

    def closeEvent(self,event):
        self.closing_requested = True
        self.end_session()
        if self.listening_thread or self.speaking_thread:
            event.ignore()
            self.subtitle.setText('Closing safely after audio finishes…')
            return
        self.orb.timer.stop()
        super().closeEvent(event)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = VoiceWindow()
    window.show()
    sys.exit(app.exec())
