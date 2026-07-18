import React, { useEffect, useRef } from 'react';
import Icon from './Icon';
import { useToast } from '../context/ToastContext';

export default function ChatComposer({ value, onChange, onSubmit, onStop, busy = false, disabled, inputRef }) {
  const localRef = useRef(null);
  const textareaRef = inputRef ?? localRef;
  const { notify } = useToast();

  useEffect(() => {
    const element = textareaRef.current;
    if (!element) return;
    element.style.height = 'auto';
    element.style.height = `${Math.min(element.scrollHeight, 144)}px`;
  }, [value]);

  const handleKeyDown = (event) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className="relative mx-auto w-full max-w-4xl">
      <div className="composer-glow absolute -inset-px rounded-[26px] opacity-0 blur-md transition duration-500" />
      <div className="composer relative flex items-end gap-2 rounded-[25px] border border-white/10 bg-[#09060f]/75 p-2 shadow-[0_18px_60px_rgba(0,0,0,.38)] backdrop-blur-2xl transition duration-300 focus-within:border-rose-300/30 focus-within:bg-[#0c0813]/90">
        <button
          type="button"
          onClick={() => notify('File attachments aren’t available yet.')}
          className="icon-button mb-0.5 shrink-0"
          aria-label="Attach file"
        >
          <Icon name="attachment" className="h-[18px] w-[18px]" />
        </button>

        <textarea
          ref={textareaRef}
          rows={1}
          value={value}
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Chhoti Don anything..."
          className="max-h-36 min-h-[42px] flex-1 resize-none bg-transparent px-1 py-2.5 text-sm leading-6 text-slate-100 outline-none placeholder:text-slate-600 disabled:cursor-not-allowed"
          aria-label="Message Chhoti Don"
        />

        <button
          type="button"
          onClick={() => notify('Voice input isn’t available yet.')}
          className="icon-button mb-0.5 shrink-0"
          aria-label="Use voice input"
        >
          <Icon name="mic" className="h-[18px] w-[18px]" />
        </button>
        {busy && onStop ? (
          <button
            type="button"
            onClick={onStop}
            aria-label="Stop generating"
            className="group mb-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-amber-300/40 bg-gradient-to-br from-amber-400/30 to-rose-500/25 text-amber-50 shadow-brand transition duration-300 hover:scale-105 hover:border-amber-200/60"
          >
            <Icon name="stop" className="h-[16px] w-[16px]" />
          </button>
        ) : (
          <button
            type="button"
            disabled={disabled || !value.trim()}
            onClick={onSubmit}
            aria-label="Send message"
            className="group mb-0.5 grid h-10 w-10 shrink-0 place-items-center rounded-2xl border border-rose-300/25 bg-gradient-to-br from-rose-400/35 via-fuchsia-500/30 to-violet-600/35 text-rose-50 shadow-brand transition duration-300 hover:scale-105 hover:border-rose-200/55 hover:shadow-[0_0_40px_rgba(244,63,94,.30)] disabled:cursor-not-allowed disabled:opacity-35 disabled:hover:scale-100"
          >
            <Icon name="send" className="h-[18px] w-[18px] transition-transform duration-300 group-hover:translate-x-0.5" />
          </button>
        )}
      </div>
      <p className="mt-2 text-center text-[10px] text-slate-600">
        Chhoti Don can make mistakes. Verify important information.
      </p>
    </div>
  );
}
