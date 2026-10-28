"""Check canonical source without starting the UI, recording, or playing audio."""
import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'app').rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
for name in ('test_state.py', 'test_everyday.py', 'test_handsfree_audio.py'):
    subprocess.run([sys.executable, str(ROOT / 'tests' / name)], cwd=ROOT, check=True)
print('PASS: canonical Python syntax and regression checks')
