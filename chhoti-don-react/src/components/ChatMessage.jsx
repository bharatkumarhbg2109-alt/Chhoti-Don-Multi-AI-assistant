import React, { useEffect, useRef, useState } from 'react';
import Icon from './Icon';
import MarkdownMessage from './MarkdownMessage';
import { useToast } from '../context/ToastContext';

export default function ChatMessage({ role, children, timestamp, isError = false, onRetry, onDismiss }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef(null);
  const { notify } = useToast();
  const isUser = role === 'user';
  const rawText = typeof children === 'string' ? children : '';

  useEffect(() => () => window.clearTimeout(timerRef.current), []);

  const copyMessage = async () => {
    try {
      await navigator.clipboard.writeText(rawText || 'Chhoti Don response');
      setCopied(true);
      window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setCopied(false);
    }
  };

  const bubbleClass = isUser
    ? 'rounded-tr-md border-rose-300/15 bg-gradient-to-br from-rose-500/20 via-fuchsia-500/13 to-violet-600/16 text-slate-100'
    : isError
      ? 'rounded-tl-md border-amber-400/30 bg-gradient-to-br from-amber-500/[0.12] to-rose-500/[0.08] text-amber-100'
      : 'rounded-tl-md border-white/10 bg-gradient-to-br from-white/[0.052] to-rose-300/[0.022] text-slate-300 backdrop-blur-xl';

  return (
    <article className={`group flex animate-message-in gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div
          className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border shadow-brand ${
            isError
              ? 'border-amber-400/25 bg-gradient-to-br from-amber-500/25 to-rose-500/20'
              : 'border-rose-300/15 bg-gradient-to-br from-rose-400/20 via-fuchsia-500/15 to-violet-600/20'
          }`}
        >
          <Icon name={isError ? 'shield' : 'sparkles'} className="h-4 w-4 text-rose-100" />
        </div>
      )}

      <div className={`max-w-[86%] sm:max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`relative rounded-[22px] border px-4 py-3 text-[13px] leading-6 shadow-glass sm:px-5 sm:py-4 sm:text-sm ${bubbleClass}`}
        >
          {isUser || isError ? (
            <span className="whitespace-pre-wrap break-words">{children}</span>
          ) : (
            <MarkdownMessage>{children}</MarkdownMessage>
          )}
        </div>

        <div className={`mt-1.5 flex items-center gap-1.5 px-1 text-[10px] text-slate-600 ${isUser ? 'flex-row-reverse' : ''}`}>
          <span>{timestamp}</span>
          {isError && (
            <div className="flex items-center gap-1">
              {onRetry && (
                <button
                  type="button"
                  onClick={onRetry}
                  className="flex items-center gap-1 rounded-lg px-2 py-0.5 text-amber-200 transition hover:bg-amber-300/[0.12] hover:text-amber-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-amber-300/40"
                >
                  <Icon name="history" className="h-3.5 w-3.5" />
                  Retry
                </button>
              )}
              {onDismiss && (
                <button
                  type="button"
                  onClick={onDismiss}
                  className="flex items-center gap-1 rounded-lg px-2 py-0.5 text-slate-500 transition hover:bg-white/[0.05] hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
                  aria-label="Dismiss error"
                >
                  <Icon name="close" className="h-3.5 w-3.5" />
                  Dismiss
                </button>
              )}
            </div>
          )}
          {!isUser && !isError && (
            <div className="flex translate-y-1 items-center gap-0.5 opacity-0 transition duration-300 focus-within:translate-y-0 focus-within:opacity-100 group-hover:translate-y-0 group-hover:opacity-100">
              <button type="button" onClick={copyMessage} className="message-action" aria-label="Copy response">
                <Icon name="copy" className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => notify('Feedback isn’t available yet.')}
                className="message-action"
                aria-label="Like response"
              >
                <Icon name="thumbsUp" className="h-3.5 w-3.5" />
              </button>
              <button
                type="button"
                onClick={() => notify('Read-aloud isn’t available yet.')}
                className="message-action"
                aria-label="Read response aloud"
              >
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
