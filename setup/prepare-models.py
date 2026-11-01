"""Explicit complete-setup model preparation. Never record or play audio."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from urllib.request import urlopen

MODEL_RELEASE = 'https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/'
# Hashes of the tested upstream v1.0 files; validate before loading model data.
VOICE_FILES = {
    'kokoro-v1.0.onnx': 'beb0d1848dee9a49da392cc3df26958d46cfa35d321edf434f52949153f0df3a',
    'voices-v1.0.bin': 'bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d',
}


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download_verified(url, path, expected, opener=urlopen):
    path = Path(path)
    if path.is_file() and digest(path) == expected:
        print('Already prepared: ' + path.name, flush=True)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + '.partial')
    for attempt in range(3):
        try:
            print('Downloading ' + path.name + '...', flush=True)
            with opener(url, timeout=120) as response, partial.open('wb') as output:
                shutil.copyfileobj(response, output, length=1024 * 1024)
            if digest(partial) != expected:
                raise ValueError('Model download checksum mismatch: ' + path.name)
            partial.replace(path)
            return
        except Exception:
            partial.unlink(missing_ok=True)
            if attempt == 2:
                raise
            print('Download interrupted or invalid; retrying...', flush=True)


def local_models():
    with urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as response:
        data = json.load(response)
    return {item['name'] for item in data.get('models', []) if isinstance(item, dict) and isinstance(item.get('name'), str)}


def prepare_chat(root, ollama, runner=subprocess.run, model_reader=local_models):
    # Do not replace an existing shared alias or change unrelated Ollama settings.
    models = model_reader()
    if models.intersection({'artemis', 'artemis:latest'}):
        print('Using the existing Artemis chat model.', flush=True)
        return
    definition = root / 'Modelfile'
    first = definition.read_text(encoding='utf-8').splitlines()[0]
    if not first.startswith('FROM ') or not first[5:].strip():
        raise ValueError('The Artemis model definition is invalid.')
    base = first[5:].strip()
    environment = dict(os.environ, OLLAMA_HOST='http://127.0.0.1:11434')
    if base not in models and base + ':latest' not in models:
        print('Preparing the local chat model. Ollama shows download progress below.', flush=True)
        runner([str(ollama), 'pull', base], check=True, env=environment)
    runner([str(ollama), 'create', 'artemis', '-f', str(definition)], check=True, env=environment)
    if not model_reader().intersection({'artemis', 'artemis:latest'}):
        raise RuntimeError('Ollama did not report the prepared Artemis model.')


def prepare_voice(root):
    for name, expected in VOICE_FILES.items():
        download_verified(MODEL_RELEASE + name, root / 'models' / 'kokoro' / name, expected)
    from faster_whisper import WhisperModel
    print('Preparing Whisper base.en. Existing cached downloads are reused.', flush=True)
    recognizer = WhisperModel('base.en', device='cpu', compute_type='int8', local_files_only=False)
    del recognizer
    from kokoro_onnx import Kokoro
    folder = root / 'models' / 'kokoro'
    voice = Kokoro(str(folder / 'kokoro-v1.0.onnx'), str(folder / 'voices-v1.0.bin'))
    del voice
    print('Voice models loaded successfully. No recording or playback was started.', flush=True)


def prepare(root, ollama, text_only=False):
    root = Path(root).resolve(strict=True)
    marker = root / 'artemis-setup.json'
    if not marker.is_file() or json.loads(marker.read_text(encoding='utf-8')).get('state') != 'complete':
        raise ValueError('Complete application package setup before preparing models.')
    status_path = root / 'artemis-model-setup.json'
    status = {'state': 'preparing', 'voice_requested': not text_only}
    def save():
        pending = status_path.with_suffix('.json.partial')
        pending.write_text(json.dumps(status, indent=2), encoding='utf-8')
        pending.replace(status_path)
    save()
    try:
        prepare_chat(root, ollama)
        status['chat_ready'] = True
        save()
        if not text_only:
            prepare_voice(root)
            status['voice_ready'] = True
        # The desktop runtime is essential even for text-only setup.
        from windows_setup import webview_runtime
        if not webview_runtime():
            raise RuntimeError('WebView2 was not detected. Rerun setup to repair the desktop runtime.')
        status['state'] = 'complete'
        save()
        return status
    except Exception as exc:
        status.update(state='failed', error=str(exc))
        save()
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--ollama', required=True)
    parser.add_argument('--text-only', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(prepare(args.root, args.ollama, args.text_only), indent=2))
    except Exception as exc:
        print('MODEL SETUP FAILED: ' + str(exc) + '\nRerun complete setup to retry; prepared models are kept.', file=sys.stderr)
        sys.exit(1)
