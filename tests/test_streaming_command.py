import unittest
import numpy as np
from artemis.streaming_command import RecentAudio, remove_wake_phrase
from artemis.commands import interpret

class Stage5Tests(unittest.TestCase):
    def test_cleanup(self):
        for utterance in ('Hey Artemis, open Notepad.', 'Artemis open Notepad', 'hey, artemis! open Notepad'):
            self.assertEqual(remove_wake_phrase(utterance).lower(), 'open notepad.') if utterance.endswith('.') else self.assertEqual(remove_wake_phrase(utterance).lower(), 'open notepad')
    def test_command_is_not_rewritten(self):
        self.assertEqual(interpret(remove_wake_phrase('Hey Artemis, open Notepad.')).name, 'open_app')
        self.assertEqual(interpret(remove_wake_phrase('Hey Artemis, delete everything')).name, 'unknown')
    def test_buffer(self):
        audio=RecentAudio(seconds=.16)
        audio.append(np.ones(1280,dtype=np.int16).tobytes())
        audio.append(np.ones(1280,dtype=np.int16).tobytes())
        audio.append(np.ones(1280,dtype=np.int16).tobytes())
        self.assertLessEqual(len(audio.snapshot()),2)
if __name__=='__main__': unittest.main()
