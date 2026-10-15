import unittest
from unittest.mock import patch

from artemis.commands import Intent, execute, interpret


class CommandTests(unittest.TestCase):
    def test_supported_app(self):
        self.assertEqual(interpret("Please open Notepad"), Intent("open_app", "notepad"))

    def test_supported_folder(self):
        self.assertEqual(interpret("open my downloads folder"), Intent("open_folder", "Downloads"))

    def test_vscode(self):
        self.assertEqual(interpret("launch visual studio code"), Intent("open_app", "vscode"))

    def test_time(self):
        self.assertEqual(interpret("what time is it"), Intent("time"))

    def test_exit(self):
        self.assertEqual(interpret("stop assistant"), Intent("exit"))

    def test_no_arbitrary_commands(self):
        for spoken in [
            "delete all my files",
            "open notepad and delete documents",
            "run powershell remove item",
            "open cmd",
            "don't open notepad",
            "open c users secret",
        ]:
            with self.subTest(spoken=spoken):
                self.assertEqual(interpret(spoken).name, "unknown")

    def test_unknown_does_not_launch_anything(self):
        with patch("artemis.commands.subprocess.Popen") as popen:
            answer, quitting = execute(interpret("delete my downloads"))
            self.assertIn("approved command", answer)
            self.assertFalse(quitting)
            popen.assert_not_called()

    def test_notepad_approved_launch(self):
        with patch("artemis.commands.subprocess.Popen") as popen:
            answer, quitting = execute(Intent("open_app", "notepad"))
            popen.assert_called_once_with(["notepad.exe"], shell=False)
            self.assertFalse(quitting)
            self.assertIn("Opening", answer)

    def test_forged_intent_fails_closed(self):
        with patch("artemis.commands.subprocess.Popen") as popen:
            answer, quitting = execute(Intent("open_app", "powershell"))
            self.assertIn("approved", answer)
            popen.assert_not_called()


if __name__ == "__main__":
    unittest.main()
