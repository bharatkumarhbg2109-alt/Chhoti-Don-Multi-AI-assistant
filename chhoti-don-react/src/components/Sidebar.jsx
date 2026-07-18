import React, { useEffect, useRef, useState } from 'react';
import Icon from './Icon';

const primaryNav = [
  { view: 'assistant', icon: 'chat', label: 'Assistant' },
  { view: 'workspace', icon: 'grid', label: 'Workspace' },
  { view: 'memory', icon: 'brain', label: 'Memory' },
];

const systemNav = [
  { view: 'system', icon: 'cpu', label: 'System Status' },
  { view: 'cyber', icon: 'shield', label: 'Cyber Engine' },
  { view: 'healing', icon: 'pulse', label: 'Self-Healing' },
];

function relativeTime(ts) {
  if (!ts) return '';
  const diff = Date.now() - ts;
  const min = Math.floor(diff / 60000);
  if (min < 1) return 'now';
  if (min < 60) return `${min}m`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h`;
  const day = Math.floor(hr / 24);
  return `${day}d`;
}

export default function Sidebar({
  open,
  onClose,
  currentView,
  onSelectView,
  conversations = [],
  activeConversationId,
  onSelectConversation,
  onNewConversation,
  onOpenSettings,
  onSearch,
  onRenameConversation,
  onDeleteConversation,
}) {
  const [search, setSearch] = useState('');
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const searchRef = useRef(null);
  const menuRef = useRef(null);
  const debounceRef = useRef(null);

  useEffect(() => {
    if (searchOpen) searchRef.current?.focus();
  }, [searchOpen]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const onDown = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    window.addEventListener('mousedown', onDown);
    return () => window.removeEventListener('mousedown', onDown);
  }, [menuOpen]);

  const handleSearchChange = (value) => {
    setSearch(value);
    if (!onSearch) return;
    window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => onSearch(value.trim()), 300);
  };

  const navButton = (item) => {
    const active = currentView === item.view;
    return (
      <button
        type="button"
        key={item.view}
        onClick={() => onSelectView(item.view)}
        aria-current={active ? 'page' : undefined}
        className={`group flex w-full items-center gap-3 rounded-2xl px-3 py-2.5 text-sm transition duration-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40 ${
          active
            ? 'border border-rose-200/10 bg-gradient-to-r from-rose-400/[0.09] to-fuchsia-500/[0.045] text-white shadow-[inset_0_1px_0_rgba(255,255,255,.05)]'
            : 'border border-transparent text-slate-400 hover:border-white/5 hover:bg-white/[0.035] hover:text-slate-100'
        }`}
      >
        <Icon name={item.icon} className={`h-[18px] w-[18px] ${active ? 'text-rose-300' : 'group-hover:text-rose-300'}`} />
        <span>{item.label}</span>
        {active && <span className="ml-auto h-1.5 w-1.5 rounded-full bg-rose-300 shadow-[0_0_12px_rgba(253,164,175,.95)]" />}
      </button>
    );
  };

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
        className={`glass-panel fixed inset-y-3 left-3 z-40 flex w-[290px] flex-col overflow-hidden rounded-[28px] p-3 transition-transform duration-500 ease-out lg:static lg:inset-auto lg:z-auto lg:h-[calc(100dvh-24px)] lg:translate-x-0 ${
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
          onClick={onNewConversation}
          className="group mt-4 flex items-center justify-center gap-2 rounded-2xl border border-rose-300/20 bg-gradient-to-r from-rose-500/20 via-fuchsia-500/15 to-violet-600/20 px-4 py-3 text-sm font-medium text-rose-50 shadow-brand transition duration-300 hover:scale-[1.02] hover:border-rose-200/40 hover:shadow-[0_0_42px_rgba(244,63,94,.20)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
        >
          <Icon name="plus" className="h-4 w-4 transition-transform duration-300 group-hover:rotate-90" />
          New conversation
        </button>

        <nav className="mt-5 space-y-1" aria-label="Primary navigation">
          {primaryNav.map(navButton)}
        </nav>

        <p className="mt-5 px-3 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">System</p>
        <nav className="mt-1 space-y-1" aria-label="System navigation">
          {systemNav.map(navButton)}
        </nav>

        <div className="mt-6 flex items-center justify-between px-2">
          <p className="text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Recent</p>
          <button
            type="button"
            onClick={() => {
              const next = !searchOpen;
              setSearchOpen(next);
              if (!next) {
                setSearch('');
                onSearch?.('');
              }
            }}
            className="text-slate-500 transition hover:text-rose-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
            aria-label={searchOpen ? 'Hide conversation search' : 'Search conversations'}
            aria-expanded={searchOpen}
          >
            <Icon name="search" className="h-4 w-4" />
          </button>
        </div>

        {searchOpen && (
          <div className="mt-2 px-1">
            <input
              ref={searchRef}
              value={search}
              onChange={(e) => handleSearchChange(e.target.value)}
              placeholder="Search title or message…"
              className="w-full rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-rose-300/30"
              aria-label="Search conversations"
            />
          </div>
        )}

        <div className="scrollbar-subtle mt-2 min-h-0 flex-1 space-y-1 overflow-y-auto pr-1">
          {conversations.length === 0 && (
            <p className="px-3 py-6 text-center text-[11px] text-slate-600">
              {search.trim() ? 'No matches.' : 'No conversations yet.'}
            </p>
          )}
          {conversations.map((conversation) => {
            const active = conversation.id === activeConversationId;
            const count = conversation.messageCount ?? conversation.messages?.length ?? 0;
            return (
              <div
                key={conversation.id}
                className={`group flex items-center gap-2 rounded-2xl border pr-1.5 transition duration-300 ${
                  active
                    ? 'border-rose-200/15 bg-rose-300/[0.06]'
                    : 'border-transparent hover:border-rose-200/[0.07] hover:bg-rose-300/[0.035]'
                }`}
              >
                <button
                  type="button"
                  onClick={() => onSelectConversation(conversation.id)}
                  aria-current={active ? 'true' : undefined}
                  className="flex min-w-0 flex-1 items-center gap-3 rounded-2xl px-3 py-2.5 text-left focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
                >
                  <span
                    className={`h-8 w-1 rounded-full ${
                      active
                        ? 'bg-gradient-to-b from-rose-300 via-fuchsia-400 to-violet-500'
                        : 'bg-white/5 group-hover:bg-white/10'
                    }`}
                  />
                  <span className="min-w-0 flex-1">
                    <span className={`block truncate text-xs font-medium ${active ? 'text-white' : 'text-slate-300 group-hover:text-white'}`}>
                      {conversation.title}
                    </span>
                    <span className="mt-1 block text-[10px] text-slate-600">
                      {count} message{count === 1 ? '' : 's'}
                    </span>
                  </span>
                  <span className="text-[10px] text-slate-600">{relativeTime(conversation.updatedAt)}</span>
                </button>
                <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition group-hover:opacity-100 focus-within:opacity-100">
                  <button
                    type="button"
                    onClick={() => onRenameConversation?.(conversation.id)}
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 transition hover:bg-white/[0.06] hover:text-rose-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
                    aria-label={`Rename ${conversation.title}`}
                  >
                    <Icon name="edit" className="h-3.5 w-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => onDeleteConversation?.(conversation.id)}
                    className="grid h-7 w-7 place-items-center rounded-lg text-slate-500 transition hover:bg-amber-300/[0.12] hover:text-amber-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300/40"
                    aria-label={`Delete ${conversation.title}`}
                  >
                    <Icon name="trash" className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            );
          })}
        </div>

        <div className="relative mt-3 rounded-2xl border border-rose-200/10 bg-gradient-to-br from-white/[0.045] to-rose-400/[0.025] p-3" ref={menuRef}>
          <div className="flex items-center gap-3">
            <div className="relative grid h-10 w-10 place-items-center rounded-2xl bg-gradient-to-br from-rose-400/35 via-fuchsia-500/25 to-amber-300/20 text-sm font-semibold text-rose-50">
              BK
              <span className="absolute -bottom-0.5 -right-0.5 h-3 w-3 rounded-full border-2 border-[#0b0710] bg-rose-300 shadow-[0_0_10px_rgba(253,164,175,.75)]" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="truncate text-xs font-medium text-white">Bharat Kumar</p>
              <p className="text-[10px] text-slate-500">Pro workspace</p>
            </div>
            <button
              type="button"
              onClick={() => setMenuOpen((v) => !v)}
              className="text-slate-500 transition hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
              aria-label="Account options"
              aria-haspopup="menu"
              aria-expanded={menuOpen}
            >
              <Icon name="more" className="h-5 w-5" />
            </button>
          </div>

          {menuOpen && (
            <div
              role="menu"
              className="absolute bottom-[calc(100%+8px)] right-2 w-48 overflow-hidden rounded-2xl border border-white/10 bg-[#0c0813]/95 p-1 shadow-glass backdrop-blur-2xl"
            >
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  onOpenSettings();
                }}
                className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs text-slate-300 transition hover:bg-white/[0.05] hover:text-white"
              >
                <Icon name="settings" className="h-4 w-4" />
                Settings
              </button>
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false);
                  onSelectView('system');
                }}
                className="flex w-full items-center gap-2.5 rounded-xl px-3 py-2 text-left text-xs text-slate-300 transition hover:bg-white/[0.05] hover:text-white"
              >
                <Icon name="cpu" className="h-4 w-4" />
                System status
              </button>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
