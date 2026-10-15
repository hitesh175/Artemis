"""One-time download and keyword setup for fully local 'HEY ARTEMIS' spotting.

Runtime makes no network requests. Model is downloaded from official sherpa-onnx
releases and can be removed if unwanted.
"""
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import urllib.request

from artemis.kws import KWS_FOLDER

MODEL_NAME = 'sherpa-onnx-kws-zipformer-gigaspeech-3.3M-2024-01-01'
MODEL_URL = (
    'https://github.com/k2-fsa/sherpa-onnx/releases/download/kws-models/'
    + MODEL_NAME + '.tar.bz2'
)


def _extract_safely(archive, destination):
    root = destination.resolve()
    with tarfile.open(archive, mode='r:bz2') as tar:
        members = tar.getmembers()
        for member in members:
            target = (destination / member.name).resolve()
            if not target.is_relative_to(root) or not member.isfile() and not member.isdir():
                raise RuntimeError('Unsafe archive entry: ' + member.name)
        tar.extractall(destination, members=members)


def main():
    parent = KWS_FOLDER.parent
    parent.mkdir(parents=True, exist_ok=True)
    token_path = KWS_FOLDER / 'tokens.txt'
    if not token_path.is_file():
        archive = parent / (MODEL_NAME + '.tar.bz2')
        print('Downloading English keyword spotter from official sherpa-onnx releases...')
        urllib.request.urlretrieve(MODEL_URL, archive)
        try:
            _extract_safely(archive, parent)
        finally:
            archive.unlink(missing_ok=True)

    if not token_path.is_file():
        raise RuntimeError('Model extraction failed: expected tokens.txt was not found')

    raw = KWS_FOLDER / 'artemis_keywords_raw.txt'
    keywords = KWS_FOLDER / 'artemis_keywords.txt'
    raw.write_text('HEY ARTEMIS\n', encoding='utf-8')
    cli = shutil.which('sherpa-onnx-cli')
    if not cli:
        exe = Path(sys.executable).parent / ('sherpa-onnx-cli.exe' if sys.platform == 'win32' else 'sherpa-onnx-cli')
        if exe.is_file():
            cli = str(exe)
    if not cli:
        raise RuntimeError(
            'sherpa-onnx-cli not found. Install package using '
            '.venv\\Scripts\\python.exe -m pip install sherpa-onnx'
        )
    print('Building the HEY ARTEMIS keyword vocabulary locally...')
    subprocess.run([
        cli, 'text2token', '--tokens', str(KWS_FOLDER / 'tokens.txt'),
        '--tokens-type', 'bpe', '--bpe-model', str(KWS_FOLDER / 'bpe.model'),
        str(raw), str(keywords),
    ], check=True)
    if not keywords.is_file() or not keywords.read_text(encoding='utf-8').strip():
        raise RuntimeError('Keyword generation failed: keywords file is empty')
    print('Keyword setup complete:', keywords)
    print('Try: .venv\\Scripts\\python.exe main.py --wake-test')


if __name__ == '__main__':
    main()
