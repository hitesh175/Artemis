"""Stage 3 tests do not require microphone, downloaded models, or Windows."""
import tempfile
import unittest
from pathlib import Path

from artemis.oww_custom import DEFAULT_THRESHOLD, validate_model_path


class OpenWakeWordTests(unittest.TestCase):
    def test_default_threshold(self):
        self.assertEqual(DEFAULT_THRESHOLD, 0.50)

    def test_model_must_exist(self):
        with self.assertRaisesRegex(RuntimeError, 'missing'):
            validate_model_path(Path(tempfile.gettempdir()) / 'no_such_artemis_model.onnx')

    def test_model_extension(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'wake.zip'
            p.touch()
            with self.assertRaises(ValueError):
                validate_model_path(p)

    def test_existing_onnx_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'hey_artemis.onnx'
            p.touch()
            self.assertEqual(validate_model_path(p), p)


if __name__ == '__main__':
    unittest.main()
