param(
  [string]$PythonPath = "",
  [switch]$InstallBuildDependency
)

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $backendDir ".venv\Scripts\python.exe"
if (-not $PythonPath) { $PythonPath = $venvPython }
if (-not (Test-Path -LiteralPath $PythonPath)) { throw "Working backend Python not found: $PythonPath" }

if ($InstallBuildDependency) {
  & $PythonPath -m pip install "pyinstaller>=6,<7"
  if ($LASTEXITCODE -ne 0) { throw "PyInstaller installation failed." }
}

& $PythonPath -c "import PyInstaller"
if ($LASTEXITCODE -ne 0) { throw "PyInstaller is missing. Run this script with -InstallBuildDependency." }

Push-Location $backendDir
try {
  & $PythonPath -m PyInstaller --noconfirm --clean nexa_backend.spec
  if ($LASTEXITCODE -ne 0) { throw "Standalone backend build failed." }
} finally { Pop-Location }

$output = Join-Path $backendDir "dist\nexa-backend\nexa-backend.exe"
if (-not (Test-Path -LiteralPath $output)) { throw "Backend executable was not produced." }
Write-Host "Standalone backend: $output"
