'use strict';

/**
 * CHHOTI DON desktop-side process manager.
 *
 * Manages Ollama and the Python backend. Only processes that THIS app starts are
 * ever stopped — ownership is tracked with PID files in the runtime directory
 * (compatible with the existing Stop-ChhotiDon.ps1 convention) plus in-memory
 * child references. Existing healthy services are detected and reused, never
 * duplicated. Termination is graceful first, forceful only after a timeout.
 */

const fs = require('fs');
const path = require('path');
const { spawn, execFile } = require('child_process');

const cfg = require('./config.cjs');
const { httpGet, isReachable, waitForUrl } = require('./serviceHealth.cjs');

const state = {
  backend: { child: null, owned: false, pid: null },
  ollama: { child: null, owned: false, pid: null },
  logStreams: {},
};

function log(line) {
  const dir = cfg.ensureRuntimeDir();
  const msg = `[${new Date().toISOString()}] ${line}\n`;
  try {
    fs.appendFileSync(path.join(dir, 'desktop.log'), msg);
  } catch {
    /* ignore */
  }
}

function logStream(name) {
  if (!state.logStreams[name]) {
    const dir = cfg.ensureRuntimeDir();
    state.logStreams[name] = fs.createWriteStream(path.join(dir, `${name}.log`), { flags: 'a' });
  }
  return state.logStreams[name];
}

function pidFile(name) {
  return path.join(cfg.runtimeDir(), `${name}.pid`);
}

function writePid(name, pid) {
  try {
    fs.writeFileSync(pidFile(name), String(pid), 'ascii');
  } catch {
    /* ignore */
  }
}

function removePid(name) {
  try {
    fs.rmSync(pidFile(name), { force: true });
  } catch {
    /* ignore */
  }
}

function pidAlive(pid) {
  if (!pid) return false;
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === 'EPERM';
  }
}

/** Remove PID files whose process is no longer running. */
function cleanupStalePids() {
  for (const name of ['backend', 'ollama', 'frontend']) {
    const f = pidFile(name);
    if (!fs.existsSync(f)) continue;
    const raw = (fs.readFileSync(f, 'utf8') || '').trim();
    const pid = Number(raw);
    if (!raw || Number.isNaN(pid) || !pidAlive(pid)) {
      removePid(name);
      log(`Removed stale PID file: ${name}`);
    }
  }
}

// ── Ollama ────────────────────────────────────────────────────
async function inspectOllama() {
  const exe = cfg.resolveOllama();
  const res = await httpGet(cfg.OLLAMA_TAGS_URL, 2500);
  let models = [];
  if (res.ok) {
    try {
      models = (JSON.parse(res.body).models || []).map((m) => m.name);
    } catch {
      models = [];
    }
  }
  const base = cfg.OLLAMA_MODEL.split(':')[0];
  const modelInstalled = models.some((m) => m === cfg.OLLAMA_MODEL || m.split(':')[0] === base);
  return {
    installed: Boolean(exe),
    exe,
    reachable: res.ok,
    models,
    model: cfg.OLLAMA_MODEL,
    modelInstalled,
  };
}

async function startOllamaIfNeeded(onProgress) {
  const info = await inspectOllama();
  if (info.reachable) {
    log('Ollama already reachable (not owned by desktop).');
    state.ollama.owned = false;
    return { ...info, started: false };
  }
  if (!info.installed) {
    log('Ollama is not installed — backend will run in simulated mode.');
    return { ...info, started: false, error: 'Ollama is not installed.' };
  }
  onProgress && onProgress('Starting Ollama…');
  log(`Starting ollama serve from ${info.exe}`);
  const child = spawn(info.exe, ['serve'], {
    cwd: cfg.projectRoot(),
    windowsHide: true,
    env: process.env,
  });
  const out = logStream('ollama');
  child.stdout.pipe(out);
  child.stderr.pipe(out);
  child.on('exit', (code) => log(`Ollama process exited (code ${code}).`));
  state.ollama.child = child;
  state.ollama.owned = true;
  state.ollama.pid = child.pid;
  writePid('ollama', child.pid);

  const ready = await waitForUrl(cfg.OLLAMA_TAGS_URL, { timeoutMs: 25000, intervalMs: 700 });
  const after = await inspectOllama();
  return { ...after, started: true, ready };
}

// ── Backend ───────────────────────────────────────────────────
async function startBackendIfNeeded(onProgress) {
  if (await isReachable(cfg.BACKEND_HEALTH_URL, 2000)) {
    log('Backend already healthy (not owned by desktop).');
    state.backend.owned = false;
    return { started: false, healthy: true };
  }

  const py = cfg.resolvePython();
  if (!py) {
    return {
      started: false,
      healthy: false,
      error: 'Python was not found. Install Python 3 or add a virtual environment to the project.',
    };
  }

  const root = cfg.projectRoot();
  const env = {
    ...process.env,
    CHHOTI_DON_RUNTIME_DIR: cfg.runtimeDir(),
    PYTHONIOENCODING: 'utf-8',
  };
  onProgress && onProgress('Starting backend…');
  log(`Starting backend: ${py.cmd} app.py (cwd=${root})`);
  const child = spawn(py.cmd, [...py.args, 'app.py'], {
    cwd: root,
    windowsHide: true,
    env,
  });
  const out = logStream('backend');
  child.stdout.pipe(out);
  child.stderr.pipe(out);
  child.on('exit', (code) => log(`Backend process exited (code ${code}).`));
  state.backend.child = child;
  state.backend.owned = true;
  state.backend.pid = child.pid;
  writePid('backend', child.pid);

  const healthy = await waitForUrl(cfg.BACKEND_HEALTH_URL, { timeoutMs: 60000, intervalMs: 600 });
  return { started: true, healthy, error: healthy ? null : 'Backend health check timed out. See runtime backend.log.' };
}

// ── Orchestration ─────────────────────────────────────────────
async function startAll(onProgress) {
  cleanupStalePids();
  const result = { ok: false, steps: [], errors: [], ollama: null, backend: null, model: cfg.OLLAMA_MODEL };

  // 1. Ollama (optional — the backend still runs in simulation without it).
  const ollama = await startOllamaIfNeeded(onProgress);
  result.ollama = ollama;
  result.steps.push({ service: 'ollama', reachable: ollama.reachable || ollama.ready, owned: state.ollama.owned });
  if (ollama.installed && !ollama.modelInstalled) {
    result.modelMissing = {
      model: cfg.OLLAMA_MODEL,
      pullCommand: `ollama pull ${cfg.OLLAMA_MODEL}`,
    };
    log(`Configured model missing: ${cfg.OLLAMA_MODEL}. Pull with: ollama pull ${cfg.OLLAMA_MODEL}`);
  }

  // 2. Backend (required).
  const backend = await startBackendIfNeeded(onProgress);
  result.backend = backend;
  result.steps.push({ service: 'backend', healthy: backend.healthy, owned: state.backend.owned });
  if (!backend.healthy) {
    result.errors.push({
      service: 'backend',
      reason: backend.error || 'Backend did not become healthy.',
      log: path.join(cfg.runtimeDir(), 'backend.log'),
    });
    return result;
  }

  result.ok = true;
  return result;
}

// ── Status ────────────────────────────────────────────────────
async function getStatus() {
  const backendHealthy = await isReachable(cfg.BACKEND_HEALTH_URL, 1500);
  const ollama = await inspectOllama();
  return {
    backend: { healthy: backendHealthy, owned: state.backend.owned, pid: state.backend.pid },
    ollama: {
      reachable: ollama.reachable,
      installed: ollama.installed,
      owned: state.ollama.owned,
      model: ollama.model,
      modelInstalled: ollama.modelInstalled,
    },
    runtimeDir: cfg.runtimeDir(),
  };
}

// ── Termination ───────────────────────────────────────────────
function forceKillTree(pid) {
  return new Promise((resolve) => {
    if (!pid) return resolve();
    if (process.platform === 'win32') {
      execFile('taskkill', ['/PID', String(pid), '/T', '/F'], () => resolve());
    } else {
      try {
        process.kill(pid, 'SIGKILL');
      } catch {
        /* ignore */
      }
      resolve();
    }
  });
}

async function stopOne(name, { graceMs = 4000 } = {}) {
  const s = state[name];
  if (!s || !s.owned || !s.pid) {
    // Nothing owned; still clean any stale PID file we might have written.
    return;
  }
  const pid = s.pid;
  log(`Stopping owned ${name} (PID ${pid})…`);
  // Graceful first.
  try {
    if (s.child) s.child.kill('SIGTERM');
    else process.kill(pid, 'SIGTERM');
  } catch {
    /* already gone */
  }
  const gone = await new Promise((resolve) => {
    const deadline = Date.now() + graceMs;
    const tick = () => {
      if (!pidAlive(pid)) return resolve(true);
      if (Date.now() > deadline) return resolve(false);
      setTimeout(tick, 250);
    };
    tick();
  });
  if (!gone) {
    log(`${name} did not exit gracefully; forcing.`);
    await forceKillTree(pid);
  }
  removePid(name);
  s.child = null;
  s.owned = false;
  s.pid = null;
}

async function stopOwned({ keepOllama = false } = {}) {
  await stopOne('backend');
  if (!keepOllama) {
    await stopOne('ollama');
  } else if (state.ollama.owned) {
    log('Keeping Ollama running per user preference.');
  }
  for (const name of Object.keys(state.logStreams)) {
    try {
      state.logStreams[name].end();
    } catch {
      /* ignore */
    }
  }
  state.logStreams = {};
}

module.exports = {
  startAll,
  getStatus,
  stopOwned,
  inspectOllama,
  cleanupStalePids,
  ownsOllama: () => state.ollama.owned,
};
