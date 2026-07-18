'use strict';

/**
 * CHHOTI DON — Electron main process.
 *
 * Opens a native desktop window (never a browser tab), orchestrates the local
 * services through the process manager, shows a readiness screen until the
 * backend is healthy, then loads the React dashboard served same-origin by the
 * backend. Closing the window minimises to the tray; quitting stops only the
 * services this app started.
 */

const { app, BrowserWindow, Tray, Menu, ipcMain, shell, nativeImage, dialog } = require('electron');
const path = require('path');
const fs = require('fs');

const cfg = require('./config.cjs');
const pm = require('./processManager.cjs');
const windowState = require('./windowState.cjs');

const ASSETS = path.join(__dirname, '..', 'assets');
const LOADING_HTML = path.join(ASSETS, 'loading.html');
const PRELOAD = path.join(__dirname, '..', 'preload', 'preload.cjs');

let mainWindow = null;
let tray = null;
let isQuitting = false;
let servicesReady = false;

// ── Preferences (persisted JSON in the runtime dir) ───────────
function prefsFile() {
  return path.join(cfg.runtimeDir(), 'desktop-prefs.json');
}
function loadPrefs() {
  try {
    return { quitOnClose: false, keepOllama: false, ...JSON.parse(fs.readFileSync(prefsFile(), 'utf8')) };
  } catch {
    return { quitOnClose: false, keepOllama: false };
  }
}
function savePrefs(p) {
  try {
    fs.mkdirSync(cfg.runtimeDir(), { recursive: true });
    fs.writeFileSync(prefsFile(), JSON.stringify(p));
  } catch {
    /* ignore */
  }
}
let prefs = { quitOnClose: false, keepOllama: false };

// ── Icon ──────────────────────────────────────────────────────
function appIcon() {
  for (const name of ['icon.png', 'icon.ico']) {
    const p = path.join(ASSETS, name);
    if (fs.existsSync(p)) {
      const img = nativeImage.createFromPath(p);
      if (!img.isEmpty()) return img;
    }
  }
  return null;
}

// ── Window ────────────────────────────────────────────────────
function createWindow() {
  const bounds = windowState.load();
  const icon = appIcon();

  mainWindow = new BrowserWindow({
    ...bounds,
    minWidth: 720,
    minHeight: 560,
    show: false,
    backgroundColor: '#050308',
    title: 'CHHOTI DON',
    icon: icon || undefined,
    autoHideMenuBar: true,
    webPreferences: {
      preload: PRELOAD,
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      webSecurity: true,
      spellcheck: false,
    },
  });

  windowState.bind(mainWindow);
  mainWindow.once('ready-to-show', () => mainWindow.show());

  // Show the readiness screen first.
  mainWindow.loadFile(LOADING_HTML);

  // Harden navigation: keep the window on the local app; open other links
  // in the system browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (isExternal(url)) shell.openExternal(url);
    return { action: 'deny' };
  });
  mainWindow.webContents.on('will-navigate', (event, url) => {
    if (isExternal(url)) {
      event.preventDefault();
      shell.openExternal(url);
    }
  });

  // Minimise to tray on close unless the user chose "quit on close".
  mainWindow.on('close', (event) => {
    if (!isQuitting && !prefs.quitOnClose) {
      event.preventDefault();
      mainWindow.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function isExternal(url) {
  return !url.startsWith(cfg.BACKEND_BASE) && !url.startsWith('file://');
}

// ── Content Security Policy ───────────────────────────────────
function applyCSP() {
  const ses = mainWindow.webContents.session;
  ses.webRequest.onHeadersReceived((details, callback) => {
    callback({
      responseHeaders: {
        ...details.responseHeaders,
        'Content-Security-Policy': [
          "default-src 'self' http://127.0.0.1:8000; " +
            "script-src 'self' 'unsafe-inline'; " +
            "style-src 'self' 'unsafe-inline'; " +
            "img-src 'self' data:; " +
            "connect-src 'self' http://127.0.0.1:8000; " +
            "font-src 'self' data:; " +
            "object-src 'none'; base-uri 'self'; frame-ancestors 'none';",
        ],
      },
    });
  });
}

// ── Startup orchestration ─────────────────────────────────────
async function runStartup() {
  const sendProgress = (msg) => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('startup:progress', msg);
  };
  const sendError = (data) => {
    if (mainWindow && !mainWindow.isDestroyed()) mainWindow.webContents.send('startup:error', data);
  };

  sendProgress('Checking local services…');
  let result;
  try {
    result = await pm.startAll(sendProgress);
  } catch (e) {
    sendError({ service: 'startup', reason: String(e && e.message ? e.message : e) });
    return;
  }

  if (!result.ok) {
    const err = result.errors[0] || { service: 'backend', reason: 'Startup failed.' };
    sendError({
      service: err.service,
      reason: err.reason,
      log: err.log,
      hint: err.reason && err.reason.includes('Python')
        ? 'Install Python 3 (python.org) or create a project virtual environment, then Retry.'
        : undefined,
    });
    return;
  }

  if (result.modelMissing) {
    // Not fatal — the backend runs in simulated mode. Inform, then continue.
    sendProgress(`Model ${result.modelMissing.model} not installed — continuing in simulated mode.`);
  }

  servicesReady = true;
  sendProgress('Ready. Loading dashboard…');
  await mainWindow.loadURL(cfg.APP_URL);
  buildTray();
}

// ── Tray ──────────────────────────────────────────────────────
function buildTray() {
  if (tray) return;
  const icon = appIcon();
  try {
    tray = new Tray(icon || nativeImage.createEmpty());
  } catch {
    return;
  }
  tray.setToolTip('CHHOTI DON');
  refreshTrayMenu();
  tray.on('double-click', showMainWindow);
}

async function refreshTrayMenu() {
  if (!tray) return;
  let statusLabel = 'Services: checking…';
  try {
    const s = await pm.getStatus();
    statusLabel = `Backend: ${s.backend.healthy ? 'online' : 'offline'} · Ollama: ${s.ollama.reachable ? 'online' : 'offline'}`;
  } catch {
    /* ignore */
  }
  const menu = Menu.buildFromTemplate([
    { label: 'Open CHHOTI DON', click: showMainWindow },
    { label: statusLabel, enabled: false },
    { type: 'separator' },
    {
      label: 'Restart services',
      click: async () => {
        await pm.stopOwned({ keepOllama: prefs.keepOllama });
        await pm.startAll(() => {});
        refreshTrayMenu();
      },
    },
    { type: 'separator' },
    {
      label: 'Quit CHHOTI DON',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);
  tray.setContextMenu(menu);
}

function showMainWindow() {
  if (!mainWindow) {
    createWindow();
    applyCSP();
    if (servicesReady) mainWindow.loadURL(cfg.APP_URL);
    else runStartup();
    return;
  }
  if (mainWindow.isMinimized()) mainWindow.restore();
  mainWindow.show();
  mainWindow.focus();
}

// ── IPC handlers ──────────────────────────────────────────────
function registerIpc() {
  ipcMain.handle('services:status', () => pm.getStatus());
  ipcMain.handle('services:restart', async () => {
    try {
      await pm.stopOwned({ keepOllama: prefs.keepOllama });
      const r = await pm.startAll(() => {});
      refreshTrayMenu();
      return { ok: r.ok, error: r.ok ? null : (r.errors[0] && r.errors[0].reason) };
    } catch (e) {
      return { ok: false, error: String(e && e.message ? e.message : e) };
    }
  });

  ipcMain.handle('window:minimize', () => mainWindow && mainWindow.minimize());
  ipcMain.handle('window:maximizeToggle', () => {
    if (!mainWindow) return;
    if (mainWindow.isMaximized()) mainWindow.unmaximize();
    else mainWindow.maximize();
  });
  ipcMain.handle('window:close', () => mainWindow && mainWindow.close());

  ipcMain.handle('prefs:getQuitOnClose', () => prefs.quitOnClose);
  ipcMain.handle('prefs:setQuitOnClose', (_e, v) => {
    prefs.quitOnClose = Boolean(v);
    savePrefs(prefs);
    return prefs.quitOnClose;
  });
  ipcMain.handle('prefs:getKeepOllama', () => prefs.keepOllama);
  ipcMain.handle('prefs:setKeepOllama', (_e, v) => {
    prefs.keepOllama = Boolean(v);
    savePrefs(prefs);
    return prefs.keepOllama;
  });

  ipcMain.handle('app:quit', () => {
    isQuitting = true;
    app.quit();
  });
  ipcMain.handle('app:openLogsFolder', () => shell.openPath(cfg.runtimeDir()));
  ipcMain.handle('app:version', () => app.getVersion());

  ipcMain.on('startup:retry', () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      mainWindow.loadFile(LOADING_HTML).then(() => runStartup());
    }
  });
}

// ── App lifecycle ─────────────────────────────────────────────
const gotLock = app.requestSingleInstanceLock();
if (!gotLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    showMainWindow();
  });

  app.whenReady().then(() => {
    prefs = loadPrefs();
    registerIpc();
    createWindow();
    applyCSP();
    runStartup();

    app.on('activate', () => {
      if (BrowserWindow.getAllWindows().length === 0) showMainWindow();
    });
  });

  app.on('window-all-closed', () => {
    // Stay alive in the tray on Windows/Linux; only fully quit via tray/quit.
    if (process.platform === 'darwin') return;
    if (prefs.quitOnClose) app.quit();
  });

  app.on('before-quit', async (event) => {
    if (isQuitting) return;
    isQuitting = true;
    event.preventDefault();
    try {
      await pm.stopOwned({ keepOllama: prefs.keepOllama });
    } catch {
      /* ignore */
    }
    app.exit(0);
  });
}
