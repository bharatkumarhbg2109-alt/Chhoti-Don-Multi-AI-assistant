import React from 'react';
import Icon from './Icon';

const primaryNav = [
  { icon: 'chat', label: 'Assistant', active: true },
  { icon: 'grid', label: 'Workspace' },
  { icon: 'brain', label: 'Memory' },
];

const conversations = [
  { title: 'Product launch strategy', time: '2m' },
  { title: 'Build my study roadmap', time: '1h' },
  { title: 'Review React architecture', time: '3h' },
  { title: 'Daily productivity plan', time: '1d' },
];

export default function Sidebar({ open, onClose }) {
  return (
    <>
      <button
        type="button"
        aria-label="Close sidebar"
        onClick={onClose}
        className={`fixed inset-0 z-30 bg-[#050308]/80 backdrop-blur-sm transition-opacity lg:hidden ${
          open ? 'pointer-events-auto opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />

      <aside
        className={`glass-panel fixed inset-y-3 left-3 z-40 flex w-[290px] flex-col rounded-[28px] p-3 transition-transform duration-500 ease-out lg:static lg:inset-auto lg:z-auto lg:h-[calc(100vh-24px)] lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-[calc(100%+24px)]'
        }`}
      >
        <div className="flex items-center justify-between px-2 py-2">
          <div className="flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center rounded-2xl border border-rose-200/15 bg-gradient-to-br from-rose-400/25 via-fuchsia-500/20 to-violet-600/25 shadow-brand">
              <Icon name="sparkles" className="h-5 w-5 text-rose-100" />
              <span className="absolute inset-0 rounded-2xl border border-rose-300/15 animate-pulse-soft" />
              <span className="absolute -right-0.5 -top-0.5 h-2 w-2 rounded-full bg-amber-200 shadow-[0_0_12px_rgba(253,230,138,.8)]" />
            </div>
            <div>
              <p className="font-display text-sm font-semibold tracking-[0.15em] text-white">CHHOTI DON</p>
              <p className="text-[11px] text-slate-400">Private AI command center</p>
            </div>
          </div>
          <button type="button" onClick={onClose} className="icon-button lg:hidden" aria-label="Close menu">
            <Icon name="close" className="h-5 w-5" />
          </button>
        </div>

        <button
          type="button"
          className="group mt-4 flex items-center justify-center gap-2 rounded-2xl border border-rose-300/20 bg-gradient-to-r from-rose-500/20 via-fuchsia-500/15 to-violet-600/20 px-4 py-3 text-sm font-medium text-rose-50 shadow-brand transition duration-300 hover:scale-[1.02] hover:border-rose-200/40 hover:shadow-[0_0_42px_rgba(244,63,94,.20)]"
        >
          <Icon name="plus" className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
          New conversation
        </button>

        <nav className="mt-5 space-y-1" aria-label="Primary navigation">
          {primaryNav.map((item) => (
            <button
              type="button"
              key={item.label}
              className={`group flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition duration-300 ${
                item.active
                  ? 'border border-rose-200/10 bg-gradient-to-r from-rose-400/[0.09] to-fuchsia-500/[0.045] text-white shadow-[inset_0_1px_0_rgba(255,255,255,.05)]'
                  : 'border border-transparent text-slate-400 hover:border-white/5 hover:bg-white/[0.035] hover:text-slate-100'
              }`}
            >
              <Icon
                name={item.icon}
                className={`h-[18px] w-[18px] ${item.active ? 'text-rose-300' : 'group-hover:text-rose-300'}`}
              />
              <span>{item.label}</span>
              {item.active && (
                <span className="ml-auto h-1.5 w-1.5 rounded-full bg-rose-300 shadow-[0_0_12px_rgba(253,164,175,.95)]" />
              )}
            </button>
          ))}
        </nav>

        <div className="mt-6 flex items-center justify-between px-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Recent</p>
          <button type="button" className="text-slate-500 transition hover:text-rose-200" aria-label="Search history">
            <Icon name="search" className="h-4 w-4" />
          </button>
        </div>

        <div className="scrollbar-subtle mt-2 flex-1 space-y-1 overflow-y-auto pr-1">
          {conversations.map((conversation, index) => (
            <button
              type="button"
              key={conversation.title}
              className="group flex w-full items-center gap-3 rounded-2xl border border-transparent px-3 py-2.5 text-left transition duration-300 hover:border-rose-200/[0.07] hover:bg-rose-300/[0.035]"
            >
              <span
                className={`h-8 w-1 rounded-full ${
                  index === 0
                    ? 'bg-gradient-to-b from-rose-300 via-fuchsia-400 to-violet-500'
                    : 'bg-white/5 group-hover:bg-white/10'
                }`}
              />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium text-slate-300 group-hover:text-white">
                  {conversation.title}
                </span>
                <span className="mt-1 block text-[10px] text-slate-600">Chhoti Don intelligence</span>
              </span>
              <span className="text-[10px] text-slate-600">{conversation.time}</span>
            </button>
          ))}
        </div>

        <div className="mt-3 rounded-2xl border border-rose-200/10 bg-gradient-to-br from-white/[0.045] to-rose-400/[0.025] p-3">
          <div className="flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-rose-400/35 via-fuchsia-500/25 to-amber-300/20 text-sm font-semibold text-rose-50">
              BK
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#0b0710] bg-rose-300 shadow-[0_0_10px_rgba(253,164,175,.75)]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-white">Bharat Kumar</p>
              <p className="text-[10px] text-slate-500">Pro workspace</p>
            </div>
            <button type="button" className="text-slate-500 transition hover:text-white" aria-label="Account options">
              <Icon name="more" className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>
    </>
  );
}
