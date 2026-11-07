@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\.nexa-setup-complete" goto launch
py -3.13 --version >nul 2>&1
if not errorlevel 1 (
  py -3.13 setup_nexa.py
  goto installed
)
py -3.12 --version >nul 2>&1
if not errorlevel 1 (
  py -3.12 setup_nexa.py
  goto installed
)
py -3.11 --version >nul 2>&1
if not errorlevel 1 (
  py -3.11 setup_nexa.py
  goto installed
)
python --version >nul 2>&1
if not errorlevel 1 (
  python setup_nexa.py
  goto installed
)
echo Install Python 3.11-3.13 from python.org with Add Python to PATH enabled.
pause
exit /b 1
:installed
if errorlevel 1 (
  echo Setup failed. Check the message above, then retry this launcher.
  pause
  exit /b 1
)
:launch
call start_nexa.cmd
