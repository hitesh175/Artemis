"""Check canonical source without starting the UI, recording, or playing audio."""
import ast
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
for path in (ROOT / 'app').rglob('*.py'):
    ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
subprocess.run([sys.executable, str(ROOT / 'tests/test_speech_cancel.py')], cwd=ROOT, check=True)
subprocess.run([sys.executable, str(ROOT / 'tests/test_performance.py')], cwd=ROOT, check=True)
for name in ('test_state.py', 'test_everyday.py', 'test_handsfree_audio.py', 'test_tool_router.py', 'test_chat_server.py', 'test_personal_memory.py', 'test_document_search.py', 'test_document_formats.py', 'test_reminders.py', 'test_daily_briefing.py', 'test_model_settings.py'):
    subprocess.run([sys.executable, str(ROOT / 'tests' / name)], cwd=ROOT, check=True)
subprocess.run(['node', '--check', str(ROOT / 'app/desktop/web/app.js')], check=True)
subprocess.run(['node', '--check', str(ROOT / 'app/desktop/web/reminders.js')], check=True)
subprocess.run(['node', '--check', str(ROOT / 'app/desktop/web/model-settings.js')], check=True)
subprocess.run(['node', '--check', str(ROOT / 'app/desktop/web/performance.js')], check=True)
subprocess.run(['node', str(ROOT / 'tests/test_chat_stream.cjs')], check=True)
subprocess.run(['node', str(ROOT / 'tests/test_reminders_ui.cjs')], check=True)
subprocess.run(['node', str(ROOT / 'tests/test_model_settings_ui.cjs')], check=True)
print('PASS: canonical Python syntax and regression checks')
