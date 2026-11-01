'use strict';

/**
 * Narrowly-scoped preload bridge. Exposes ONLY a fixed set of safe, validated
 * IPC channels to the renderer — no Node APIs, no arbitrary shell execution.
 */

const { contextBridge, ipcRenderer } = require('electron');

const invoke = (channel, payload) => ipcRenderer.invoke(channel, payload);

contextBridge.exposeInMainWorld('chhotiDon', {
  isDesktop: true,
  platform: process.platform,

  // Service lifecycle
  getServiceStatus: () => invoke('services:status'),
  restartServices: () => invoke('services:restart'),

  // Window controls
  minimize: () => invoke('window:minimize'),
  maximizeToggle: () => invoke('window:maximizeToggle'),
  close: () => invoke('window:close'),

  // Preferences
  getMinimizeToTray: () => invoke('prefs:getMinimizeToTray'),
  setMinimizeToTray: (value) => invoke('prefs:setMinimizeToTray', Boolean(value)),
  getKeepOllama: () => invoke('prefs:getKeepOllama'),
  setKeepOllama: (value) => invoke('prefs:setKeepOllama', Boolean(value)),

  // Misc
  quit: () => invoke('app:quit'),
  openLogsFolder: () => invoke('app:openLogsFolder'),
  getVersion: () => invoke('app:version'),
  selectDirectory: () => invoke('dialog:selectDirectory'),
});

// Readiness-screen bridge (used only while loading.html is shown).
contextBridge.exposeInMainWorld('chhotiLoader', {
  onProgress: (cb) => ipcRenderer.on('startup:progress', (_e, msg) => cb(msg)),
  onError: (cb) => ipcRenderer.on('startup:error', (_e, data) => cb(data)),
  onSetup: (cb) => ipcRenderer.on('startup:setup', (_e, data) => cb(data)),
  retry: () => ipcRenderer.send('startup:retry'),
  continueAnyway: () => ipcRenderer.send('startup:continue'),
});
