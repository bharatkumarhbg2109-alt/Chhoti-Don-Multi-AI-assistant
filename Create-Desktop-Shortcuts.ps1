param([switch]$Quiet)

# Creates desktop + Start Menu shortcuts for the NATIVE CHHOTI DON desktop app.
# The Start shortcut launches the Electron executable directly (never a browser
# or a URL). The Stop shortcut runs Stop-ChhotiDon.ps1, which stops only the
# processes owned by CHHOTI DON.

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")
$StartMenu = [Environment]::GetFolderPath("Programs")
$Shell = New-Object -ComObject WScript.Shell
$dash = [char]0x2014  # em dash, for display only

# Resolve the desktop executable:
#   1. installed build (electron-builder NSIS output), if present
#   2. portable build produced by desktop\build-portable.ps1
$installed = Join-Path $env:LOCALAPPDATA "Programs\chhoti-don-desktop\CHHOTI DON.exe"
$portable = Join-Path $Root "desktop\release\CHHOTI DON\CHHOTI DON.exe"

if (Test-Path $installed) {
    $exe = $installed
} elseif (Test-Path $portable) {
    $exe = $portable
} else {
    throw "CHHOTI DON.exe not found. Build it first: run desktop\build-portable.ps1 (or 'npm run dist' in desktop\ with Developer Mode enabled)."
}

$icon = Join-Path $Root "desktop\assets\icon.ico"
if (-not (Test-Path $icon)) { $icon = $exe }
$workDir = Split-Path $exe -Parent

function New-Shortcut($path, $target, $arguments, $iconLoc, $desc, $work) {
    $sc = $Shell.CreateShortcut($path)
    $sc.TargetPath = $target
    if ($arguments) { $sc.Arguments = $arguments }
    $sc.WorkingDirectory = $work
    $sc.IconLocation = $iconLoc
    $sc.Description = $desc
    $sc.Save()
}

# --- CHHOTI DON (Start) : launches the native desktop app ---
foreach ($dir in @($Desktop, $StartMenu)) {
    New-Shortcut (Join-Path $dir "CHHOTI DON.lnk") $exe $null "$icon,0" "CHHOTI DON - Private AI command center" $workDir
}

# --- CHHOTI DON - Stop : stops only app-owned services ---
$stopScript = Join-Path $Root "Stop-ChhotiDon.ps1"
$psArgs = "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$stopScript`""
$stopIcon = "$env:SystemRoot\System32\shell32.dll,131"
foreach ($dir in @($Desktop, $StartMenu)) {
    New-Shortcut (Join-Path $dir "CHHOTI DON $dash Stop.lnk") "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe" $psArgs $stopIcon "Stop CHHOTI DON services" $Root
}

Write-Output ("Start shortcut -> " + $exe)
Write-Output (Join-Path $Desktop "CHHOTI DON.lnk")
Write-Output (Join-Path $Desktop "CHHOTI DON $dash Stop.lnk")

if (-not $Quiet) {
    Add-Type -AssemblyName PresentationFramework
    [System.Windows.MessageBox]::Show(
        "Desktop shortcuts created:`n`nCHHOTI DON  (launches the native app)`nCHHOTI DON $dash Stop",
        "CHHOTI DON Setup", "OK", "Information") | Out-Null
}
