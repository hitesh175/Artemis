"""ARTEMIS Stage 6.3.3: living orb connected to mic, offline Whisper, approved commands.
Place this script alongside artemis_orb_planet_633.py in the artemis package folder.
Run from project root: .\.venv\Scripts\python.exe .\artemis\artemis_orb_voice_633.py
"""
from __future__ import annotations
import sys, time, threading
from pathlib import Path
import numpy as np
from PySide6.QtCore import Qt, QObject, QThread, Signal, Slot, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QCheckBox, QVBoxLayout, QHBoxLayout, QWidget
from artemis_orb_planet_633 import PlanetOrb, configure_gpu

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

def execute_approved(heard: str, permitted: bool) -> str:
    from artemis.commands import interpret, execute
    try:
        from artemis.streaming_command import remove_wake_phrase
        heard = remove_wake_phrase(heard).strip()
    except ImportError:
        heard = heard.strip()
    if not heard:
        return "No command detected."
    intent = interpret(heard)
    if intent.name == "unknown":
        return "I heard you, but this is not an approved command."
    if not permitted:
        return f"Preview: {intent.name.replace('_', ' ')}" + (f" — {intent.target}" if intent.target else "") + "."
    result, _ = execute(intent)
    return result

class VoiceWorker(QObject):
    level = Signal(float)
    state = Signal(str)
    success = Signal(str, str)
    failure = Signal(str)
    done = Signal()

    def __init__(self, allow_execution=False):
        super().__init__()
        self.stop = threading.Event()
        self.allow_execution = allow_execution

    @Slot()
    def run(self):
        try:
            import sounddevice as sd
            frames = []
            def callback(indata, count, info, status):
                audio = indata[:,0].copy()
                frames.append(audio)
                rms = float(np.sqrt(np.mean(audio*audio))) if len(audio) else 0.
                self.level.emit(min(1., rms * 13.))
            self.state.emit("Listening")
            begin = time.monotonic()
            # Mic opens in this background worker and closes before Whisper starts.
            with sd.InputStream(samplerate=16000, channels=1, dtype="float32",
                                blocksize=1600, callback=callback):
                while not self.stop.is_set() and time.monotonic()-begin < 20:
                    time.sleep(.04)
            if not frames:
                raise RuntimeError("Microphone returned no audio.")
            audio = np.concatenate(frames)
            duration = len(audio)/16000
            peak = float(np.max(np.abs(audio)))
            if duration < .35 or peak < .01:
                raise ValueError(f"Audio too short or quiet ({duration:.1f}s, peak {peak:.3f}).")
            self.state.emit("Thinking")
            from faster_whisper import WhisperModel
            model = WhisperModel("base.en", device="cpu", compute_type="int8",
                                 local_files_only=True)
            segments, _ = model.transcribe(audio, language="en", beam_size=5,
                vad_filter=True, condition_on_previous_text=False,
                without_timestamps=True)
            heard = " ".join(s.text.strip() for s in segments).strip()
            if not heard:
                raise ValueError("No recognizable speech. Please retry.")
            self.state.emit("Command")
            reply = execute_approved(heard, self.allow_execution)
            self.success.emit(heard, reply)
        except Exception as e:
            self.failure.emit(f"{type(e).__name__}: {e}")
        finally:
            self.done.emit()

class SpeakWorker(QObject):
    def __init__(self, reply):
        super().__init__()
        self.reply = reply
    done = Signal()
    failed = Signal(str)
    @Slot()
    def run(self):
        try:
            from artemis.voice import Speaker
            Speaker(enabled=True).say(self.reply)
        except Exception as e:
            self.failed.emit(f"Speech unavailable: {e}")
        finally:
            self.done.emit()

class VoiceWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ARTEMIS — Living Planet Voice Mode")
        self.resize(840, 720)
        self.setMinimumSize(600, 570)
        self.setStyleSheet("""
          QWidget { background:#0E1119; color:#E2E6EF; font-family:'Segoe UI'; }
          QLabel#title { color:#93A2B8; font-size:15px; font-weight:bold; }
          QLabel#state { color:#E1E9F0; font-size:25px; font-weight:600; }
          QLabel#text { color:#A9B4C7; font-size:14px; }
          QPushButton { background:#253246; border:1px solid #3D4C65;
               border-radius:18px; padding:12px 20px; font-size:14px; }
          QPushButton:hover { background:#354962; }
          QPushButton:disabled { color:#798396; background:#1B2533; }
          QCheckBox { color:#A9B4C7; padding:7px; }
        """)
        layout=QVBoxLayout(self)
        layout.setContentsMargins(32,22,32,24)
        title=QLabel("A R T E M I S", objectName="title")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        self.orb=PlanetOrb()
        layout.addWidget(self.orb, 1)
        self.label=QLabel("Idle", objectName="state")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        self.subtitle=QLabel("Click Start listening, then speak and click Stop.", objectName="text")
        self.subtitle.setAlignment(Qt.AlignCenter)
        self.subtitle.setWordWrap(True)
        self.subtitle.setMinimumHeight(42)
        layout.addWidget(self.subtitle)
        flags=QHBoxLayout()
        self.allow=QCheckBox("Allow approved commands")
        self.speak_box=QCheckBox("Speak responses")
        flags.addStretch()
        flags.addWidget(self.allow)
        flags.addWidget(self.speak_box)
        flags.addStretch()
        layout.addLayout(flags)
        buttons=QHBoxLayout()
        self.button=QPushButton("🎙  Start listening")
        self.button.clicked.connect(self.toggle)
        buttons.addStretch()
        buttons.addWidget(self.button)
        buttons.addStretch()
        layout.addLayout(buttons)
        self.worker_thread=None
        self.worker=None
        self.speech_thread=None
        self.speech_worker=None
        self.recording=False
        self.busy=False

    def state(self, name):
        self.orb.set_state(name)
        self.label.setText(name)

    def toggle(self):
        if self.recording:
            self.worker.stop.set()
            self.recording=False
            self.button.setEnabled(False)
            self.button.setText("Processing…")
            self.state("Thinking")
            return
        if self.busy:
            return
        self.busy=True
        self.recording=True
        self.allow.setEnabled(False)
        self.speak_box.setEnabled(False)
        self.button.setText("■  Stop listening")
        self.subtitle.setText("Listening… speak naturally.")
        self.thread=QThread(self)
        self.worker_thread=self.thread
        self.worker=VoiceWorker(self.allow.isChecked())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.level.connect(self.orb.set_audio_level)
        self.worker.state.connect(self.state)
        self.worker.success.connect(self.on_success)
        self.worker.failure.connect(self.on_failure)
        self.worker.done.connect(self.thread.quit)
        self.worker.done.connect(self.worker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.recording_finished)
        self.thread.start()

    @Slot(str,str)
    def on_success(self, heard, reply):
        self.subtitle.setText(f"You: {heard}\nArtemis: {reply}")
        if self.speak_box.isChecked():
            self.begin_speak(reply)
        else:
            self.state("Idle")

    @Slot(str)
    def on_failure(self, message):
        self.state("Error")
        self.subtitle.setText(message)
        QTimer.singleShot(2600, self.restore_idle_if_error)

    def restore_idle_if_error(self):
        if not self.busy and self.label.text()=="Error":
            self.state("Idle")

    def begin_speak(self, reply):
        self.state("Speaking")
        self.speech_thread=QThread(self)
        self.speech_worker=SpeakWorker(reply)
        self.speech_worker.moveToThread(self.speech_thread)
        self.speech_thread.started.connect(self.speech_worker.run)
        self.speech_worker.failed.connect(self.on_failure)
        self.speech_worker.done.connect(self.speech_thread.quit)
        self.speech_worker.done.connect(self.speech_worker.deleteLater)
        self.speech_thread.finished.connect(self.speech_thread.deleteLater)
        self.speech_thread.finished.connect(self.speech_finished)
        self.speech_thread.start()

    def speech_finished(self):
        self.speech_thread=None
        self.speech_worker=None
        if self.label.text()=="Speaking":
            self.state("Idle")

    @Slot()
    def recording_finished(self):
        self.recording=False
        self.busy=False
        self.worker_thread=None
        self.worker=None
        self.button.setEnabled(True)
        self.button.setText("🎙  Start listening")
        self.allow.setEnabled(True)
        self.speak_box.setEnabled(True)

    def closeEvent(self, event):
        if self.recording and self.worker:
            self.worker.stop.set()
        if self.worker_thread and self.worker_thread.isRunning():
            event.ignore()
            self.subtitle.setText("Finishing voice capture before closing…")
            return
        if self.speech_thread and self.speech_thread.isRunning():
            event.ignore()
            self.subtitle.setText("Finishing spoken response before closing…")
            return
        super().closeEvent(event)

if __name__=="__main__":
    configure_gpu()
    app=QApplication(sys.argv)
    w=VoiceWindow()
    w.show()
    sys.exit(app.exec())
