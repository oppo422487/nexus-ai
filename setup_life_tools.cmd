@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
 echo Create the Python 3.12 virtual environment and install project requirements first.
 pause
 exit /b 1
)
".venv\Scripts\python.exe" -m pip install -r requirements-life.txt
if errorlevel 1 goto failed
echo Optional offline translation and meeting audio dependencies are larger.
choice /C YN /M "Install optional offline dependencies too?"
if errorlevel 2 goto ocr
".venv\Scripts\python.exe" -m pip install -r requirements-life-models.txt
if errorlevel 1 goto failed
:ocr
echo Tesseract OCR needs a separate engine plus eng and ben language data.
echo See LIFE-TOOLS.md for setup, account connections and Excel MCP settings.
pause
exit /b 0
:failed
echo Setup failed. Keep the displayed error and check LIFE-TOOLS.md.
pause
exit /b 1
