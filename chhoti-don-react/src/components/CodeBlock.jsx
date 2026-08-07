import React, { useEffect, useRef, useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import Icon from './Icon';

/**
 * A syntax-highlighted code block with its own "Copy code" button.
 * Used for fenced code inside assistant markdown.
 */
export default function CodeBlock({ language = 'text', value = '' }) {
  const [copied, setCopied] = useState(false);
  const timerRef = useRef(null);

  useEffect(() => () => window.clearTimeout(timerRef.current), []);

  const copyCode = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      window.clearTimeout(timerRef.current);
      timerRef.current = window.setTimeout(() => setCopied(false), 1400);
    } catch {
      setCopied(false);
    }
  };

  return (
    <div className="group/code relative my-3 overflow-hidden rounded-2xl border border-white/10 bg-[#0a0710]/80">
      <div className="flex items-center justify-between border-b border-white/[0.06] px-3 py-1.5">
        <span className="text-[10px] font-medium uppercase tracking-[0.18em] text-slate-500">
          {language}
        </span>
        <button
          type="button"
          onClick={copyCode}
          className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-[11px] text-slate-400 transition duration-200 hover:bg-brand-300/[0.08] hover:text-brand-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
          aria-label={copied ? 'Code copied to clipboard' : 'Copy code to clipboard'}
        >
          <Icon name={copied ? 'shield' : 'copy'} className="h-3.5 w-3.5" />
          {copied ? 'Copied' : 'Copy code'}
        </button>
      </div>
      <SyntaxHighlighter
        language={language}
        style={oneDark}
        customStyle={{
          margin: 0,
          padding: '14px 16px',
          background: 'transparent',
          fontSize: '12.5px',
          lineHeight: 1.6,
          overflowX: 'auto',
          maxWidth: '100%',
        }}
        codeTagProps={{ style: { fontFamily: 'ui-monospace, SFMono-Regular, Menlo, monospace' } }}
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
}
