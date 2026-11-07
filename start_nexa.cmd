@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run python setup_nexa.py first.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -u main.py
if errorlevel 1 pause
