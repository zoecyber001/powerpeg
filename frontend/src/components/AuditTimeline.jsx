import React from 'react';
import { History, Shield, Cpu, Terminal } from 'lucide-react';

export default function AuditTimeline({ events }) {
  const getBadgeStyle = (actorType) => {
    switch (actorType) {
      case 'ADMIN':
        return 'bg-purple-500/10 text-purple-300 border-purple-500/20';
      case 'DEVICE':
        return 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20';
      default:
        return 'bg-emerald-500/10 text-emerald-300 border-emerald-500/20';
    }
  };

  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <History className="h-5 w-5 text-indigo-400" />
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">
            Audit Trail & Event Timeline (FR-13)
          </h2>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {(events || []).length} Recorded Events
        </span>
      </div>

      <div className="space-y-2.5 flex-1 overflow-y-auto max-h-[320px] pr-1 font-mono text-xs">
        {(events || []).length === 0 ? (
          <div className="text-center py-8 text-slate-500 text-xs">
            No events logged yet.
          </div>
        ) : (
          events.map((evt) => (
            <div 
              key={evt.id}
              className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col gap-1"
            >
              <div className="flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold uppercase border ${getBadgeStyle(evt.actor_type)}`}>
                    {evt.actor_type}
                  </span>
                  <span className="font-semibold text-slate-200">
                    {evt.event_type}
                  </span>
                </div>
                <span className="text-[10px] text-slate-500">
                  {new Date(evt.created_at).toLocaleTimeString()}
                </span>
              </div>

              {evt.details && (
                <div className="text-[11px] text-slate-400 pl-1 border-l border-slate-800 break-all">
                  {JSON.stringify(evt.details)}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
