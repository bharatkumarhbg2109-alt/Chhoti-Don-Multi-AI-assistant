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
    ? 'rounded-tr-md border-brand-300/15 bg-gradient-to-br from-brand-500/20 via-brand-deep-500/13 to-brand-blue-600/16 text-slate-100'
    : isError
      ? 'rounded-tl-md border-brand-mist-400/30 bg-gradient-to-br from-brand-mist-500/[0.12] to-brand-500/[0.08] text-brand-mist-100'
      : 'rounded-tl-md border-white/10 bg-gradient-to-br from-white/[0.052] to-brand-300/[0.022] text-slate-300 backdrop-blur-xl';

  return (
    <article className={`group flex animate-message-in gap-3 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div
          className={`mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border shadow-brand ${
            isError
              ? 'border-brand-mist-400/25 bg-gradient-to-br from-brand-mist-500/25 to-brand-500/20'
              : 'border-brand-300/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20'
          }`}
        >
          <Icon name={isError ? 'shield' : 'sparkles'} className="h-4 w-4 text-brand-100" />
        </div>
      )}

      <div className={`min-w-0 max-w-[86%] sm:max-w-[78%] ${isUser ? 'items-end' : 'items-start'} flex flex-col`}>
        <div
          className={`relative min-w-0 max-w-full rounded-[22px] border px-4 py-3 text-[13px] leading-6 shadow-glass sm:px-5 sm:py-4 sm:text-sm ${bubbleClass}`}
        >
          {isUser || isError ? (
            <span className="block whitespace-pre-wrap [overflow-wrap:anywhere]">{children}</span>
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
                  className="flex items-center gap-1 rounded-lg px-2 py-0.5 text-brand-mist-200 transition hover:bg-brand-mist-300/[0.12] hover:text-brand-mist-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-mist-300/40"
                >
                  <Icon name="history" className="h-3.5 w-3.5" />
                  Retry
                </button>
              )}
              {onDismiss && (
                <button
                  type="button"
                  onClick={onDismiss}
                  className="flex items-center gap-1 rounded-lg px-2 py-0.5 text-slate-500 transition hover:bg-white/[0.05] hover:text-slate-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
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
              {copied && <span className="ml-1 text-brand-300">Copied</span>}
            </div>
          )}
        </div>
      </div>

      {isUser && (
        <div className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-xl border border-brand-200/10 bg-gradient-to-br from-white/[0.09] to-brand-400/[0.08] text-[10px] font-semibold text-white">
          BK
        </div>
      )}
    </article>
  );
}
