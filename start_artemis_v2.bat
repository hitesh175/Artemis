@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Missing Artemis Python environment.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -u run_logged.py
if errorlevel 1 (
  echo Artemis stopped or could not start. Details are in the logs folder above.
  pause
)
