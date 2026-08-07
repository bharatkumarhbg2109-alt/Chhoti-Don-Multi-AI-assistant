import React, { useCallback, useEffect, useState } from 'react';
import Icon from './Icon';
import { getHealingStatus, runHealingAnalyze } from '../services/chatApi';
import { useToast } from '../context/ToastContext';

export default function HealingView() {
  const { notify } = useToast();
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [analyzing, setAnalyzing] = useState(false);
  const [analysis, setAnalysis] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    getHealingStatus()
      .then((s) => {
        setStatus(s);
        if (s?.last_analysis) setAnalysis(s.last_analysis);
      })
      .catch((e) => setError(e?.message || 'Failed to load self-healing status.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runAnalyze = async () => {
    setAnalyzing(true);
    try {
      const res = await runHealingAnalyze();
      setAnalysis(res);
      notify(`Analysis complete · ${res.files_analyzed} files scanned.`);
    } catch (e) {
      notify(`Analysis failed: ${e?.message || e}`);
    } finally {
      setAnalyzing(false);
    }
  };

  const health = analysis?.health;
  const issues = analysis?.issues || [];

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20 shadow-brand">
            <Icon name="pulse" className="h-5 w-5 text-brand-100" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-white">Self-Healing</h2>
            <p className="text-[11px] text-slate-500">Read-only code intelligence · applying fixes stays manual for safety</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={load}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-slate-300 transition hover:border-brand-300/20 hover:bg-brand-300/[0.055] hover:text-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
          >
            <Icon name="refresh" className="h-4 w-4" />
            Refresh
          </button>
          <button
            type="button"
            onClick={runAnalyze}
            disabled={analyzing || (status && !status.available)}
            className="flex items-center gap-2 rounded-xl border border-brand-300/25 bg-brand-400/15 px-3 py-2 text-xs text-brand-50 transition hover:bg-brand-400/25 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
          >
            <Icon name="pulse" className={`h-4 w-4 ${analyzing ? 'animate-orb-spin' : ''}`} />
            {analyzing ? 'Analyzing…' : 'Run analysis'}
          </button>
        </div>
      </div>

      {loading && (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.03]" />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="rounded-2xl border border-brand-mist-400/25 bg-brand-mist-500/[0.1] p-5 text-center">
          <Icon name="shield" className="mx-auto h-6 w-6 text-brand-mist-300" />
          <p className="mt-2 text-sm text-brand-mist-100">{error}</p>
          <button type="button" onClick={load} className="mt-3 rounded-xl border border-brand-mist-400/30 px-3 py-1.5 text-xs text-brand-mist-100 transition hover:bg-brand-mist-300/[0.12]">
            Try again
          </button>
        </div>
      )}

      {!loading && !error && (
        <div className="space-y-4">
          <div className="grid grid-cols-3 gap-3">
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 text-center">
              <p className="text-2xl font-semibold text-white">{analysis?.files_analyzed ?? '—'}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">Files analyzed</p>
            </div>
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 text-center">
              <p className="text-2xl font-semibold text-white">{analysis?.issues_found ?? '—'}</p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">Issues found</p>
            </div>
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4 text-center">
              <p className="text-2xl font-semibold text-white">
                {health?.health_score ?? health?.score ?? (analysis ? '✓' : '—')}
              </p>
              <p className="mt-1 text-[10px] uppercase tracking-wide text-slate-500">Health</p>
            </div>
          </div>

          {analysis?.timestamp && (
            <p className="text-[11px] text-slate-500">
              Last analysis: {analysis.timestamp} · {analysis.duration_sec}s · read-only
            </p>
          )}

          {issues.length > 0 && (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
              <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Detected issues</h3>
              <ul className="scrollbar-subtle max-h-72 space-y-2 overflow-y-auto">
                {issues.map((it, i) => (
                  <li key={i} className="rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2 text-[11px]">
                    <span className="rounded bg-brand-mist-400/15 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-brand-mist-200">
                      {it.type || it.category || 'issue'}
                    </span>
                    <span className="ml-2 text-slate-300">{it.message || it.detail || it.description || JSON.stringify(it).slice(0, 140)}</span>
                    {it.file && <span className="mt-0.5 block text-[10px] text-slate-600">{it.file}{it.line ? `:${it.line}` : ''}</span>}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {analysis && issues.length === 0 && (
            <div className="rounded-2xl border border-emerald-300/20 bg-emerald-400/[0.06] p-5 text-center">
              <Icon name="shield" className="mx-auto h-6 w-6 text-emerald-300" />
              <p className="mt-2 text-sm text-emerald-100">No issues detected in the last analysis.</p>
            </div>
          )}

          {/* Apply-fix is intentionally gated: mutating code requires manual review. */}
          <div className="rounded-2xl border border-white/[0.07] bg-white/[0.02] p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-slate-200">Apply suggested fix</p>
                <p className="mt-0.5 text-[11px] leading-4 text-slate-500">
                  {status?.apply_note || 'Applying code fixes modifies files and requires explicit review; it is not automated from the desktop UI.'}
                </p>
              </div>
              <button
                type="button"
                disabled
                title="Disabled for safety — apply fixes via the CLI self-heal tool after review"
                className="shrink-0 cursor-not-allowed rounded-xl border border-white/10 bg-white/[0.03] px-3 py-2 text-xs text-slate-500"
              >
                Manual only
              </button>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {(status?.read_only_modules || []).map((m) => (
                <span key={m} className="rounded-md border border-emerald-300/15 bg-emerald-400/[0.06] px-2 py-0.5 text-[10px] text-emerald-200/80">
                  {m} · read-only
                </span>
              ))}
              {(status?.mutating_modules || []).map((m) => (
                <span key={m} className="rounded-md border border-brand-mist-400/15 bg-brand-mist-400/[0.06] px-2 py-0.5 text-[10px] text-brand-mist-200/80">
                  {m} · mutating
                </span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
