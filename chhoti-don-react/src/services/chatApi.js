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
  const { tool = 'chat', conversationId, isPrivate = false, persistUser = true, signal } = opts;
  return request('/chat', {
    method: 'POST',
    body: {
      message,
      tool,
      conversation_id: conversationId || null,
      private: isPrivate,
      persist_user: persistUser,
    },
    signal,
    timeout: CHAT_TIMEOUT,
  });
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
