import React from 'react';
import Icon from './Icon';
import { TONE_DOT } from '../services/status';

const VIEW_META = {
  assistant: { title: 'CHHOTI DON Assistant', subtitle: 'Personal, context-aware, and ready to help' },
  workspace: { title: 'Workspace', subtitle: 'Project & file integration — planned' },
  memory: { title: 'Memory', subtitle: 'Recent context held by the engine' },
  system: { title: 'System Status', subtitle: 'Desktop shell, backend, Ollama, model & database' },
  cyber: { title: 'Cyber Engine', subtitle: 'Read-only defensive posture & safety policy' },
  healing: { title: 'Self-Healing', subtitle: 'Read-only code intelligence & project health' },
};

export default function TopBar({
  onOpenSidebar,
  currentView = 'assistant',
  aiStatus,
  privateMode,
  desktop = false,
  onTogglePrivate,
  onOpenSettings,
  onThemeClick,
  theme = 'dark',
}) {
  const meta = VIEW_META[currentView] || VIEW_META.assistant;
  const status = aiStatus || { label: 'Checking…', tone: 'muted' };

  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/[0.06] px-3 sm:px-5">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onOpenSidebar} className="icon-button lg:hidden" aria-label="Open menu">
          <Icon name="menu" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-sm font-semibold text-white sm:text-base">{meta.title}</h1>
            <span
              className="hidden items-center gap-1.5 rounded-full border border-white/10 bg-white/[0.035] px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.16em] text-slate-300 sm:inline-flex"
              title={status.detail || status.label}
            >
              <span className={`h-1.5 w-1.5 rounded-full ${TONE_DOT[status.tone] || TONE_DOT.muted}`} />
              {status.label}
            </span>
          </div>
          <p className="mt-0.5 hidden text-[11px] text-slate-500 sm:block">{meta.subtitle}</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {desktop && (
          <span
            className="hidden items-center gap-1.5 rounded-full border border-emerald-300/25 bg-emerald-400/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-emerald-200 md:inline-flex"
            title="Running inside the CHHOTI DON desktop app"
          >
            <Icon name="desktop" className="h-3.5 w-3.5" />
            Desktop
          </span>
        )}
        <button
          type="button"
          onClick={onTogglePrivate}
          aria-pressed={privateMode}
          title={privateMode ? 'Private mode on — new messages are not saved locally' : 'Private mode off'}
          className={`hidden items-center gap-2 rounded-full border px-3 py-1.5 text-[11px] transition md:flex focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40 ${
            privateMode
              ? 'border-brand-300/30 bg-brand-400/15 text-brand-100'
              : 'border-white/10 bg-white/[0.035] text-slate-400 hover:text-slate-200'
          }`}
        >
          <Icon name="shield" className={`h-3.5 w-3.5 ${privateMode ? 'text-brand-300' : ''}`} />
          Private mode{privateMode ? ' · on' : ''}
        </button>
        <button type="button" onClick={onThemeClick} className="icon-button" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} appearance`}>
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} className="h-[18px] w-[18px]" />
        </button>
        <button type="button" onClick={onOpenSettings} className="icon-button" aria-label="Settings">
          <Icon name="settings" className="h-[18px] w-[18px]" />
        </button>
      </div>
    </header>
  );
}
