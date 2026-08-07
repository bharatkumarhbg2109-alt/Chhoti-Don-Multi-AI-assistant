import React from 'react';
import Icon from './Icon';

const planned = [
  { icon: 'grid', title: 'Project spaces', desc: 'Group conversations and files by project.' },
  { icon: 'attachment', title: 'File & repo context', desc: 'Attach code, docs, and datasets for grounded answers.' },
  { icon: 'brain', title: 'Persistent knowledge', desc: 'Long-term memory scoped to each workspace.' },
];

/**
 * Local placeholder for the Workspace view. Deliberately does NOT pretend that
 * backend workspace/project functionality exists — it explains what's planned.
 */
export default function WorkspaceView() {
  return (
    <div className="mx-auto max-w-3xl">
      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-10 w-10 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20 shadow-brand">
          <Icon name="grid" className="h-5 w-5 text-brand-100" />
        </div>
        <div>
          <h2 className="font-display text-base font-semibold text-white">Workspace</h2>
          <p className="text-[11px] text-slate-500">Project & file integration — planned</p>
        </div>
      </div>

      <div className="rounded-3xl border border-white/[0.07] bg-gradient-to-br from-white/[0.03] to-brand-400/[0.02] p-8 text-center">
        <div className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-brand-200/15 bg-gradient-to-br from-brand-400/20 via-brand-deep-500/15 to-brand-blue-600/20">
          <Icon name="grid" className="h-7 w-7 text-brand-100" />
        </div>
        <h3 className="mt-4 text-lg font-semibold text-white">Workspaces are on the way</h3>
        <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-400">
          Project and file integration isn't available in the backend yet. This space is reserved
          so the experience is ready the moment it ships. For now, use the Assistant to chat and the
          Memory view to inspect recent context.
        </p>
        <span className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-brand-300/20 bg-brand-400/10 px-3 py-1 text-[11px] font-medium text-brand-200">
          <span className="h-1.5 w-1.5 rounded-full bg-brand-300" />
          Planned feature
        </span>
      </div>

      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {planned.map((item) => (
          <div key={item.title} className="rounded-2xl border border-white/[0.07] bg-white/[0.025] p-4">
            <Icon name={item.icon} className="h-5 w-5 text-brand-deep-300" />
            <p className="mt-2.5 text-sm font-medium text-slate-200">{item.title}</p>
            <p className="mt-1 text-[11px] leading-5 text-slate-500">{item.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
