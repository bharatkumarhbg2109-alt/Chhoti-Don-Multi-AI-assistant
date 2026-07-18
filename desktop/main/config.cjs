'use strict';

/**
 * Central configuration + path resolution for the CHHOTI DON desktop shell.
 * All paths are resolved from the install/project directory and support spaces.
 */

const path = require('path');
const fs = require('fs');
const { app } = require('electron');
const { execFileSync } = require('child_process');

const BACKEND_HOST = '127.0.0.1';
const BACKEND_PORT = Number(process.env.CHHOTI_DON_BACKEND_PORT || 8000);
const BACKEND_BASE = `http://${BACKEND_HOST}:${BACKEND_PORT}`;
const BACKEND_HEALTH_URL = `${BACKEND_BASE}/api/health`;
const BACKEND_STATUS_URL = `${BACKEND_BASE}/api/status`;
const APP_URL = `${BACKEND_BASE}/`;

const OLLAMA_HOST = process.env.OLLAMA_HOST || 'http://127.0.0.1:11434';
const OLLAMA_TAGS_URL = `${OLLAMA_HOST.replace(/\/$/, '')}/api/tags`;

// The configured local model. Mirrors core/config.py's LOCAL_MODEL default so
// the shell never guesses a random model.
const OLLAMA_MODEL = process.env.CHHOTI_DON_OLLAMA_MODEL || 'mistral:latest';

/** Project root that holds app.py / core / chhoti-don-react/dist. */
function projectRoot() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'app_root');
  }
  // desktop/main/config.cjs → project root is two levels up.
  return path.resolve(__dirname, '..', '..');
}

/** Writable runtime directory for PID files, logs and the history DB. */
function runtimeDir() {
  if (app.isPackaged) {
    return path.join(app.getPath('userData'), 'runtime');
  }
  return path.join(projectRoot(), '.runtime');
}

function ensureRuntimeDir() {
  const dir = runtimeDir();
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

/**
 * Resolve the Python interpreter:
 *   1. project virtual environment (.venv / venv / env)
 *   2. configured interpreter (CHHOTI_DON_PYTHON)
 *   3. system python / py launcher (safe fallback)
 */
function resolvePython() {
  const root = projectRoot();
  const venvCandidates = [
    path.join(root, '.venv', 'Scripts', 'python.exe'),
    path.join(root, 'venv', 'Scripts', 'python.exe'),
    path.join(root, 'env', 'Scripts', 'python.exe'),
  ];
  for (const c of venvCandidates) {
    if (fs.existsSync(c)) return { cmd: c, args: [] };
  }
  if (process.env.CHHOTI_DON_PYTHON && fs.existsSync(process.env.CHHOTI_DON_PYTHON)) {
    return { cmd: process.env.CHHOTI_DON_PYTHON, args: [] };
  }
  // System fallbacks — verified to run without throwing.
  for (const candidate of ['python', 'py']) {
    try {
      execFileSync(candidate, ['--version'], { stdio: 'ignore' });
      return { cmd: candidate, args: [] };
    } catch {
      /* try next */
    }
  }
  return null;
}

/** Resolve the Ollama executable path (PATH or the default Windows install). */
function resolveOllama() {
  // 1. explicit override
  if (process.env.CHHOTI_DON_OLLAMA && fs.existsSync(process.env.CHHOTI_DON_OLLAMA)) {
    return process.env.CHHOTI_DON_OLLAMA;
  }
  // 2. PATH lookup
  try {
    const out = execFileSync(process.platform === 'win32' ? 'where' : 'which', ['ollama'], {
      encoding: 'utf8',
    });
    const first = out.split(/\r?\n/).map((s) => s.trim()).filter(Boolean)[0];
    if (first && fs.existsSync(first)) return first;
  } catch {
    /* not on PATH */
  }
  // 3. default Windows install location
  const local = process.env.LOCALAPPDATA;
  if (local) {
    const guess = path.join(local, 'Programs', 'Ollama', 'ollama.exe');
    if (fs.existsSync(guess)) return guess;
  }
  return null;
}

module.exports = {
  BACKEND_HOST,
  BACKEND_PORT,
  BACKEND_BASE,
  BACKEND_HEALTH_URL,
  BACKEND_STATUS_URL,
  APP_URL,
  OLLAMA_HOST,
  OLLAMA_TAGS_URL,
  OLLAMA_MODEL,
  projectRoot,
  runtimeDir,
  ensureRuntimeDir,
  resolvePython,
  resolveOllama,
};
