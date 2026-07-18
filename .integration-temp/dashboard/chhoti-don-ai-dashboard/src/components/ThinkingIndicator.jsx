import React from 'react';
import Icon from './Icon';

export default function ThinkingIndicator() {
  return (
    <div className="flex animate-message-in items-start gap-3">
      <div className="mt-1 grid h-8 w-8 place-items-center rounded-xl border border-rose-300/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20 shadow-brand">
        <Icon name="sparkles" className="h-4 w-4 text-rose-100" />
      </div>
      <div className="rounded-[22px] rounded-tl-md border border-white/10 bg-gradient-to-br from-white/[0.052] to-rose-300/[0.022] px-5 py-4 backdrop-blur-xl">
        <div className="flex items-center gap-2">
          {[0, 1, 2].map((dot) => (
            <span
              key={dot}
              className="h-2 w-2 rounded-full bg-gradient-to-r from-rose-300 via-fuchsia-400 to-violet-400 animate-bounce"
              style={{ animationDelay: `${dot * 160}ms`, animationDuration: '900ms' }}
            />
          ))}
          <span className="ml-1 text-xs text-slate-500">Chhoti Don is thinking</span>
        </div>
        <div className="mt-3 h-1.5 w-44 overflow-hidden rounded-full bg-white/5">
          <div className="h-full w-full bg-[linear-gradient(90deg,transparent,rgba(253,164,175,.76),rgba(232,121,249,.78),rgba(196,181,253,.72),transparent)] bg-[length:200%_100%] animate-shimmer" />
        </div>
      </div>
    </div>
  );
}
