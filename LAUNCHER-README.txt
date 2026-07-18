CHHOTI DON — WINDOWS ONE-CLICK LAUNCHER
======================================

PURPOSE
-------
This launcher starts:
1. The FastAPI backend on http://127.0.0.1:8000
2. The React/Vite frontend on http://127.0.0.1:5173
3. Your default browser automatically

It also creates Start and Stop shortcuts on the Windows desktop.

INSTALLATION
------------
1. Copy every file from this launcher pack into the CHHOTI DON project root.
   Put them beside app.py, main.py, package.json, and the chhoti-don-react folder.

2. Double-click:
   Install-Desktop-Shortcuts.bat

3. Two shortcuts will appear on the desktop:
   - CHHOTI DON
   - Stop CHHOTI DON

4. Double-click CHHOTI DON to start the assistant.

AUTO-DETECTION
--------------
The launcher automatically checks:
- .venv, venv, or env for Python
- chhoti-don-react/package.json first
- root/package.json as fallback
- app.py or main.py for FastAPI

BACKEND MODULE OVERRIDE
-----------------------
If the launcher selects the wrong backend file, open Start-ChhotiDon.ps1
and change:

$PreferredBackendModule = ""

to one of these:

$PreferredBackendModule = "app:app"

or:

$PreferredBackendModule = "main:app"

CUSTOM ICON
-----------
Put an ICO file named:

chhoti_don.ico

inside the project root, then run Install-Desktop-Shortcuts.bat again.

LOGS
----
Startup logs are stored in:

logs\backend.out.log
logs\backend.err.log
logs\frontend.out.log
logs\frontend.err.log
logs\npm-install.out.log
logs\npm-install.err.log

SECURITY
--------
Both services bind only to 127.0.0.1, so they are not exposed to other
devices on the network.
