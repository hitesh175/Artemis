"""ARTEMIS 6.4: auto-endpoint, hands-free session on existing matte planet.
Keeps approved-command allowlist, offline Whisper, and existing voice output.
No wake-word activation; Start Conversation is an explicit privacy control.
"""
from __future__ import annotations
import sys, time, threading, collections, re
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import (QApplication, QLabel, QPushButton, QCheckBox,
                               QVBoxLayout, QHBoxLayout, QWidget)
from artemis_orb_planet_634 import PlanetOrb

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))



def normalize_voice_command(text):
    """Correct only known, exact application-command mishearings."""
    normalized = re.sub(r"[.!?,]+$", "", text.casefold().strip())
    corrections = {
        "open not bad": "open notepad",
        "open note pad": "open notepad",
        "open not pet": "open notepad",
        "open not paid": "open notepad",
    }
    return corrections.get(normalized, text)

def approved_command(text, permitted):
    from artemis.commands import interpret, execute
    from artemis.streaming_command import remove_wake_phrase
    text = normalize_voice_command(remove_wake_phrase(text).strip())
    if not text:
        return 'No command detected.'
    intent = interpret(text)
    if intent.name == 'unknown':
        return 'I heard you, but this is not an approved command.'
    if not permitted:
        suffix = f' — {intent.target}' if intent.target else ''
        return f'Preview: {intent.name.replace("_", " ")}{suffix}.'
    result, _ = execute(intent)
    return result


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

    def __init__(self, permitted):
        super().__init__()
        self.stop = threading.Event()
        self.permitted = permitted

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
            threshold = .012
            begin = time.monotonic()
            with sd.InputStream(samplerate=rate, channels=1, dtype='float32',
                                blocksize=block, callback=cb):
                while not self.stop.is_set():
                    try:
                        data = q.get(timeout=.2)
                    except queue.Empty:
                        continue
                    rms = float(np.sqrt(np.mean(data * data)))
                    peak = float(np.max(np.abs(data)))
                    self.level.emit(min(1.0, rms*15.0))
                    if time.monotonic()-begin < .7:
                        ambient.append(rms)
                        pre.append(data)
                        continue
                    if not started:
                        if ambient:
                            threshold = max(.012, min(.085, float(np.median(ambient))*3.5))
                        if rms > threshold and peak > .018:
                            active_blocks += 1
                        else:
                            active_blocks = 0
                        if active_blocks >= 2:  # 200 ms confirms onset
                            started = True
                            captured.extend(pre)
                            captured.append(data)
                            self.status.emit('Hearing you… pause to finish')
                        else:
                            pre.append(data)
                    else:
                        captured.append(data)
                        quiet_blocks = quiet_blocks + 1 if rms < threshold*.8 else 0
                        if quiet_blocks >= 11:  # 1.1 seconds quiet
                            break
                        if len(captured) * block / rate >= 14:
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
            from faster_whisper import WhisperModel
            model = WhisperModel('base.en', device='cpu', compute_type='int8',
                                 local_files_only=True)
            parts, _ = model.transcribe(audio, language='en', beam_size=5,
                vad_filter=True, condition_on_previous_text=False,
                without_timestamps=True,
                initial_prompt='Windows voice commands: Open Notepad. Open Calculator. Help.')
            heard = ' '.join(part.text.strip() for part in parts).strip()
            if self.stop.is_set():
                self.cancelled.emit()
                return
            if not heard:
                self.cancelled.emit()
                return
            self.state.emit('Command')
            reply = approved_command(heard, self.permitted)
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
            from artemis.voice import Speaker
            Speaker(enabled=True).say(self.reply)
        except Exception as exc:
            self.failed.emit(f'Speech unavailable: {exc}')
        finally:
            self.finished.emit()


class VoiceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ARTEMIS — Hands-free Planet Voice Mode')
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
        checks.addStretch(); checks.addWidget(self.permitted)
        checks.addWidget(self.tts); checks.addStretch()
        outer.addLayout(checks)
        control = QHBoxLayout()
        self.button = QPushButton('🎙  Start conversation')
        self.button.clicked.connect(self.toggle_session)
        control.addStretch(); control.addWidget(self.button); control.addStretch()
        outer.addLayout(control)
        hint = QLabel('No wake-word needed • audio stays in memory • Stop conversation to mute', objectName='text')
        hint.setAlignment(Qt.AlignCenter)
        outer.addWidget(hint)
        self.session = False
        self.listening_thread = None
        self.listening_worker = None
        self.speaking_thread = None
        self.speaking_worker = None
        self.pending_reply = None
        self.closing_requested = False
        self.rearm = QTimer(self)
        self.rearm.setSingleShot(True)
        self.rearm.timeout.connect(self.arm_listening)

    def show_state(self, value):
        self.orb.set_state(value)
        self.activity.setText(value)

    def toggle_session(self):
        if self.session:
            self.end_session()
        else:
            self.session = True
            self.permitted.setEnabled(False)
            self.button.setText('■  Stop conversation')
            self.arm_listening()

    def end_session(self):
        self.session = False
        self.rearm.stop()
        self.button.setText('🎙  Start conversation')
        if self.listening_worker:
            self.listening_worker.stop.set()
        self.subtitle.setText('Conversation stopped. Microphone will close.')
        self.show_state('Sleep')
        if self.listening_thread is None and self.speaking_thread is None:
            self.permitted.setEnabled(True)

    def arm_listening(self):
        if not self.session or self.listening_thread or self.speaking_thread or self.closing_requested:
            return
        self.show_state('Listening')
        self.subtitle.setText('Listening… speak, then pause naturally.')
        th = QThread(self)
        wk = ListenWorker(self.permitted.isChecked())
        wk.moveToThread(th)
        self.listening_thread = th
        self.listening_worker = wk
        th.started.connect(wk.run)
        wk.level.connect(self.orb.set_audio_level)
        wk.state.connect(self.show_state)
        wk.status.connect(self.subtitle.setText)
        wk.result.connect(self.on_result)
        wk.failed.connect(self.on_error)
        wk.cancelled.connect(self.on_cancelled)
        wk.finished.connect(th.quit)
        wk.finished.connect(wk.deleteLater)
        th.finished.connect(th.deleteLater)
        th.finished.connect(self.on_listening_finished)
        th.start()

    @Slot(str,str)
    def on_result(self, heard, reply):
        self.subtitle.setText(f'You: {heard}\nArtemis: {reply}')
        # IMPORTANT: wait until microphone stream has closed before beginning TTS.
        self.pending_reply = reply if (self.session and self.tts.isChecked()) else None
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
        self.show_state('Speaking')
        th = QThread(self)
        wk = TalkWorker(reply)
        wk.moveToThread(th)
        self.speaking_thread = th
        self.speaking_worker = wk
        th.started.connect(wk.run)
        wk.failed.connect(self.on_error)
        wk.finished.connect(th.quit)
        wk.finished.connect(wk.deleteLater)
        th.finished.connect(th.deleteLater)
        th.finished.connect(self.on_speaking_finished)
        th.start()

    @Slot()
    def on_speaking_finished(self):
        self.speaking_thread = None
        self.speaking_worker = None
        if self.closing_requested:
            self.close()
            return
        if self.session:
            self.show_state('Idle')
            self.rearm.start(550)  # pause before mic resumes; avoids feedback
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
