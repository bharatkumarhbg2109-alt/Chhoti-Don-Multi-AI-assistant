/**
 * Chat API Service — connects the React dashboard to the Chhoti Don Flask backend.
 * All requests go through the Vite dev-server proxy (/api → http://127.0.0.1:8000).
 */

const configuredBase = String(import.meta.env.VITE_API_BASE_URL || '/api').replace(/\/$/, '');
const API_BASE = configuredBase.endsWith('/api') ? configuredBase : `${configuredBase}/api`;

const CHAT_TIMEOUT = 60000; // ms
const QUICK_TIMEOUT = 8000; // ms (health/status/memory)

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

/**
 * Combine an optional external AbortSignal with a timeout into one signal.
 * Returns the merged signal, a cleanup fn, and a flag object recording whether
 * the timeout (not the caller) fired.
 */
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

/**
 * Perform a fetch with timeout + typed error classification.
 * Throws AbortError (name preserved) when the CALLER aborts, so callers can
 * silently ignore cancellations (e.g. switching conversations).
 */
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
    // Caller-initiated cancellation → re-throw as AbortError (name preserved).
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
    const msg = (data && (data.response || data.error)) || `Server error ${res.status}`;
    throw new ApiError(msg, res.status >= 500 ? 'server' : 'http', res.status);
  }
  if (parseFailed) {
    throw new ApiError('Received an invalid response from the server.', 'parse', res.status);
  }
  return data;
}

/**
 * Send a chat message to the backend.
 * @param {string} message  - The user's message text.
 * @param {string} [tool]   - Optional tool hint (e.g. "coder", "recon", "chat").
 * @param {AbortSignal} [signal] - Optional abort signal to cancel the request.
 */
export function sendMessage(message, tool = 'chat', signal) {
  return request('/chat', { method: 'POST', body: { message, tool }, signal, timeout: CHAT_TIMEOUT });
}

/** Lightweight health check. */
export function checkHealth(signal) {
  return request('/health', { signal });
}

/** Extended status: provider mode, model availability, simulated fallback. */
export function getStatus(signal) {
  return request('/status', { signal });
}

/** Conversation memory stored on the backend. */
export function getMemory(signal) {
  return request('/memory', { signal });
}

/** Clear conversation memory on the backend. */
export function resetMemory(signal) {
  return request('/reset', { method: 'POST', signal });
}
