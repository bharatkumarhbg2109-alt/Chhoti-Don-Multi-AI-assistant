import React, { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { deriveAiStatus, TONE_DOT } from '../services/status';
import { useToast } from '../context/ToastContext';

function StatusRow({ label, value, tone = 'muted', detail }) {
  return (
    <div className="flex items-start justify-between gap-3 rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3">
      <div className="min-w-0">
        <p className="text-xs font-medium text-slate-300">{label}</p>
        {detail && <p className="mt-0.5 text-[11px] leading-4 text-slate-500">{detail}</p>}
      </div>
      <span className="flex shrink-0 items-center gap-2 text-xs text-slate-200">
        <span className={`h-2 w-2 rounded-full ${TONE_DOT[tone] || TONE_DOT.muted}`} />
        {value}
      </span>
    </div>
  );
}

function Toggle({ checked, onChange, label }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full border transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40 ${
        checked ? 'border-rose-300/40 bg-rose-400/30' : 'border-white/10 bg-white/[0.06]'
      }`}
      aria-label={label}
    >
      <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${checked ? 'translate-x-6' : 'translate-x-1'}`} />
    </button>
  );
}

/**
 * Settings modal. Shows live connection/provider/database status, safe local
 * preferences, and — inside the desktop shell — window & service controls.
 * Never exposes secrets or environment-variable values.
 */
export default function SettingsModal({
  open,
  onClose,
  status,
  backendOnline,
  desktop = false,
  onRefreshStatus,
  reduceMotion,
  onToggleReduceMotion,
  onClearMemory,
}) {
  const closeRef = useRef(null);
  const { notify } = useToast();
  const [quitOnClose, setQuitOnClose] = useState(false);

  useEffect(() => {
    if (!open) return undefined;
    closeRef.current?.focus();
    const onKey = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (open && desktop && window.chhotiDon?.getQuitOnClose) {
      window.chhotiDon.getQuitOnClose().then((v) => setQuitOnClose(Boolean(v))).catch(() => {});
    }
  }, [open, desktop]);

  if (!open) return null;

  const ai = deriveAiStatus(status, backendOnline);
  const backendTone = backendOnline === false ? 'error' : backendOnline ? 'ok' : 'muted';
  const backendLabel = backendOnline === false ? 'Offline' : backendOnline ? 'Online' : 'Checking…';
  const mode = status?.mode || (status?.simulated ? 'simulation' : '—');
  const db = status?.database;

  const handleQuitToggle = (v) => {
    setQuitOnClose(v);
    window.chhotiDon?.setQuitOnClose?.(v);
    notify(v ? 'The app will quit when the window closes.' : 'The window will minimise to the tray on close.');
  };

  const handleRestart = async () => {
    if (!window.chhotiDon?.restartServices) return;
    if (!window.confirm('Restart CHHOTI DON background services?')) return;
    try {
      const res = await window.chhotiDon.restartServices();
      notify(res?.ok ? 'Services restarting…' : `Restart failed: ${res?.error || 'unknown'}`);
    } catch (e) {
      notify(`Restart failed: ${e?.message || e}`);
    }
  };

  return (
    <div className="fixed inset-0 z-[150] flex items-center justify-center p-4" role="dialog" aria-modal="true" aria-label="Settings">
      <button type="button" aria-label="Close settings" onClick={onClose} className="absolute inset-0 bg-[#050308]/80 backdrop-blur-sm" />
      <div className="glass-panel relative z-10 w-full max-w-lg overflow-hidden rounded-[28px]">
        <div className="flex items-center justify-between border-b border-white/[0.06] px-5 py-4">
          <div className="flex items-center gap-3">
            <div className="grid h-9 w-9 place-items-center rounded-xl border border-rose-200/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20">
              <Icon name="settings" className="h-5 w-5 text-rose-100" />
            </div>
            <h2 className="font-display text-base font-semibold text-white">Settings</h2>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="icon-button" aria-label="Close settings">
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>

        <div className="scrollbar-subtle max-h-[70vh] space-y-5 overflow-y-auto p-5">
          <section>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">System status</h3>
              <button
                type="button"
                onClick={onRefreshStatus}
                className="flex items-center gap-1.5 text-[11px] text-slate-400 transition hover:text-rose-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
              >
                <Icon name="refresh" className="h-3.5 w-3.5" />
                Refresh
              </button>
            </div>
            <div className="space-y-2">
              <StatusRow label="Backend connection" value={backendLabel} tone={backendTone} detail="Flask API · port 8000" />
              <StatusRow label="AI provider" value={ai.label} tone={ai.tone} detail={ai.detail} />
              <StatusRow label="Operating mode" value={mode} tone={ai.tone} detail="api · local · simulation" />
              <StatusRow
                label="History database"
                value={db?.exists ? `${db.conversations} chats` : 'Empty'}
                tone={db?.exists ? 'ok' : 'muted'}
                detail={db ? `${db.messages} messages · SQLite` : 'Local conversation store'}
              />
            </div>
          </section>

          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Preferences</h3>
            <div className="flex items-center justify-between rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3">
              <div>
                <p className="text-xs font-medium text-slate-300">Reduce motion</p>
                <p className="mt-0.5 text-[11px] text-slate-500">Minimise animations and instant-reveal responses.</p>
              </div>
              <Toggle checked={reduceMotion} onChange={onToggleReduceMotion} label="Reduce motion" />
            </div>
          </section>

          {desktop && (
            <section>
              <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Desktop</h3>
              <div className="space-y-2">
                <div className="flex items-center justify-between rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3">
                  <div>
                    <p className="text-xs font-medium text-slate-300">Quit when window closes</p>
                    <p className="mt-0.5 text-[11px] text-slate-500">Off: closing minimises to the system tray.</p>
                  </div>
                  <Toggle checked={quitOnClose} onChange={handleQuitToggle} label="Quit when window closes" />
                </div>
                <div className="flex items-center justify-between rounded-2xl border border-white/[0.07] bg-white/[0.025] px-4 py-3">
                  <div>
                    <p className="text-xs font-medium text-slate-300">Background services</p>
                    <p className="mt-0.5 text-[11px] text-slate-500">Restart the backend / Ollama managed by this app.</p>
                  </div>
                  <button
                    type="button"
                    onClick={handleRestart}
                    className="shrink-0 rounded-xl border border-white/10 px-3 py-1.5 text-xs text-slate-200 transition hover:border-rose-300/25 hover:bg-rose-300/[0.08] focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
                  >
                    Restart
                  </button>
                </div>
              </div>
            </section>
          )}

          <section>
            <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Data</h3>
            <div className="flex items-center justify-between rounded-2xl border border-amber-400/20 bg-amber-500/[0.06] px-4 py-3">
              <div>
                <p className="text-xs font-medium text-amber-100">Clear short-term memory</p>
                <p className="mt-0.5 text-[11px] text-amber-200/70">Clears the assistant’s recent context. Saved conversations are kept.</p>
              </div>
              <button
                type="button"
                onClick={onClearMemory}
                className="shrink-0 rounded-xl border border-amber-400/30 px-3 py-1.5 text-xs text-amber-100 transition hover:bg-amber-300/[0.12] focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300/40"
              >
                Clear
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
