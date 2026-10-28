"""Console-free entry point for the Artemis Desktop/Start menu shortcut."""
from pathlib import Path
import os
import runpy
import sys
root=Path(__file__).resolve().parent
os.chdir(root)
try:
    runpy.run_path(str(root/'run_logged.py'),run_name='__main__')
except SystemExit as exc:
    if exc.code not in (None,0):
        import ctypes
        message = ('Artemis is already running. Switch to its existing window.' if exc.code==2
                   else 'Artemis could not start. See the latest file in the logs folder for details.')
        ctypes.windll.user32.MessageBoxW(None,message,'Artemis',0)
except Exception:
    import traceback,ctypes
    try:
        (root/'logs').mkdir(exist_ok=True)
        (root/'logs'/'launcher-error.log').write_text(traceback.format_exc(),encoding='utf-8')
    finally:
        ctypes.windll.user32.MessageBoxW(None,'Artemis could not start. See logs/launcher-error.log.','Artemis',0)
