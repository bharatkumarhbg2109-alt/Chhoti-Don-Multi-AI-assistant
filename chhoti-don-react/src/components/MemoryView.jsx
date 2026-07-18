import React, { useCallback, useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import { getMemory, searchMemory } from '../services/chatApi';

/**
 * Backend conversation memory viewer (GET /api/memory + POST /api/memory/search).
 * Handles loading, success, empty, and error states with manual refresh, search
 * and a confirmed clear action.
 */
export default function MemoryView({ onClearMemory }) {
  const [state, setState] = useState('loading'); // loading | ready | empty | error
  const [entries, setEntries] = useState([]);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const abortRef = useRef(null);

  const load = useCallback((q = '') => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setState('loading');
    setError('');

    const req = q.trim()
      ? searchMemory(q.trim(), controller.signal).then((d) => d?.matches || [])
      : getMemory(controller.signal).then((d) => (Array.isArray(d?.memory) ? d.memory : []));

    req
      .then((memory) => {
        setEntries(memory);
        setState(memory.length ? 'ready' : 'empty');
      })
      .catch((err) => {
        if (err?.name === 'AbortError') return;
        setError(err?.message || 'Failed to load memory.');
        setState('error');
      });
  }, []);

  useEffect(() => {
    load();
    return () => abortRef.current?.abort();
  }, [load]);

  const onSearchSubmit = (e) => {
    e.preventDefault();
    load(query);
  };

  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-2xl border border-rose-200/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20 shadow-brand">
            <Icon name="brain" className="h-5 w-5 text-rose-100" />
          </div>
          <div>
            <h2 className="font-display text-base font-semibold text-white">Memory</h2>
            <p className="text-[11px] text-slate-500">Recent context held by the backend engine</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setQuery('');
              load();
            }}
            disabled={state === 'loading'}
            className="flex items-center gap-2 rounded-xl border border-white/10 bg-white/[0.035] px-3 py-2 text-xs text-slate-300 transition hover:border-rose-300/20 hover:bg-rose-300/[0.055] hover:text-rose-100 disabled:opacity-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
          >
            <Icon name="refresh" className={`h-4 w-4 ${state === 'loading' ? 'animate-orb-spin' : ''}`} />
            Refresh
          </button>
          {onClearMemory && (
            <button
              type="button"
              onClick={onClearMemory}
              className="flex items-center gap-2 rounded-xl border border-amber-400/25 bg-amber-500/[0.08] px-3 py-2 text-xs text-amber-100 transition hover:bg-amber-300/[0.14] focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300/40"
            >
              <Icon name="trash" className="h-4 w-4" />
              Clear
            </button>
          )}
        </div>
      </div>

      <form onSubmit={onSearchSubmit} className="mb-4 flex items-center gap-2">
        <div className="flex flex-1 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2">
          <Icon name="search" className="h-4 w-4 text-slate-500" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search memory…"
            className="flex-1 bg-transparent text-xs text-slate-200 outline-none placeholder:text-slate-600"
            aria-label="Search memory"
          />
        </div>
        <button
          type="submit"
          className="rounded-xl border border-rose-300/20 bg-rose-400/10 px-3 py-2 text-xs text-rose-100 transition hover:bg-rose-400/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
        >
          Search
        </button>
      </form>

      {state === 'loading' && (
        <div className="space-y-3" aria-busy="true">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-2xl border border-white/[0.06] bg-white/[0.03]" />
          ))}
        </div>
      )}

      {state === 'error' && (
        <div className="rounded-2xl border border-amber-400/25 bg-amber-500/[0.1] p-5 text-center">
          <Icon name="shield" className="mx-auto h-6 w-6 text-amber-300" />
          <p className="mt-2 text-sm text-amber-100">{error}</p>
          <button
            type="button"
            onClick={() => load(query)}
            className="mt-3 rounded-xl border border-amber-400/30 px-3 py-1.5 text-xs text-amber-100 transition hover:bg-amber-300/[0.12]"
          >
            Try again
          </button>
        </div>
      )}

      {state === 'empty' && (
        <div className="rounded-2xl border border-white/[0.06] bg-white/[0.02] p-8 text-center">
          <Icon name="brain" className="mx-auto h-7 w-7 text-slate-600" />
          <p className="mt-3 text-sm text-slate-400">{query.trim() ? 'No matching memory.' : 'No memory yet.'}</p>
          <p className="mt-1 text-xs text-slate-600">Start a conversation and the engine's recent context appears here.</p>
        </div>
      )}

      {state === 'ready' && (
        <ol className="space-y-2.5">
          {entries.map((entry, index) => {
            const role = entry.role || 'unknown';
            const isUser = role === 'user';
            return (
              <li
                key={`${entry.timestamp || index}-${index}`}
                className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-3.5"
              >
                <div className="mb-1.5 flex items-center gap-2">
                  <span
                    className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-[0.16em] ${
                      isUser ? 'bg-rose-400/15 text-rose-200' : 'bg-fuchsia-400/15 text-fuchsia-200'
                    }`}
                  >
                    {role}
                  </span>
                  {entry.timestamp && (
                    <span className="text-[10px] text-slate-600">{String(entry.timestamp).replace('T', ' ').slice(0, 19)}</span>
                  )}
                </div>
                <p className="whitespace-pre-wrap break-words text-[13px] leading-6 text-slate-300">
                  {String(entry.content ?? '')}
                </p>
              </li>
            );
          })}
        </ol>
      )}
    </div>
  );
}
