'use strict';

/**
 * Lightweight HTTP health helpers (no external dependencies).
 */

const http = require('http');

/** GET a URL, resolving { ok, status, body } and never rejecting. */
function httpGet(url, timeoutMs = 3000) {
  return new Promise((resolve) => {
    let done = false;
    const finish = (result) => {
      if (!done) {
        done = true;
        resolve(result);
      }
    };
    try {
      const req = http.get(url, (res) => {
        let data = '';
        res.on('data', (chunk) => {
          data += chunk;
        });
        res.on('end', () => finish({ ok: res.statusCode >= 200 && res.statusCode < 400, status: res.statusCode, body: data }));
      });
      req.setTimeout(timeoutMs, () => {
        req.destroy();
        finish({ ok: false, status: 0, body: '' });
      });
      req.on('error', () => finish({ ok: false, status: 0, body: '' }));
    } catch {
      finish({ ok: false, status: 0, body: '' });
    }
  });
}

/** True when the URL responds with a 2xx/3xx within the timeout. */
async function isReachable(url, timeoutMs = 3000) {
  const res = await httpGet(url, timeoutMs);
  return res.ok;
}

/** Poll until reachable or the deadline passes. */
async function waitForUrl(url, { timeoutMs = 60000, intervalMs = 500, onTick } = {}) {
  const deadline = Date.now() + timeoutMs;
  let attempt = 0;
  while (Date.now() < deadline) {
    attempt += 1;
    if (await isReachable(url, Math.min(intervalMs + 1500, 3000))) return true;
    if (onTick) onTick(attempt);
    await new Promise((r) => setTimeout(r, intervalMs));
  }
  return false;
}

module.exports = { httpGet, isReachable, waitForUrl };
