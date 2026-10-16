"""Minimal regression tests; use: python -m unittest discover -s tests -p test_speech_whisper.py"""
import unittest
from unittest.mock import patch
import numpy as np

from artemis import speech_whisper

class Microphone:
    def __init__(self, frames):
        self.frames = iter(frames)
    def read(self, timeout=0.3):
        return next(self.frames, None)

class Whisper:
    def __init__(self):
        self.called = False
    def transcribe(self, audio, **kwargs):
        self.called = True
        assert audio.ndim == 1 and audio.dtype == np.float32
        assert abs(audio).max() <= 1
        return [type('Segment', (), {'text': ' Open Notepad. '})()], None

class TestWhisper(unittest.TestCase):
    def test_recognizes_command(self):
        loud = np.full(1280, 1500, dtype=np.int16).tobytes()
        silence = np.zeros(1280, dtype=np.int16).tobytes()
        clock = iter(np.arange(0, 3, 0.08))
        whisper = Whisper()
        with patch.object(speech_whisper.time, 'monotonic', side_effect=lambda: next(clock, 100.0)):
            result = speech_whisper.listen_for_whisper_command(
                Microphone([silence, loud, loud] + [silence] * 20), whisper)
        self.assertEqual(result, 'Open Notepad.')
        self.assertTrue(whisper.called)

    def test_silence_is_not_transcribed(self):
        silence = np.zeros(1280, dtype=np.int16).tobytes()
        clock = iter(np.arange(0, 8, 0.08))
        whisper = Whisper()
        with patch.object(speech_whisper.time, 'monotonic', side_effect=lambda: next(clock, 100.0)):
            result = speech_whisper.listen_for_whisper_command(Microphone([silence] * 60), whisper)
        self.assertEqual(result, '')
        self.assertFalse(whisper.called)

if __name__ == '__main__':
    unittest.main()
