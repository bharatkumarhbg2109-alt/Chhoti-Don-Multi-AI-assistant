import React, { useCallback, useEffect, useState } from 'react';
import Icon from './Icon';
import { getCyberStatus, getCyberCapabilities, runCyberSafeAction } from '../services/chatApi';
import { useToast } from '../context/ToastContext';

export default function CyberView() {
  const { notify } = useToast();
  const [status, setStatus] = useState(null);
  const [caps, setCaps] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    setError('');
    Promise.all([getCyberStatus(), getCyberCapabilities()])
      .then(([s, c]) => {
        setStatus(s);
        setCaps(c);
      })
      .catch((e) => setError(e?.message || 'Failed to load cyber status.'))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const runLoopbackScan = async () => {
    if (!window.confirm('Run a loopback port check on 127.0.0.1 only? No external targets are contacted.')) return;
    setScanning(true);
    setScanError('');
    setScanResult(null);
    try {
      const res = await runCyberSafeAction('loopback_port_check', true);
      setScanResult(res);
      notify('Loopback port check complete.');
    } catch (e) {
      setScanError(e?.payload?.message || e?.message || 'Scan failed.');
    } finally {
      setScanning(false);
    }
  };

  const policy = status?.safety_policy || caps?.safety_policy;

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20 shadow-brand">
            <Icon name="shield" className="h-5 w-5 text-brand-100" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-white">Cyber Engine</h2>
            <p className="text-[11px] text-slate-500">Defensive, read-only posture · offensive tooling is not exposed</p>
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-slate-300 transition hover:border-brand-300/20 hover:bg-brand-300/[0.055] hover:text-brand-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
        >
          <Icon name="refresh" className="h-4 w-4" />
          Refresh
        </button>
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
          <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium text-slate-300">Engine</p>
              <span className={`flex items-center gap-2 text-xs ${status?.available ? 'text-emerald-200' : 'text-brand-mist-200'}`}>
                <span className={`h-2 w-2 rounded-full ${status?.available ? 'bg-emerald-300' : 'bg-brand-mist-300'}`} />
                {status?.available ? 'Ready' : 'Unavailable'}
              </span>
            </div>
            {status?.version && <p className="mt-1 text-[11px] text-slate-500">{status.version}</p>}
            {status?.note && <p className="mt-2 text-[11px] leading-4 text-slate-500">{status.note}</p>}
          </div>

          {policy && (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
              <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Safety policy</h3>
              <dl className="grid grid-cols-2 gap-3 text-[12px]">
                <div>
                  <dt className="text-slate-500">Lab mode</dt>
                  <dd className="text-slate-200">{policy.lab_mode ? 'On (private only)' : 'Off'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Guardian</dt>
                  <dd className="text-slate-200">{policy.guardian_enabled ? 'Enabled' : 'Disabled'}</dd>
                </div>
                <div>
                  <dt className="text-slate-500">Rate limit</dt>
                  <dd className="text-slate-200">
                    {policy.max_scans_per_window ?? '—'} / {policy.rate_limit_window ?? '—'}s
                  </dd>
                </div>
                <div>
                  <dt className="text-slate-500">Allowed ranges</dt>
                  <dd className="text-slate-200">{(policy.allowed_ranges || []).length} private CIDRs</dd>
                </div>
              </dl>
              {policy.allowed_ranges?.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-1.5">
                  {policy.allowed_ranges.map((r) => (
                    <span key={r} className="rounded-md border border-white/10 bg-white/[0.04] px-2 py-0.5 text-[10px] text-slate-400">
                      {r}
                    </span>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Safe active action: loopback-only port check */}
          <div className="rounded-2xl border border-brand-300/15 bg-gradient-to-br from-brand-400/[0.06] to-transparent p-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-sm font-medium text-white">Loopback port check</p>
                <p className="mt-0.5 text-[11px] leading-4 text-slate-400">
                  Checks common ports on <span className="text-brand-200">127.0.0.1</span> only. Requires confirmation; no external targets are permitted.
                </p>
              </div>
              <button
                type="button"
                onClick={runLoopbackScan}
                disabled={scanning}
                className="shrink-0 rounded-xl border border-brand-300/25 bg-brand-400/15 px-3 py-2 text-xs text-brand-50 transition hover:bg-brand-400/25 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
              >
                {scanning ? 'Scanning…' : 'Run check'}
              </button>
            </div>

            {scanError && <p className="mt-3 rounded-lg border border-brand-mist-400/25 bg-brand-mist-500/[0.1] px-3 py-2 text-[11px] text-brand-mist-100">{scanError}</p>}

            {scanResult && (
              <div className="mt-3 rounded-xl border border-white/[0.07] bg-[#031716]/60 p-3">
                <p className="text-[11px] text-slate-500">
                  Target {scanResult.target} · checked {scanResult.checked_ports?.length} ports
                </p>
                {scanResult.open_ports?.length ? (
                  <ul className="mt-2 flex flex-wrap gap-1.5">
                    {scanResult.open_ports.map((p) => (
                      <li key={p.port} className="rounded-md border border-emerald-300/20 bg-emerald-400/10 px-2 py-0.5 text-[11px] text-emerald-100">
                        {p.port} · {p.service}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="mt-2 text-[11px] text-slate-400">No listening ports found on loopback.</p>
                )}
              </div>
            )}
          </div>

          {caps?.capabilities && (
            <div className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
              <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Available capabilities</h3>
              <ul className="space-y-2">
                {caps.capabilities.map((c) => (
                  <li key={c.id} className="flex items-start gap-3 rounded-xl border border-white/[0.05] bg-white/[0.02] px-3 py-2">
                    <Icon name={c.active ? 'pulse' : 'shield'} className="mt-0.5 h-4 w-4 text-brand-200" />
                    <div className="min-w-0">
                      <p className="text-xs text-slate-200">
                        {c.name}
                        {c.active && <span className="ml-2 rounded bg-brand-400/15 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-brand-200">active</span>}
                        {!c.active && <span className="ml-2 rounded bg-white/5 px-1.5 py-0.5 text-[9px] uppercase tracking-wide text-slate-400">read-only</span>}
                      </p>
                      <p className="mt-0.5 text-[11px] leading-4 text-slate-500">{c.description}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
