param(
  [switch]$BuildInstaller,
  [switch]$SkipBackendBuild
)

$ErrorActionPreference = "Stop"
$frontendDir = Split-Path -Parent $PSScriptRoot
$projectDir = Split-Path -Parent $frontendDir
$releaseDir = Join-Path $projectDir "release\NexaAI"
$backendDir = Join-Path $projectDir "backend"
$backendExe = Join-Path $backendDir "dist\nexa-backend\nexa-backend.exe"

if (-not $SkipBackendBuild) {
  & (Join-Path $backendDir "scripts\build-standalone.ps1")
  if ($LASTEXITCODE -ne 0) { throw "Standalone backend build failed." }
}
if (-not (Test-Path -LiteralPath $backendExe)) { throw "Standalone backend executable is missing: $backendExe" }

Push-Location $frontendDir
try {
  & npm.cmd run build
  if ($LASTEXITCODE -ne 0) { throw "Frontend build failed." }
} finally { Pop-Location }

if (Test-Path -LiteralPath $releaseDir) { Remove-Item -LiteralPath $releaseDir -Recurse -Force }
New-Item -ItemType Directory -Path $releaseDir | Out-Null
$electronRuntime = Join-Path $frontendDir "node_modules\electron\dist"
if (-not (Test-Path -LiteralPath (Join-Path $electronRuntime "electron.exe"))) { throw "Electron runtime is missing. Run npm install first." }
Copy-Item -Path (Join-Path $electronRuntime "*") -Destination $releaseDir -Recurse
Move-Item -LiteralPath (Join-Path $releaseDir "electron.exe") -Destination (Join-Path $releaseDir "NexaAI.exe")

$appDir = Join-Path $releaseDir "resources\app"
New-Item -ItemType Directory -Path $appDir | Out-Null
Copy-Item -LiteralPath (Join-Path $frontendDir "dist") -Destination (Join-Path $appDir "dist") -Recurse
Copy-Item -LiteralPath (Join-Path $frontendDir "electron") -Destination (Join-Path $appDir "electron") -Recurse
Copy-Item -LiteralPath (Join-Path $backendDir "dist\nexa-backend") -Destination (Join-Path $appDir "backend") -Recurse
Copy-Item -LiteralPath (Join-Path $projectDir "packaging\runtime-package.json") -Destination (Join-Path $appDir "package.json")
Copy-Item -LiteralPath (Join-Path $projectDir "README.md") -Destination (Join-Path $releaseDir "README.md")

$zipPath = Join-Path $projectDir "release\NexaAI-Windows.zip"
if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
Compress-Archive -LiteralPath $releaseDir -DestinationPath $zipPath -CompressionLevel Optimal
Write-Host "Standalone portable release: $zipPath"

if ($BuildInstaller) {
  $iscc = Get-Command ISCC.exe -ErrorAction SilentlyContinue
  if (-not $iscc) { throw "Inno Setup 6 (ISCC.exe) is required for -BuildInstaller." }
  & $iscc.Source (Join-Path $projectDir "packaging\NexaAI.iss")
  if ($LASTEXITCODE -ne 0) { throw "Inno Setup build failed." }
}
