import React from 'react';
import AiOrb from './AiOrb';
import Icon from './Icon';

/**
 * Dedicated empty state shown before the first user message.
 * Presents the orb, a welcome line, and suggestion chips that seed a prompt.
 */
export default function EmptyState({ backendOnline, prompts = [], onPick }) {
  return (
    <div className="flex flex-col items-center text-center">
      <AiOrb compact />

      <div className="mt-5 flex items-center gap-2 rounded-full border border-rose-200/10 bg-gradient-to-r from-white/[0.04] to-rose-400/[0.025] px-3 py-1.5 backdrop-blur-xl">
        <span className="relative flex h-2 w-2">
          <span
            className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-55 ${
              backendOnline === false ? 'bg-amber-400' : 'bg-rose-300'
            }`}
          />
          <span
            className={`relative inline-flex h-2 w-2 rounded-full ${
              backendOnline === false
                ? 'bg-amber-400 shadow-[0_0_10px_rgba(251,191,36,.7)]'
                : 'bg-rose-200 shadow-[0_0_10px_rgba(253,164,175,.7)]'
            }`}
          />
        </span>
        <span className="text-[10px] font-medium uppercase tracking-[0.2em] text-slate-400">
          {backendOnline === false ? 'CHHOTI DON offline' : 'CHHOTI DON online'}
        </span>
      </div>

      <h2 className="font-display mt-4 bg-gradient-to-r from-white via-rose-100 to-fuchsia-200 bg-clip-text text-2xl font-semibold tracking-tight text-transparent sm:text-3xl">
        Your intelligence. Your command.
      </h2>
      <p className="mt-2 max-w-xl text-xs leading-5 text-slate-500 sm:text-sm">
        A private, adaptive space for learning, building, planning, and making confident decisions.
      </p>

      <div className="mt-7 flex flex-wrap justify-center gap-2">
        {prompts.map((idea) => (
          <button
            type="button"
            key={idea}
            onClick={() => onPick(idea)}
            title="Add this prompt to the composer"
            className="group flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3 py-2 text-[11px] text-slate-400 backdrop-blur-xl transition duration-300 hover:scale-[1.02] hover:border-rose-300/20 hover:bg-rose-300/[0.055] hover:text-rose-100 focus-visible:outline focus-visible:outline-2 focus-visible:outline-rose-300/40"
          >
            <Icon name="sparkles" className="h-3.5 w-3.5 text-fuchsia-300 transition group-hover:text-rose-300" />
            {idea}
          </button>
        ))}
      </div>
    </div>
  );
}
