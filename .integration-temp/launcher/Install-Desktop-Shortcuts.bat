@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Create-Desktop-Shortcuts.ps1"
if errorlevel 1 (
  echo.
  echo Shortcut setup failed. Please read the error above.
  pause
)
