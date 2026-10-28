"""Build a repeatable source distribution; no private state or model weights."""
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]

def build():
    files = [p for p in (ROOT / 'app').rglob('*') if p.is_file()
             and not any(x in p.relative_to(ROOT / 'app').parts for x in
                         ('__pycache__', '.venv', 'data', 'logs', 'models', 'voice_test'))
             and p.suffix != '.pyc']
    files += [ROOT / p for p in ('README.md', 'requirements.txt',
                                 'requirements-baseline.lock', 'SOURCE-BASELINE.json')]
    files += [p for p in (ROOT / 'scripts').glob('*.py')]
    files += [p for p in (ROOT / 'tests').glob('*.py')]
    hashes = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(files)}
    output = ROOT / 'output' / 'releases' / 'artemis-source.zip'
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(hashes):
            info = zipfile.ZipInfo(name, date_time=(2026, 10, 28, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, (ROOT / name).read_bytes())
        info = zipfile.ZipInfo('MANIFEST.json', date_time=(2026, 10, 28, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o100644 << 16
        archive.writestr(info, json.dumps(hashes, indent=2, sort_keys=True))
    print(output)
    return output

if __name__ == '__main__':
    build()
