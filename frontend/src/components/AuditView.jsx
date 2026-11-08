import React, { useState } from 'react';
import { 
  History, Shield, Cpu, Terminal, Filter, Zap, Power, 
  CheckCircle2, AlertTriangle, UserCheck, ChevronDown, ChevronRight
} from 'lucide-react';

export default function AuditView({ events = [] }) {
  const [filterActor, setFilterActor] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);

  const filteredEvents = events.filter(evt => {
    if (filterActor === 'ALL') return true;
    return evt.actor_type === filterActor;
  });

  const getActorBadge = (actor) => {
    switch (actor) {
      case 'ADMIN':
        return { label: 'Front Desk', bg: 'bg-purple-50 text-purple-700 border-purple-200' };
      case 'DEVICE':
        return { label: 'AZ3166 Switch', bg: 'bg-cyan-50 text-cyan-700 border-cyan-200' };
      default:
        return { label: 'Workpeg Engine', bg: 'bg-emerald-50 text-emerald-700 border-emerald-200' };
    }
  };

  const getEventIcon = (eventType) => {
    if (eventType.includes('ALERT')) return <AlertTriangle className="h-4 w-4 text-rose-500" />;
    if (eventType.includes('OVERRIDE')) return <Shield className="h-4 w-4 text-indigo-500" />;
    if (eventType.includes('OFF') || eventType.includes('REVOKE')) return <Power className="h-4 w-4 text-slate-500" />;
    if (eventType.includes('ON') || eventType.includes('AUTH')) return <Zap className="h-4 w-4 text-emerald-500" />;
    if (eventType.includes('PAYMENT') || eventType.includes('BOOKING')) return <CheckCircle2 className="h-4 w-4 text-blue-500" />;
    return <History className="h-4 w-4 text-slate-400" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
            System Audit Trail
          </h2>
          <p className="text-xs font-medium text-slate-500 mt-0.5">
            Immutable log of all power authorizations, automated cutoffs, and staff actions
          </p>
        </div>

        <div className="flex items-center gap-1.5 p-1 bg-slate-100 rounded-xl overflow-x-auto">
          {['ALL', 'SYSTEM', 'ADMIN', 'DEVICE'].map(actor => (
            <button
              key={actor}
              onClick={() => setFilterActor(actor)}
              className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                filterActor === actor
                  ? 'bg-white text-slate-900 shadow-sm'
                  : 'text-slate-500 hover:text-slate-900'
              }`}
            >
              {actor === 'ALL' ? 'All Actors' : actor === 'ADMIN' ? 'Front Desk' : actor === 'DEVICE' ? 'IoT Device' : 'System Engine'}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl shadow-card overflow-hidden">
        <div className="p-4 border-b border-slate-100 flex items-center justify-between">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
            Chronological Events ({filteredEvents.length})
          </span>
          <span className="text-[11px] text-slate-400">
            Auto-recorded by Workpeg hooks
          </span>
        </div>

        <div className="divide-y divide-slate-100">
          {filteredEvents.length === 0 ? (
            <div className="p-8 text-center text-slate-400 text-xs">
              No audit logs recorded for this filter.
            </div>
          ) : (
            filteredEvents.map(evt => {
              const actorBadge = getActorBadge(evt.actor_type);
              const isExpanded = expandedId === evt.id;

              return (
                <div 
                  key={evt.id} 
                  className="p-4 hover:bg-slate-50/60 transition cursor-pointer"
                  onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                >
                  <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                      <div className="h-8 w-8 rounded-xl bg-slate-100 flex items-center justify-center shrink-0">
                        {getEventIcon(evt.event_type)}
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-bold text-slate-900">
                            {evt.event_type.replace(/_/g, ' ')}
                          </span>
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-md border ${actorBadge.bg}`}>
                            {actorBadge.label}
                          </span>
                        </div>
                        <p className="text-[11px] text-slate-500 mt-0.5">
                          Actor ID: <span className="font-mono text-slate-600">{evt.actor_id}</span>
                        </p>
                      </div>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs font-mono text-slate-400">
                        {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                      {isExpanded ? (
                        <ChevronDown className="h-4 w-4 text-slate-400" />
                      ) : (
                        <ChevronRight className="h-4 w-4 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {isExpanded && evt.details && (
                    <div className="mt-3 pt-3 border-t border-slate-100 pl-11">
                      <div className="p-3 bg-slate-50 rounded-xl border border-slate-200/80 font-mono text-[11px] text-slate-700">
                        <pre className="whitespace-pre-wrap overflow-x-auto">
                          {JSON.stringify(evt.details, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
