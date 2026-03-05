param(
  [string]$IconPath = 'backend\backend.ico'
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not (Test-Path $python)) {
  throw "Missing venv python at $python. Create the venv and install backend deps (including PyInstaller) first."
}

$appPy = Join-Path $repoRoot 'backend\app.py'
$distPath = Join-Path $repoRoot 'src-tauri\resources'
$frontendDist = Join-Path $repoRoot 'dist'
$frontendResourcePath = Join-Path $distPath 'web'
$workPath = Join-Path $repoRoot 'backend\build'
$specPath = Join-Path $repoRoot 'backend'
$targetExe = Join-Path $distPath 'local_v_backend.exe'
$iconFullPath = if ([System.IO.Path]::IsPathRooted($IconPath)) {
  $IconPath
} else {
  Join-Path $repoRoot $IconPath
}

# PyInstaller overwrites by deleting the old EXE. On Windows this can fail if the backend is still running
# or antivirus is scanning the file, so retry a few times to reduce flakiness.
for ($i = 0; $i -lt 10; $i++) {
  if (-not (Test-Path $targetExe)) { break }
  try {
    Remove-Item -Force -ErrorAction Stop $targetExe
    break
  } catch {
    Start-Sleep -Milliseconds (200 + ($i * 250))
  }
}

if (Test-Path $targetExe) {
  throw "Failed to overwrite $targetExe (file is locked). Close the installed app / any running backend process and retry."
}

if (Test-Path $frontendResourcePath) {
  Remove-Item -Recurse -Force $frontendResourcePath
}

if (Test-Path $frontendDist) {
  New-Item -ItemType Directory -Force -Path $frontendResourcePath | Out-Null
  Copy-Item -Path (Join-Path $frontendDist '*') -Destination $frontendResourcePath -Recurse -Force
} else {
  Write-Warning "Frontend dist not found at $frontendDist. Run 'npm run build' before backend build for LAN page sharing."
}

$pyInstallerArgs = @(
  '-m', 'PyInstaller',
  '-F', $appPy,
  '--name', 'local_v_backend',
  '--distpath', $distPath,
  '--workpath', $workPath,
  '--specpath', $specPath,
  '--noconfirm'
)

if (Test-Path $iconFullPath) {
  $pyInstallerArgs += @('--icon', $iconFullPath)
  Write-Host "Using backend icon: $iconFullPath"
} else {
  Write-Warning "Backend icon not found at $iconFullPath. Continue without --icon."
}

& $python @pyInstallerArgs
