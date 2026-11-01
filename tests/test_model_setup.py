"""Complete-setup recovery and integrity checks without downloads or audio."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
spec = importlib.util.spec_from_file_location('prepare_models', ROOT / 'setup/prepare-models.py')
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)


class ModelSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'Modelfile').write_text('FROM example/model\nSYSTEM "Artemis"')

    def test_verified_download_and_cache_reuse(self):
        path = self.root / 'model.bin'
        payload = b'tested model data'
        expected = hashlib.sha256(payload).hexdigest()
        opener = Mock(return_value=io.BytesIO(payload))
        setup.download_verified('https://example.test/model', path, expected, opener)
        self.assertEqual(path.read_bytes(), payload)
        setup.download_verified('https://example.test/model', path, expected, opener)
        self.assertEqual(opener.call_count, 1)
        self.assertFalse(path.with_name('model.bin.partial').exists())

    def test_bad_download_never_replaces_existing_file(self):
        path = self.root / 'model.bin'
        path.write_bytes(b'keep until replacement verified')
        opener = Mock(side_effect=lambda *a, **k: io.BytesIO(b'bad'))
        with self.assertRaisesRegex(ValueError, 'checksum'):
            setup.download_verified('https://example.test/model', path, '0' * 64, opener)
        self.assertEqual(opener.call_count, 3)
        self.assertEqual(path.read_bytes(), b'keep until replacement verified')
        self.assertFalse(path.with_name('model.bin.partial').exists())

    def test_interrupted_download_retries(self):
        payload = b'complete'
        opener = Mock(side_effect=[OSError('network down'), io.BytesIO(payload)])
        path = self.root / 'model.bin'
        setup.download_verified('https://example.test/model', path, hashlib.sha256(payload).hexdigest(), opener)
        self.assertEqual(path.read_bytes(), payload)

    def test_existing_alias_is_never_overwritten(self):
        runner = Mock()
        setup.prepare_chat(self.root, 'ollama.exe', runner, lambda: {'artemis:latest'})
        runner.assert_not_called()

    def test_model_pull_create_and_local_endpoint(self):
        runner = Mock()
        reader = Mock(side_effect=[set(), {'artemis:latest'}])
        with patch.dict(setup.os.environ, {'OLLAMA_HOST': 'http://remote.invalid'}):
            setup.prepare_chat(self.root, 'ollama.exe', runner, reader)
        self.assertEqual(runner.call_args_list[0].args[0], ['ollama.exe', 'pull', 'example/model'])
        self.assertEqual(runner.call_args_list[1].args[0][1:3], ['create', 'artemis'])
        self.assertEqual(runner.call_args.kwargs['env']['OLLAMA_HOST'], 'http://127.0.0.1:11434')

    def test_cached_base_skips_pull_and_checks_created_alias(self):
        runner = Mock()
        setup.prepare_chat(self.root, 'ollama', runner, Mock(side_effect=[{'example/model:latest'}, {'artemis'}]))
        self.assertEqual(runner.call_count, 1)
        with self.assertRaisesRegex(RuntimeError, 'did not report'):
            setup.prepare_chat(self.root, 'ollama', Mock(), lambda: set())

    def test_setup_failure_and_retry_preserve_personal_data(self):
        (self.root / 'artemis-setup.json').write_text('{"state":"complete"}')
        private = self.root / 'data' / 'memory.sqlite3'
        private.parent.mkdir()
        private.write_bytes(b'personal data')
        with patch.object(setup, 'prepare_chat'), patch.object(setup, 'prepare_voice', side_effect=OSError('interrupted')):
            with self.assertRaises(OSError):
                setup.prepare(self.root, 'ollama')
        status = json.loads((self.root / 'artemis-model-setup.json').read_text())
        self.assertEqual(status['state'], 'failed')
        self.assertTrue(status['chat_ready'])
        with patch.object(setup, 'prepare_chat'), patch.object(setup, 'prepare_voice') as voice, patch('windows_setup.webview_runtime', return_value='1.2.3'):
            status = setup.prepare(self.root, 'ollama', text_only=True)
        voice.assert_not_called()
        self.assertEqual(status['state'], 'complete')
        self.assertFalse(status['voice_requested'])
        self.assertEqual(private.read_bytes(), b'personal data')

    def test_packages_required_before_any_model_work(self):
        with patch.object(setup, 'prepare_chat') as chat:
            with self.assertRaisesRegex(ValueError, 'package setup'):
                setup.prepare(self.root, 'ollama')
        chat.assert_not_called()
        self.assertFalse((self.root / 'artemis-model-setup.json').exists())

    def test_voice_success_does_not_mask_missing_desktop_runtime(self):
        (self.root / 'artemis-setup.json').write_text('{"state":"complete"}')
        with patch.object(setup, 'prepare_chat'), patch.object(setup, 'prepare_voice'), patch('windows_setup.webview_runtime', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'WebView2'):
                setup.prepare(self.root, 'ollama')
        self.assertEqual(json.loads((self.root / 'artemis-model-setup.json').read_text())['state'], 'failed')

    def test_complete_voice_setup_records_both_stages(self):
        (self.root / 'artemis-setup.json').write_text('{"state":"complete"}')
        with patch.object(setup, 'prepare_chat') as chat, patch.object(setup, 'prepare_voice') as voice, patch('windows_setup.webview_runtime', return_value='1.2.3'):
            status = setup.prepare(self.root, 'ollama')
        chat.assert_called_once()
        voice.assert_called_once_with(self.root)
        self.assertEqual(status['state'], 'complete')
        self.assertTrue(status['chat_ready'] and status['voice_ready'])
        self.assertEqual(json.loads((self.root / 'artemis-model-setup.json').read_text()), status)


if __name__ == '__main__':
    unittest.main()
