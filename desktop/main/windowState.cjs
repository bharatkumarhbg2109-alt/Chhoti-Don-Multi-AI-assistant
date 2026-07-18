'use strict';

/**
 * Persist and restore the main window's size/position across restarts.
 * Stored as JSON in the writable runtime directory.
 */

const fs = require('fs');
const path = require('path');
const { screen } = require('electron');
const cfg = require('./config.cjs');

function stateFile() {
  return path.join(cfg.runtimeDir(), 'window-state.json');
}

const DEFAULTS = { width: 1200, height: 820 };

function load() {
  try {
    const raw = fs.readFileSync(stateFile(), 'utf8');
    const s = JSON.parse(raw);
    if (s && Number.isFinite(s.width) && Number.isFinite(s.height)) {
      return sanitize(s);
    }
  } catch {
    /* fall through to defaults */
  }
  return { ...DEFAULTS };
}

/** Keep the window on a currently-connected display. */
function sanitize(s) {
  try {
    const area = screen.getPrimaryDisplay().workArea;
    const width = Math.min(Math.max(s.width, 640), area.width);
    const height = Math.min(Math.max(s.height, 480), area.height);
    const out = { width, height };
    if (Number.isFinite(s.x) && Number.isFinite(s.y)) {
      const displays = screen.getAllDisplays();
      const visible = displays.some((d) => {
        const b = d.bounds;
        return s.x < b.x + b.width && s.x + width > b.x && s.y < b.y + b.height && s.y + height > b.y;
      });
      if (visible) {
        out.x = s.x;
        out.y = s.y;
      }
    }
    return out;
  } catch {
    return { width: s.width, height: s.height };
  }
}

function bind(win) {
  const save = () => {
    if (win.isDestroyed() || win.isMinimized()) return;
    try {
      const b = win.getBounds();
      fs.mkdirSync(cfg.runtimeDir(), { recursive: true });
      fs.writeFileSync(stateFile(), JSON.stringify(b));
    } catch {
      /* ignore */
    }
  };
  let t = null;
  const debounced = () => {
    clearTimeout(t);
    t = setTimeout(save, 400);
  };
  win.on('resize', debounced);
  win.on('move', debounced);
  win.on('close', save);
}

module.exports = { load, bind };
