"""Pure tests: require no microphone, Vosk installation, or model downloads."""
import unittest
from artemis.wakeword import get_command_after_wake, normalize


class WakePhraseTests(unittest.TestCase):
    def test_exact_phrase(self):
        self.assertEqual(get_command_after_wake("Hey Artemis"), "")

    def test_command_in_same_utterance(self):
        self.assertEqual(get_command_after_wake("Hey Artemis, open Notepad!"), "open notepad")

    def test_punctuation(self):
        self.assertEqual(get_command_after_wake("HEY... ARTEMIS!"), "")

    def test_no_wake(self):
        self.assertIsNone(get_command_after_wake("please open notepad"))

    def test_prefix_is_not_enough(self):
        self.assertIsNone(get_command_after_wake("hey artemisian open notepad"))

    def test_wake_does_not_trigger_mid_conversation(self):
        self.assertIsNone(get_command_after_wake("my friend said hey artemis"))

    def test_compound_command_tail_stays_whole(self):
        from artemis.commands import interpret
        command = get_command_after_wake("Hey Artemis open notepad and delete everything")
        self.assertEqual(interpret(command).name, "unknown")

    def test_reject_short_soundalikes(self):
        self.assertIsNone(get_command_after_wake("hey art"))

    def test_normalizes_spaces(self):
        self.assertEqual(normalize("  HEY,    Artemis "), "hey artemis")


if __name__ == "__main__":
    unittest.main()
