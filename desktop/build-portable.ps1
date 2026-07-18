<#
  build-portable.ps1
  Assembles a portable CHHOTI DON desktop app from the local Electron runtime.

  Fallback packager used when electron-builder's NSIS/winCodeSign step cannot
  run (it needs Windows Developer Mode or admin rights to extract the code-
  signing toolchain's macOS symlinks). The CHHOTI DON shell has NO external npm
  dependencies (only Node/Electron built-ins), so a portable build is simply:
  the Electron runtime + resources/app (shell) + resources/app_root (backend +
  built dashboard).

  Output: desktop\release\CHHOTI DON\CHHOTI DON.exe
#>
param(
  [string]$OutName = "CHHOTI DON"
)
$ErrorActionPreference = "Stop"
$DesktopDir = $PSScriptRoot
$ProjectRoot = Split-Path $DesktopDir -Parent
$ElectronDist = Join-Path $DesktopDir "node_modules\electron\dist"
$Release = Join-Path $DesktopDir "release"
$AppDir = Join-Path $Release $OutName

if (-not (Test-Path $ElectronDist)) { throw "Electron runtime not found. Run 'npm install' in desktop first." }

Write-Host "Cleaning $AppDir"
if (Test-Path $AppDir) { Remove-Item $AppDir -Recurse -Force }
New-Item -ItemType Directory -Force -Path $AppDir | Out-Null

Write-Host "Copying Electron runtime"
robocopy $ElectronDist $AppDir /E /NFL /NDL /NJH /NJS /NP | Out-Null

$src = Join-Path $AppDir "electron.exe"
if (Test-Path $src) { Rename-Item -LiteralPath $src -NewName "$OutName.exe" -Force }
$dst = Join-Path $AppDir "$OutName.exe"

$ResApp = Join-Path $AppDir "resources\app"
New-Item -ItemType Directory -Force -Path $ResApp | Out-Null
foreach ($item in @("main", "preload", "assets", "package.json")) {
  $s = Join-Path $DesktopDir $item
  if (Test-Path $s -PathType Container) {
    robocopy $s (Join-Path $ResApp $item) /E /NFL /NDL /NJH /NJS /NP | Out-Null
  } else {
    Copy-Item $s (Join-Path $ResApp $item) -Force
  }
}
$defApp = Join-Path $AppDir "resources\default_app.asar"
if (Test-Path $defApp) { Remove-Item $defApp -Force }

$Root = Join-Path $AppDir "resources\app_root"
New-Item -ItemType Directory -Force -Path $Root | Out-Null
foreach ($f in @("app.py", "requirements.txt", "chhoti_don_ui.html")) {
  Copy-Item (Join-Path $ProjectRoot $f) (Join-Path $Root $f) -Force
}
foreach ($d in @("core", "cyber_engine", "tools", "chhoti_agents")) {
  robocopy (Join-Path $ProjectRoot $d) (Join-Path $Root $d) /E /XD "__pycache__" /XF "*.pyc" "*.pyo" /NFL /NDL /NJH /NJS /NP | Out-Null
}
$distSrc = Join-Path $ProjectRoot "chhoti-don-react\dist"
$distDst = Join-Path $Root "chhoti-don-react\dist"
New-Item -ItemType Directory -Force -Path (Split-Path $distDst -Parent) | Out-Null
robocopy $distSrc $distDst /E /NFL /NDL /NJH /NJS /NP | Out-Null

$rcedit = Get-ChildItem -Path (Join-Path $DesktopDir "node_modules") -Recurse -Filter "rcedit*.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
$icon = Join-Path $DesktopDir "assets\icon.ico"
if ($rcedit -and (Test-Path $icon)) {
  try { & $rcedit.FullName $dst --set-icon $icon; Write-Host "Set exe icon" } catch { Write-Host "Icon stamp skipped" }
} else {
  Write-Host "rcedit not found - exe uses default Electron icon (window/tray icon still branded)"
}

Write-Host "Portable build ready:"
Write-Host $dst