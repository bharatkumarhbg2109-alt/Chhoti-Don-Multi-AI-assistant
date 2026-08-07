# CHHOTI DON — Desktop Shell (Electron)

Native Windows desktop wrapper around the existing CHHOTI DON backend + React
dashboard. Opens in its own window (never a browser tab), orchestrates the local
services, and shows the dashboard once the backend is healthy.

## What it does

- Starts the **Python backend** (`app.py`) as a managed child process and waits
  for `/api/health` before showing the UI.
- Detects and **reuses an already-running Ollama** — it only starts Ollama if it
  isn't running, and only stops Ollama on quit if *this app* started it.
- Loads the React dashboard **same-origin from the backend** (`http://127.0.0.1:8000/`),
  so `/api` calls need no CORS and there is no separate frontend server at runtime.
- Persists window size/position, single-instance lock, system tray, readiness
  screen with retry, and a "minimise to tray / quit" lifecycle.

## Security

`contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`, a strict CSP,
navigation is locked to the local app (external links open in the system browser),
and the preload exposes only a small, fixed set of validated IPC methods — no
Node APIs and no arbitrary shell access to the renderer.

## Requirements

- **Python 3** on PATH (or a project virtualenv), with `pip install -r ../requirements.txt`.
- **Ollama** installed with the configured model (`qwen3.5:latest`). If the model
  is missing the app still runs (simulated fallback) and shows the exact
  `ollama pull qwen3.5:latest` command.
- The React dashboard must be built once: `cd ../chhoti-don-react && npm run build`.

## Run in development

```powershell
cd desktop
npm install          # first time only (Electron + electron-builder)
npm start            # launches the native window
```

## Build a portable app (no admin required)

```powershell
cd desktop
./build-portable.ps1
# -> desktop/release/CHHOTI DON/CHHOTI DON.exe
```

The portable build bundles the Electron runtime, the desktop shell
(`resources/app`), and the backend + built dashboard (`resources/app_root`). It
uses the system Python at runtime. Data (history DB, logs, window state) is
written to `%APPDATA%\CHHOTI DON\runtime\`.

## Build the NSIS installer (optional)

```powershell
cd desktop
npm run dist         # electron-builder -> desktop/release/CHHOTI-DON-Setup-<ver>.exe
```

> **Note:** On Windows, `electron-builder` extracts a code-signing toolchain
> (`winCodeSign`) that contains macOS symlinks. Creating those symlinks requires
> **Windows Developer Mode** (Settings → Privacy & security → For developers) or
> an elevated shell. Without it the installer step fails with
> *"Cannot create symbolic link : A required privilege is not held by the client."*
> Enable Developer Mode, then `npm run dist` produces the NSIS installer + a
> portable exe. The app itself needs no elevation to run.

## Desktop shortcuts

From the project root:

```powershell
./Create-Desktop-Shortcuts.ps1
```

Creates **CHHOTI DON** (launches `CHHOTI DON.exe`) and **CHHOTI DON — Stop**
(runs `Stop-ChhotiDon.ps1`, which stops only app-owned processes and preserves
an externally started Ollama) on the Desktop and Start Menu.
