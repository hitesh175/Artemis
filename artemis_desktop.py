"""ARTEMIS Stage 6 desktop companion. Offline GUI for existing commands/Whisper."""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QApplication, QCheckBox, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QMainWindow, QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget)

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def process_command(raw: str, execute_enabled: bool):
    from artemis.commands import interpret, execute
    from artemis.streaming_command import remove_wake_phrase
    cleaned = remove_wake_phrase(raw).strip()
    if not cleaned:
        return 'I did not hear a command.'
    intent = interpret(cleaned)
    if not execute_enabled:
        if intent.name == 'unknown':
            return 'Preview: This is not an approved command. Try “open Notepad” or “help”.'
        return f'Preview: Recognized {intent.name.replace("_", " ")}' + (f' — {intent.target}' if intent.target else '') + '. Enable execution to run it.'
    reply, _ = execute(intent)
    return reply


class RecordWorker(QObject):
    status = Signal(str)
    recorded = Signal(object, str)
    done = Signal(str, str)
    failed = Signal(str)
    finished = Signal()

    def __init__(self, execute_enabled: bool, device=None, model_name='base.en'):
        super().__init__()
        self.execute_enabled = execute_enabled
        self.device = device
        self.model_name = model_name
        self.stop_event = threading.Event()

    @Slot()
    def run(self):
        try:
            from artemis_audio_capture import MicCapture, metrics, transcribe
            self.status.emit('● Recording… speak naturally, then click Stop')
            with MicCapture(device=self.device) as capture:
                started = time.monotonic()
                while not self.stop_event.is_set() and time.monotonic() - started < 15:
                    time.sleep(0.03)
            audio, notices = capture.result()
            if not len(audio):
                self.failed.emit('No microphone audio received. Check Windows microphone permissions.')
                return
            seconds, peak, rms = metrics(audio)
            report = f'{seconds:.1f}s • peak {peak:.4f} • RMS {rms:.4f}'
            if notices:
                report += ' • Stream notices: ' + '; '.join(notices[:2])
            self.recorded.emit(audio, report)
            self.status.emit('● Transcribing offline…')
            if seconds < 0.45:
                self.failed.emit('Recording too short. Speak a complete command before stopping.')
                return
            if peak < 0.01 or rms < 0.001:
                self.failed.emit('Microphone audio is extremely quiet. Check Windows Sound → Input.')
                return
            if peak >= 0.99:
                self.status.emit('● Microphone clipping — consider lowering Windows input gain')
            heard = transcribe(audio, self.model_name)
            if not heard:
                self.failed.emit('Whisper detected no speech. Play the last recording to check the capture.')
                return
            # The existing approved-command interpreter is the only execution gate.
            reply = process_command(heard, self.execute_enabled)
            self.done.emit(heard, reply)
        except Exception as exc:
            self.failed.emit(f'{type(exc).__name__}: {exc}')
        finally:
            self.finished.emit()


STYLE = '''
QMainWindow, QWidget#root { background: #0D1019; color: #ECF0FC; }
QLabel { color: #E9EDFA; background: transparent; }
QFrame#sidebar { background: #151A28; border-right: 1px solid #293247; }
QFrame#topbar { background: #101522; border-bottom: 1px solid #293247; }
QLabel#brand { font-size: 23px; font-weight: 800; color: #EAF1FF; }
QLabel#subtle { color: #94A3BC; font-size: 12px; }
QLabel#heading { font-size: 18px; font-weight: 650; }
QLabel#userMsg { color: #FAFBFF; background: #304174; border-radius: 14px; padding: 12px 15px; }
QLabel#botMsg { color: #EAF0FF; background: #1B2438; border-radius: 14px; padding: 12px 15px; }
QLineEdit { background: #1A2334; border: 1px solid #32415D; border-radius: 10px; padding: 12px 14px; color: white; font-size: 14px; }
QLineEdit:focus { border-color: #708BFF; }
QPushButton { background: #465FD3; color: white; border: 0; border-radius: 10px; padding: 11px 16px; font-weight: 650; }
QPushButton:hover { background: #5C76EF; }
QPushButton:disabled { background: #2C3446; color: #8190AB; }
QPushButton#secondary { background: #232D44; }
QPushButton#secondary:hover { background: #33415F; }
QCheckBox { color: #DCE3F6; spacing: 8px; }
QScrollArea { border: 0; background: transparent; }
QScrollBar:vertical { background: #111726; width: 8px; }
QScrollBar::handle:vertical { background: #3A4A68; border-radius: 4px; }
'''


class ArtemisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('ARTEMIS — Offline Desktop Assistant')
        self.resize(1050, 690)
        self.setMinimumSize(760, 530)
        self._thread = None
        self._worker = None
        self._recording = False
        self._last_audio = None
        self._playing = False
        self.setStyleSheet(STYLE)
        self.playback_finished.connect(self.playback_done)

        root = QWidget(objectName='root')
        self.setCentralWidget(root)
        horizontal = QHBoxLayout(root)
        horizontal.setContentsMargins(0, 0, 0, 0)
        horizontal.setSpacing(0)

        sidebar = QFrame(objectName='sidebar')
        sidebar.setFixedWidth(240)
        sl = QVBoxLayout(sidebar)
        sl.setContentsMargins(22, 28, 22, 22)
        sl.setSpacing(14)
        sl.addWidget(QLabel('✦  ARTEMIS', objectName='brand'))
        sl.addWidget(QLabel('PRIVATE · OFFLINE', objectName='subtle'))
        sl.addSpacing(25)
        sl.addWidget(QLabel('CONTROLS', objectName='subtle'))
        self.execute_box = QCheckBox('Allow approved commands')
        self.execute_box.setChecked(False)
        sl.addWidget(self.execute_box)
        sl.addWidget(QLabel('Off = preview only', objectName='subtle'))
        sl.addSpacing(10)
        self.voice_box = QCheckBox('Speak responses')
        self.voice_box.setChecked(False)
        sl.addWidget(self.voice_box)
        sl.addWidget(QLabel('Uses installed Windows / Piper voice', objectName='subtle'))
        sl.addStretch()
        clear = QPushButton('Clear chat', objectName='secondary')
        clear.clicked.connect(self.clear_chat)
        sl.addWidget(clear)
        sl.addWidget(QLabel('Stage 6  •  Wake-free voice mode', objectName='subtle'))
        horizontal.addWidget(sidebar)

        main = QWidget()
        ml = QVBoxLayout(main)
        ml.setContentsMargins(0, 0, 0, 0)
        ml.setSpacing(0)
        bar = QFrame(objectName='topbar')
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(22, 16, 22, 16)
        bl.addWidget(QLabel('Assistant', objectName='heading'))
        bl.addStretch()
        self.status = QLabel('● Ready — local mode', objectName='subtle')
        bl.addWidget(self.status)
        ml.addWidget(bar)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(25, 25, 25, 25)
        self.chat_layout.setSpacing(14)
        self.chat_layout.addStretch(1)
        self.scroll.setWidget(self.chat_widget)
        ml.addWidget(self.scroll, 1)

        bottom = QWidget()
        bt = QVBoxLayout(bottom)
        bt.setContentsMargins(24, 12, 24, 23)
        self.tip = QLabel('Mic: click Start, speak, then Stop. Play last recording to inspect. Audio stays in RAM.', objectName='subtle')
        bt.addWidget(self.tip)
        tools = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText('Type an approved command, e.g. open Notepad')
        self.input.returnPressed.connect(self.send_text)
        tools.addWidget(self.input, 1)
        send = QPushButton('Send')
        send.clicked.connect(self.send_text)
        tools.addWidget(send)
        self.mic = QPushButton('🎙  Start recording', objectName='secondary')
        self.mic.clicked.connect(self.toggle_recording)
        tools.addWidget(self.mic)
        self.play_button = QPushButton('▶ Play last recording', objectName='secondary')
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self.play_last_recording)
        tools.addWidget(self.play_button)
        bt.addLayout(tools)
        self.audio_info = QLabel('Audio capture: no recording yet', objectName='subtle')
        bt.addWidget(self.audio_info)
        ml.addWidget(bottom)
        horizontal.addWidget(main, 1)
        self.add_message('ARTEMIS', 'Hello. You can type a command or record with the microphone. Preview mode is on by default.')

    def add_message(self, who, message):
        line = QHBoxLayout()
        bubble = QLabel(message, objectName='userMsg' if who == 'You' else 'botMsg')
        bubble.setWordWrap(True)
        bubble.setTextInteractionFlags(Qt.TextSelectableByMouse)
        bubble.setMaximumWidth(570)
        line.addStretch(1) if who == 'You' else None
        line.addWidget(bubble)
        line.addStretch(1) if who != 'You' else None
        self.chat_layout.insertLayout(self.chat_layout.count()-1, line)
        from PySide6.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum()))

    def clear_chat(self):
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            layout = item.layout()
            if layout:
                while layout.count():
                    child = layout.takeAt(0)
                    if child.widget(): child.widget().deleteLater()
                layout.deleteLater()
        self.add_message('ARTEMIS', 'Chat cleared. No conversation was saved to disk.')

    def send_text(self):
        text = self.input.text().strip()
        if not text: return
        self.input.clear()
        self.add_message('You', text)
        try:
            reply = process_command(text, self.execute_box.isChecked())
        except Exception as exc:
            reply = f'Command error: {type(exc).__name__}: {exc}'
        self.add_message('ARTEMIS', reply)
        self.speak(reply)

    def speak(self, reply):
        if not self.voice_box.isChecked(): return
        # Voice can be slow; do not block the GUI thread.
        def job():
            try:
                from artemis.voice import Speaker
                Speaker(enabled=True).say(reply)
            except Exception as exc:
                print('Speech unavailable:', exc)
        threading.Thread(target=job, daemon=True).start()

    def toggle_recording(self):
        if self._recording:
            if self._worker: self._worker.stop_event.set()
            self._recording = False
            self.mic.setEnabled(False)
            self.status.setText('● Processing voice…')
            return
        if self._thread is not None: return
        self._recording = True
        self.play_button.setEnabled(False)
        self._last_audio = None
        self.audio_info.setText('Audio capture: recording…')
        self.execute_box.setEnabled(False)
        self.mic.setText('■  Stop recording')
        self.status.setText('● Recording…')
        self._thread = QThread(self)
        self._worker = RecordWorker(execute_enabled=self.execute_box.isChecked())
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.status.connect(self.status.setText)
        self._worker.recorded.connect(self.audio_recorded)
        self._worker.done.connect(self.voice_done)
        self._worker.failed.connect(self.voice_error)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.finished.connect(self.reset_voice)
        self._thread.start()

    @Slot(object, str)
    def audio_recorded(self, audio, report):
        self._last_audio = audio
        self.audio_info.setText('Last recording: ' + report)
        self.play_button.setEnabled(not self._recording and not self._playing)

    def play_last_recording(self):
        if self._last_audio is None or self._recording or self._playing:
            return
        self._playing = True
        self.play_button.setEnabled(False)
        audio = self._last_audio.copy()
        self.status.setText('● Playing microphone recording…')
        # Play through sounddevice using the same sample rate as capture.
        # Keep playback off the Qt UI thread.
        def playback():
            try:
                import sounddevice as sd
                from artemis_audio_capture import RATE
                sd.play(audio, samplerate=RATE, blocking=True)
            except Exception as exc:
                print('Audio playback failed:', type(exc).__name__, exc)
            finally:
                self.playback_finished.emit()
        threading.Thread(target=playback, daemon=True).start()

    playback_finished = Signal()

    @Slot()
    def playback_done(self):
        self._playing = False
        self.play_button.setEnabled(self._last_audio is not None and not self._recording)
        self.status.setText('● Ready — local mode')

    @Slot(str, str)
    def voice_done(self, heard, reply):
        self.add_message('You', heard)
        self.add_message('ARTEMIS', reply)
        self.speak(reply)

    @Slot(str)
    def voice_error(self, error):
        self.add_message('ARTEMIS', error)

    @Slot()
    def reset_voice(self):
        self._thread = None
        self._worker = None
        self._recording = False
        self.execute_box.setEnabled(True)
        self.mic.setEnabled(True)
        self.mic.setText('🎙  Start recording')
        self.play_button.setEnabled(self._last_audio is not None and not self._playing)
        self.status.setText('● Ready — local mode')

    def closeEvent(self, event):
        if self._thread is not None:
            if self._worker: self._worker.stop_event.set()
            self._thread.quit()
            self._thread.wait(20000)
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont('Segoe UI', 10))
    window = ArtemisWindow()
    window.show()
    return app.exec()


if __name__ == '__main__':
    raise SystemExit(main())
