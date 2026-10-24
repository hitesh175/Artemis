@echo off
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" desktop\main.py --browser
) else (
  python desktop\main.py --browser
)
pause
