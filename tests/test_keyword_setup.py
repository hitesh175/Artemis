"""Unit tests for keyword runtime validation, without audio or a model download."""
import tempfile
import unittest
from pathlib import Path

from artemis.kws import paths
from artemis.wakeword import get_command_after_wake


class KeywordSetupTests(unittest.TestCase):
    def test_model_filename_structure(self):
        with tempfile.TemporaryDirectory() as temp:
            required = paths(temp)
            self.assertEqual(set(required), {'tokens','encoder','decoder','joiner','keywords_file'})
            self.assertTrue(required['keywords_file'].endswith('artemis_keywords.txt'))
            self.assertTrue(required['encoder'].endswith('.int8.onnx'))
    def test_legacy_phrase_matching_still_works(self):
        self.assertEqual(get_command_after_wake('Hey Artemis open Notepad'), 'open notepad')


if __name__ == '__main__':
    unittest.main()
