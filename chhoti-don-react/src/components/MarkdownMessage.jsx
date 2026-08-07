import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import CodeBlock from './CodeBlock';

/**
 * Renders assistant text as GitHub-flavoured markdown.
 * Fenced code becomes a syntax-highlighted CodeBlock with its own copy button;
 * inline code, links, lists, tables and headings get palette-matched styling.
 */
const components = {
  // Unwrap <pre> so our CodeBlock (a <div>) is not nested inside <pre>.
  pre: ({ children }) => <>{children}</>,
  code({ className, children, ...rest }) {
    const match = /language-(\w+)/.exec(className || '');
    const raw = String(children ?? '');
    const isBlock = Boolean(match) || raw.includes('\n');

    if (isBlock) {
      return <CodeBlock language={match ? match[1] : 'text'} value={raw.replace(/\n$/, '')} />;
    }
    return (
      <code
        className="rounded-md border border-white/10 bg-white/[0.06] px-1.5 py-0.5 text-[0.85em] text-brand-200"
        {...rest}
      >
        {children}
      </code>
    );
  },
  a: ({ children, ...props }) => (
    <a
      {...props}
      target="_blank"
      rel="noopener noreferrer"
      className="text-brand-300 underline decoration-brand-300/40 underline-offset-2 transition hover:text-brand-200"
    >
      {children}
    </a>
  ),
  ul: ({ children }) => <ul className="my-2 ml-4 list-disc space-y-1 marker:text-brand-300/60">{children}</ul>,
  ol: ({ children }) => <ol className="my-2 ml-4 list-decimal space-y-1 marker:text-brand-300/60">{children}</ol>,
  li: ({ children }) => <li className="leading-6">{children}</li>,
  p: ({ children }) => <p className="my-1.5 leading-6 first:mt-0 last:mb-0">{children}</p>,
  h1: ({ children }) => <h1 className="mb-2 mt-3 text-base font-semibold text-white">{children}</h1>,
  h2: ({ children }) => <h2 className="mb-2 mt-3 text-[15px] font-semibold text-white">{children}</h2>,
  h3: ({ children }) => <h3 className="mb-1.5 mt-2.5 text-sm font-semibold text-slate-100">{children}</h3>,
  blockquote: ({ children }) => (
    <blockquote className="my-2 border-l-2 border-brand-300/40 pl-3 text-slate-400">{children}</blockquote>
  ),
  strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
  hr: () => <hr className="my-3 border-white/10" />,
  table: ({ children }) => (
    <div className="my-3 overflow-x-auto">
      <table className="w-full border-collapse text-xs">{children}</table>
    </div>
  ),
  th: ({ children }) => (
    <th className="border border-white/10 bg-white/[0.04] px-2.5 py-1.5 text-left font-semibold text-slate-200">
      {children}
    </th>
  ),
  td: ({ children }) => <td className="border border-white/10 px-2.5 py-1.5 text-slate-300">{children}</td>,
};

export default function MarkdownMessage({ children }) {
  return (
    <div className="markdown-body text-[13px] sm:text-sm">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {typeof children === 'string' ? children : ''}
      </ReactMarkdown>
    </div>
  );
}
