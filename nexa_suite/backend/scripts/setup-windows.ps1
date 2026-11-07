param(
  [string]$PythonPath = "python",
  [switch]$ForceRecreate
)

$ErrorActionPreference = "Stop"
$backendDir = Split-Path -Parent $PSScriptRoot
$venvDir = Join-Path $backendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if ((Test-Path -LiteralPath $venvDir) -and $ForceRecreate) {
  $backupDir = Join-Path $backendDir (".venv.backup-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
  Move-Item -LiteralPath $venvDir -Destination $backupDir
  Write-Host "Previous environment preserved at: $backupDir"
}

if (-not (Test-Path -LiteralPath $venvPython)) {
  & $PythonPath -m venv $venvDir
  if ($LASTEXITCODE -ne 0) { throw "Virtual environment creation failed." }
}

& $venvPython -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $venvPython -m pip install -r (Join-Path $backendDir "requirements.txt") "pyinstaller>=6,<7"
if ($LASTEXITCODE -ne 0) { throw "Backend dependency installation failed." }
& $venvPython -c "import fastapi, uvicorn, selenium, huggingface_hub, PIL, edge_tts; print('Nexa optional dependencies: ready')"
if ($LASTEXITCODE -ne 0) { throw "Backend dependency verification failed." }
Write-Host "Backend environment ready: $venvPython"
