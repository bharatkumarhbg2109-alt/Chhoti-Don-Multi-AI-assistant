import React, { useCallback, useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { TONE_DOT } from '../services/status';
import { getCyberStatus, getHealingStatus, getLog, isDesktop } from '../services/chatApi';
import { useToast } from '../context/ToastContext';

function Row({ label, value, tone = 'muted', detail }) {
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

const LOG_NAMES = ['desktop', 'backend', 'frontend', 'ollama', 'launcher'];

export default function SystemStatusView({ status, backendOnline, onRefreshStatus }) {
  const { notify } = useToast();
  const [cyber, setCyber] = useState(null);
  const [heal, setHeal] = useState(null);
  const [logName, setLogName] = useState('backend');
  const [logLines, setLogLines] = useState([]);
  const [logLoading, setLogLoading] = useState(false);
  const [restarting, setRestarting] = useState(false);
  const desktop = isDesktop();
  const logEndRef = useRef(null);

  const loadExtras = useCallback(() => {
    getCyberStatus().then(setCyber).catch(() => setCyber(null));
    getHealingStatus().then(setHeal).catch(() => setHeal(null));
  }, []);

  useEffect(() => {
    loadExtras();
  }, [loadExtras]);

  const loadLog = useCallback((name) => {
    setLogLoading(true);
    getLog(name)
      .then((d) => setLogLines(d?.lines || []))
      .catch(() => setLogLines(['(log unavailable)']))
      .finally(() => setLogLoading(false));
  }, []);

  useEffect(() => {
    loadLog(logName);
  }, [logName, loadLog]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ block: 'nearest' });
  }, [logLines]);

  const handleRefresh = () => {
    onRefreshStatus?.();
    loadExtras();
    loadLog(logName);
  };

  const handleRestart = async () => {
    if (!desktop || !window.chhotiDon?.restartServices) {
      notify('Service restart is available in the desktop app.');
      return;
    }
    if (!window.confirm('Restart CHHOTI DON background services (backend / Ollama)?')) return;
    setRestarting(true);
    try {
      const res = await window.chhotiDon.restartServices();
      notify(res?.ok ? 'Services restarting…' : `Restart failed: ${res?.error || 'unknown error'}`);
      setTimeout(handleRefresh, 2500);
    } catch (e) {
      notify(`Restart failed: ${e?.message || e}`);
    } finally {
      setRestarting(false);
    }
  };

  const db = status?.database;
  const model = status?.model || 'unknown';
  const modelTone = status?.model_available ? 'ok' : 'warn';

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-rose-200/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20 shadow-brand">
            <Icon name="cpu" className="h-5 w-5 text-rose-100" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-white">System Status</h2>
            <p className="text-[11px] text-slate-500">Live health of the desktop shell and local services</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleRefresh}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-slate-300 transition hover:border-rose-300/20 hover:bg-rose-300/[0.055] hover:text-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
          >
            <Icon name="refresh" className="h-4 w-4" />
            Refresh
          </button>
          <button
            type="button"
            onClick={handleRestart}
            disabled={restarting}
            title={desktop ? 'Restart background services' : 'Available in the desktop app'}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-slate-300 transition hover:border-rose-300/20 hover:bg-rose-300/[0.055] hover:text-rose-100 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
          >
            <Icon name="history" className={`h-4 w-4 ${restarting ? 'animate-orb-spin' : ''}`} />
            Restart services
          </button>
        </div>
      </div>

      <div className="space-y-2">
        <Row
          label="Desktop shell"
          value={desktop ? 'Running' : 'Browser'}
          tone={desktop ? 'ok' : 'muted'}
          detail={desktop ? 'Native Electron window' : 'Opened in a web browser'}
        />
        <Row
          label="Backend"
          value={backendOnline === false ? 'Offline' : backendOnline ? 'Online' : 'Checking…'}
          tone={backendOnline === false ? 'error' : backendOnline ? 'ok' : 'muted'}
          detail="Flask API · 127.0.0.1:8000"
        />
        <Row
          label="Ollama"
          value={status?.ollama ? 'Online' : 'Offline'}
          tone={status?.ollama ? 'ok' : 'warn'}
          detail={`Local model provider · ${status?.provider || 'ollama'}`}
        />
        <Row
          label="Configured model"
          value={status?.model_available ? 'Installed' : 'Missing'}
          tone={modelTone}
          detail={model}
        />
        <Row
          label="AI mode"
          value={status?.simulated ? 'Simulated' : status?.ai_online ? 'Live' : '—'}
          tone={status?.simulated ? 'warn' : status?.ai_online ? 'ok' : 'muted'}
          detail={status?.runtime_mode ? `runtime: ${status.runtime_mode}` : undefined}
        />
        <Row
          label="Database"
          value={db?.exists ? `${db.conversations} chats` : 'Not created'}
          tone={db?.exists ? 'ok' : 'muted'}
          detail={db ? `${db.messages} messages · SQLite` : 'Conversation history store'}
        />
        <Row
          label="Cyber Engine"
          value={cyber?.available ? 'Ready' : cyber ? 'Unavailable' : 'Checking…'}
          tone={cyber?.available ? 'ok' : cyber ? 'warn' : 'muted'}
          detail={cyber?.version || 'Defensive posture (read-only)'}
        />
        <Row
          label="Self-Healing"
          value={heal?.available ? 'Ready' : heal ? 'Unavailable' : 'Checking…'}
          tone={heal?.available ? 'ok' : heal ? 'warn' : 'muted'}
          detail="Code intelligence (read-only analysis)"
        />
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Runtime logs</h3>
          <div className="flex items-center gap-1 rounded-xl border border-white/10 bg-white/[0.03] p-1">
            {LOG_NAMES.map((n) => (
              <button
                key={n}
                type="button"
                onClick={() => setLogName(n)}
                className={`rounded-lg px-2.5 py-1 text-[11px] transition ${
                  logName === n ? 'bg-rose-400/20 text-rose-100' : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {n}
              </button>
            ))}
          </div>
        </div>
        <div className="scrollbar-subtle max-h-64 overflow-y-auto rounded-2xl border border-white/[0.07] bg-[#08060d]/80 p-3 font-mono text-[11px] leading-5 text-slate-400">
          {logLoading && <p className="text-slate-600">Loading…</p>}
          {!logLoading && logLines.length === 0 && <p className="text-slate-600">No log entries.</p>}
          {!logLoading &&
            logLines.map((line, i) => (
              <div key={i} className="whitespace-pre-wrap break-words">
                {line || ' '}
              </div>
            ))}
          <div ref={logEndRef} />
        </div>
      </div>
    </div>
  );
}
