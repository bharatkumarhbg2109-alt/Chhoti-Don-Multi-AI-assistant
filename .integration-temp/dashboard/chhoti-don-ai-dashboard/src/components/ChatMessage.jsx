import React, { useState } from 'react';
import Icon from './Icon';

export default function ChatMessage({ role, children, timestamp }) {
  const [copied, setCopied] = useState(false);
  const isUser = role === 'user';

  const copyMessage = async () => {
    try {
      await navigator.clipboard.writeText(typeof children === 'string' ? children : 'Chhoti Don response');
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  return (
    <article className={`group flex animate-message-in gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-rose-300/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20 shadow-brand">
          <Icon name="sparkles" className="h-4 w-4 text-rose-100" />
        </div>
      )}

      <div className={`max-w-[86%] sm:max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`relative rounded-[22px] border px-4 py-3 text-[13px] leading-6 shadow-glass sm:px-5 sm:py-4 sm:text-sm ${
            isUser
              ? 'rounded-tr-md border-rose-300/15 bg-gradient-to-br from-rose-500/20 via-fuchsia-500/13 to-violet-600/16 text-slate-100'
              : 'rounded-tl-md border-white/10 bg-gradient-to-br from-white/[0.052] to-rose-300/[0.022] text-slate-300 backdrop-blur-xl'
          }`}
        >
          {children}
        </div>

        <div className={`mt-1.5 flex items-center gap-1.5 px-1 text-[10px] text-slate-600 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span>{timestamp}</span>
          {!isUser && (
            <div className="flex translate-y-1 items-center gap-0.5 opacity-0 transition duration-300 group-hover:translate-y-0 group-hover:opacity-100">
              <button type="button" onClick={copyMessage} className="message-action" aria-label="Copy response">
                <Icon name="copy" className="h-3.5 w-3.5" />
              </button>
              <button type="button" className="message-action" aria-label="Like response">
                <Icon name="thumbsUp" className="h-3.5 w-3.5" />
              </button>
              <button type="button" className="message-action" aria-label="Read response aloud">
                <Icon name="volume" className="h-3.5 w-3.5" />
              </button>
              {copied && <span className="ml-1 text-rose-300">Copied</span>}
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-rose-200/10 bg-gradient-to-br from-white/[0.09] to-rose-400/[0.08] text-[10px] font-semibold text-white">
          BK
        </div>
      )}
    </article>
  );
}
