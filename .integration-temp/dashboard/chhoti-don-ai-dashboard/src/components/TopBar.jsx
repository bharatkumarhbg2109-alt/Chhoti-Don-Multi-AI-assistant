import React from 'react';
import Icon from './Icon';

export default function TopBar({ onOpenSidebar }) {
  return (
    <header className="flex h-16 shrink-0 items-center justify-between border-b border-white/[0.06] px-3 sm:px-5">
      <div className="flex items-center gap-3">
        <button type="button" onClick={onOpenSidebar} className="icon-button lg:hidden" aria-label="Open menu">
          <Icon name="menu" />
        </button>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-sm font-semibold text-white sm:text-base">CHHOTI DON Assistant</h1>
            <span className="hidden rounded-full border border-rose-300/20 bg-rose-400/10 px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.18em] text-rose-200 sm:inline-flex">
              Live
            </span>
          </div>
          <p className="mt-0.5 hidden text-[11px] text-slate-500 sm:block">
            Personal, context-aware, and ready to help
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-1.5 text-[11px] text-slate-400 md:flex">
          <Icon name="shield" className="h-3.5 w-3.5 text-rose-300" />
          Private mode
        </div>
        <button type="button" className="icon-button" aria-label="Toggle appearance">
          <Icon name="sun" className="h-[18px] w-[18px]" />
        </button>
        <button type="button" className="icon-button" aria-label="Settings">
          <Icon name="settings" className="h-[18px] w-[18px]" />
        </button>
      </div>
    </header>
  );
}
