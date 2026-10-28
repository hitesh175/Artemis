"""Launch the existing desktop with single-instance protection and local crash logs."""
import faulthandler
import msvcrt
from pathlib import Path
import runpy
import sys
import traceback
from datetime import datetime

root = Path(__file__).resolve().parent
logs = root / 'logs'
logs.mkdir(exist_ok=True)
lock = (logs / 'desktop.lock').open('a+b')
lock.seek(0)
if not lock.read(1):
    lock.write(b'0')
    lock.flush()
lock.seek(0)
try:
    msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
except OSError:
    print('Artemis is already running. Close its existing window before starting again.')
    sys.exit(2)

log_path = logs / ('desktop-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '.log')
print('Artemis diagnostics:', log_path, flush=True)
with log_path.open('w', encoding='utf-8', buffering=1) as log:
    sys.stdout = log
    sys.stderr = log
    faulthandler.enable(log, all_threads=True)
    print('Started:', datetime.now().isoformat(), flush=True)
    sys.path.insert(0, str(root / 'desktop'))
    try:
        runpy.run_path(str(root / 'desktop' / 'main.py'), run_name='__main__')
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        raise SystemExit(1)
    finally:
        print('Stopped:', datetime.now().isoformat(), flush=True)
        faulthandler.disable()
        sys.stdout = sys.__stdout__
        sys.stderr = sys.__stderr__
