/**
 * Chat API Service — connects the React dashboard to the Chhoti Don Flask backend.
 *
 * Origin handling:
 *   - Vite dev server proxies /api → http://127.0.0.1:8000.
 *   - The packaged desktop shell loads the app same-origin FROM the backend
 *     (http://127.0.0.1:8000), so relative /api also works there.
 *   - An explicit VITE_API_BASE_URL or window.__CHHOTI_DON_API_BASE overrides both.
 */

function resolveBase() {
  if (typeof window !== 'undefined' && window.__CHHOTI_DON_API_BASE) {
    return String(window.__CHHOTI_DON_API_BASE).replace(/\/$/, '');
  }
  const configured = String(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
  return configured.endsWith('/api') ? configured : `${configured}/api`;
}

const API_BASE = resolveBase();

const CHAT_TIMEOUT = 120000; // ms
const QUICK_TIMEOUT = 8000; // ms (health/status/memory)
const ACTION_TIMEOUT = 30000; // ms (analyze, safe-action)

/** True when running inside the Electron desktop shell (preload bridge present). */
export const isDesktop = () =>
  typeof window !== 'undefined' && Boolean(window.chhotiDon?.isDesktop);

/**
 * Typed API error so the UI can distinguish failure kinds.
 * kind: 'network' | 'timeout' | 'http' | 'server' | 'parse'
 */
export class ApiError extends Error {
  constructor(message, kind, status) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
  }
}

function withTimeout(externalSignal, timeoutMs) {
  const controller = new AbortController();
  const state = { timedOut: false };
  const timer = window.setTimeout(() => {
    state.timedOut = true;
    controller.abort();
  }, timeoutMs);

  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) controller.abort();
    else externalSignal.addEventListener('abort', onExternalAbort, { once: true });
  }
  const cleanup = () => {
    window.clearTimeout(timer);
    externalSignal?.removeEventListener('abort', onExternalAbort);
  };
  return { signal: controller.signal, state, cleanup };
}

async function request(path, { method = 'GET', body, signal, timeout = QUICK_TIMEOUT } = {}) {
  const { signal: merged, state, cleanup } = withTimeout(signal, timeout);

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: body ? { 'Content-Type': 'application/json' } : undefined,
      body: body ? JSON.stringify(body) : undefined,
      signal: merged,
    });
  } catch (err) {
    cleanup();
    if (err?.name === 'AbortError' && !state.timedOut) {
      const abortErr = new Error('Request aborted');
      abortErr.name = 'AbortError';
      throw abortErr;
    }
    if (state.timedOut) {
      throw new ApiError('The request timed out. The backend may be busy or unreachable.', 'timeout');
    }
    throw new ApiError('Cannot reach the backend server. Is it running on port 8000?', 'network');
  }
  cleanup();

  let data = null;
  let parseFailed = false;
  try {
    const text = await res.text();
    data = text ? JSON.parse(text) : null;
  } catch {
    parseFailed = true;
  }

  if (!res.ok) {
    const msg = (data && (data.response || data.message || data.error)) || `Server error ${res.status}`;
    // Attach the parsed payload so callers can read structured "blocked" responses.
    const apiErr = new ApiError(msg, res.status >= 500 ? 'server' : 'http', res.status);
    apiErr.payload = data;
    throw apiErr;
  }
  if (parseFailed) {
    throw new ApiError('Received an invalid response from the server.', 'parse', res.status);
  }
  return data;
}

// ── Chat ──────────────────────────────────────────────────────
/**
 * Send a chat message to the backend.
 * @param {string} message
 * @param {object} [opts] - { tool, conversationId, isPrivate, persistUser, signal }
 */
export function sendMessage(message, opts = {}) {
  const { tool = 'chat', conversationId, isPrivate = false, persistUser = true, image, signal } = opts;
  const body = {
    message,
    tool,
    conversation_id: conversationId || null,
    private: isPrivate,
    persist_user: persistUser,
  };
  if (image) body.image = image; // base64/data-URL -> backend routes to vision
  return request('/chat', { method: 'POST', body, signal, timeout: CHAT_TIMEOUT });
}

// ── Voice: local STT / TTS (faster-whisper + Piper) ───────────
/** Send a recorded audio Blob to the backend and get a transcript. */
export async function transcribeAudio(blob, signal) {
  const form = new FormData();
  form.append('audio', blob, 'speech.webm');
  let res;
  try {
    res = await fetch(`${API_BASE}/voice/transcribe`, { method: 'POST', body: form, signal });
  } catch (err) {
    if (err?.name === 'AbortError') throw err;
    throw new ApiError('Cannot reach the backend for transcription.', 'network');
  }
  const data = await res.json().catch(() => null);
  if (!res.ok) throw new ApiError((data && data.message) || 'Transcription failed', 'server', res.status);
  return data; // { text, language, confidence, device }
}

/** Synthesize speech for text; resolves to an audio Blob (audio/wav). */
export async function speakText(text, signal) {
  const res = await fetch(`${API_BASE}/voice/speak`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ text }),
    signal,
  });
  if (!res.ok) throw new ApiError('Speech synthesis failed', 'server', res.status);
  return res.blob();
}

// ── Health / status / capabilities ────────────────────────────
export const checkHealth = (signal) => request('/health', { signal });
export const getStatus = (signal) => request('/status', { signal });
export const getCapabilities = (signal) => request('/capabilities', { signal });

// ── Memory ────────────────────────────────────────────────────
export const getMemory = (signal) => request('/memory', { signal });
export const searchMemory = (query, signal) =>
  request('/memory/search', { method: 'POST', body: { query }, signal });
export const resetMemory = (signal) => request('/reset', { method: 'POST', signal });

// ── Conversations (persistent history) ────────────────────────
export const listConversations = (query, signal) =>
  request(`/conversations${query ? `?q=${encodeURIComponent(query)}` : ''}`, { signal });
export const createConversation = (title, isPrivate = false, signal) =>
  request('/conversations', { method: 'POST', body: { title, private: isPrivate }, signal });
export const getConversation = (id, signal) =>
  request(`/conversations/${encodeURIComponent(id)}`, { signal });
export const patchConversation = (id, patch, signal) =>
  request(`/conversations/${encodeURIComponent(id)}`, { method: 'PATCH', body: patch, signal });
export const deleteConversation = (id, signal) =>
  request(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE', signal });
export const importConversations = (conversations, signal) =>
  request('/conversations/import', { method: 'POST', body: { conversations }, signal });

// ── Cyber Engine (safe, defensive) ────────────────────────────
export const getCyberStatus = (signal) => request('/cyber/status', { signal });
export const getCyberCapabilities = (signal) => request('/cyber/capabilities', { signal });
export const runCyberSafeAction = (action, confirm, signal) =>
  request('/cyber/run-safe-action', { method: 'POST', body: { action, confirm }, signal, timeout: ACTION_TIMEOUT });

// ── Self-Healing / Code Intelligence ──────────────────────────
export const getHealingStatus = (signal) => request('/self-healing/status', { signal });
export const runHealingAnalyze = (signal) =>
  request('/self-healing/analyze', { method: 'POST', body: {}, signal, timeout: ACTION_TIMEOUT });
export const getHealingReports = (signal) => request('/self-healing/reports', { signal });

// ── Logs ──────────────────────────────────────────────────────
export const getLog = (name, signal) => request(`/logs/${encodeURIComponent(name)}`, { signal });

// ── Workspace & Autonomous Coding Agent ──────────────────────
export const getWorkspaceStatus = (signal) => request('/workspace', { signal });
export const grantWorkspace = (path, signal) =>
  request('/workspace/grant', { method: 'POST', body: { path }, signal, timeout: ACTION_TIMEOUT });
export const revokeWorkspace = (signal) =>
  request('/workspace/revoke', { method: 'POST', signal });
export const getWorkspaceFiles = (path = '.', maxDepth = null, signal) => {
  const q = new URLSearchParams({ path });
  if (maxDepth !== null) q.append('max_depth', maxDepth);
  return request(`/workspace/files?${q.toString()}`, { signal });
};
export const getWorkspaceFile = (path, signal) =>
  request(`/workspace/file?path=${encodeURIComponent(path)}`, { signal });
export const getWorkspaceServers = (signal) => request('/workspace/servers', { signal });
export const stopWorkspaceServer = (id, signal) =>
  request('/workspace/servers/stop', { method: 'POST', body: { id }, signal });

export const startCodingBuild = (task, workspace = null, wait = 0, signal) =>
  request('/coding/build', { method: 'POST', body: { task, workspace, wait }, signal, timeout: CHAT_TIMEOUT });
export const pollCodingBuild = (sessionId, wait = 30, signal) =>
  request(`/coding/build/${encodeURIComponent(sessionId)}?wait=${wait}`, { signal, timeout: CHAT_TIMEOUT });
export const respondCodingBuild = (sessionId, approve, wait = 30, signal) =>
  request(`/coding/build/${encodeURIComponent(sessionId)}/respond`, {
    method: 'POST',
    body: { approve, wait },
    signal,
    timeout: CHAT_TIMEOUT,
  });
export const abortCodingBuild = (sessionId, signal) =>
  request(`/coding/build/${encodeURIComponent(sessionId)}/abort`, { method: 'POST', signal });

export const streamCodingBuild = (sessionId, { onEvent, onDone, onError } = {}) => {
  const url = `${API_BASE}/coding/build/${encodeURIComponent(sessionId)}/stream`;
  const es = new EventSource(url);

  const handlePayload = (dataStr) => {
    try {
      const payload = typeof dataStr === 'string' ? JSON.parse(dataStr) : dataStr;
      if (onEvent) onEvent(payload);
      const ev = payload?.event || payload?.status;
      if (ev === 'done' || ev === 'error' || ev === 'aborted') {
        es.close();
        if (onDone) onDone(payload);
      }
    } catch (err) {
      console.error('[streamCodingBuild] parse error:', err);
    }
  };

  const eventTypes = [
    'session_start', 'planning', 'plan', 'plan_failed', 'plan_rejected', 'plan_approved',
    'pending_plan', 'plan_response', 'step_start', 'action_start', 'action_complete',
    'diff', 'pending_confirmation', 'confirmation_response', 'finish', 'done', 'error', 'aborted'
  ];

  eventTypes.forEach((type) => {
    es.addEventListener(type, (e) => handlePayload(e.data));
  });

  es.onmessage = (e) => handlePayload(e.data);

  es.onerror = (err) => {
    console.warn('[streamCodingBuild] EventSource error or disconnect:', err);
    es.close();
    if (onError) onError(err);
  };

  return () => {
    es.close();
  };
};

