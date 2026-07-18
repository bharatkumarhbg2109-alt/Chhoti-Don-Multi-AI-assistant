$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$Desktop = [Environment]::GetFolderPath("Desktop")
$Shell = New-Object -ComObject WScript.Shell

$launcherVbs = Join-Path $Root "Launch-ChhotiDon.vbs"
$stopVbs = Join-Path $Root "Stop-ChhotiDon.vbs"

if (-not (Test-Path $launcherVbs)) {
    throw "Launch-ChhotiDon.vbs was not found in the project root."
}

$customIcon = Join-Path $Root "chhoti_don.ico"
$iconLocation = if (Test-Path $customIcon) {
    $customIcon
}
else {
    "$env:SystemRoot\System32\shell32.dll,220"
}

$startShortcutPath = Join-Path $Desktop "CHHOTI DON.lnk"
$startShortcut = $Shell.CreateShortcut($startShortcutPath)
$startShortcut.TargetPath = "$env:SystemRoot\System32\wscript.exe"
$startShortcut.Arguments = """" + $launcherVbs + """"
$startShortcut.WorkingDirectory = $Root
$startShortcut.IconLocation = $iconLocation
$startShortcut.Description = "Start CHHOTI DON AI Assistant"
$startShortcut.Save()

$stopShortcutPath = Join-Path $Desktop "Stop CHHOTI DON.lnk"
$stopShortcut = $Shell.CreateShortcut($stopShortcutPath)
$stopShortcut.TargetPath = "$env:SystemRoot\System32\wscript.exe"
$stopShortcut.Arguments = """" + $stopVbs + """"
$stopShortcut.WorkingDirectory = $Root
$stopShortcut.IconLocation = "$env:SystemRoot\System32\shell32.dll,131"
$stopShortcut.Description = "Stop CHHOTI DON AI Assistant"
$stopShortcut.Save()

Add-Type -AssemblyName PresentationFramework
[System.Windows.MessageBox]::Show(
    "Desktop shortcuts created successfully:`n`nCHHOTI DON`nStop CHHOTI DON",
    "CHHOTI DON Setup",
    "OK",
    "Information"
) | Out-Null
