import React, { useState } from 'react';
import { ChevronDown, ChevronRight } from 'lucide-react';

export default function AuditView({ events = [] }) {
  const [filterActor, setFilterActor] = useState('ALL');
  const [expandedId, setExpandedId] = useState(null);

  const filteredEvents = events.filter(evt => {
    if (filterActor === 'ALL') return true;
    return evt.actor_type === filterActor;
  });

  const actorLabel = (actor) => {
    if (actor === 'ADMIN') return 'front desk';
    if (actor === 'DEVICE') return 'device';
    return 'engine';
  };

  const filters = [
    { id: 'ALL', label: 'Everything' },
    { id: 'SYSTEM', label: 'Engine' },
    { id: 'ADMIN', label: 'Front desk' },
    { id: 'DEVICE', label: 'Device' },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-medium text-ink">Audit trail</h2>
          <p className="mt-0.5 text-xs text-ink-3">
            Power authorisations, cutoffs and staff actions
          </p>
        </div>

        <div className="flex items-center gap-0.5 overflow-x-auto rounded-control border border-line bg-surface p-0.5">
          {filters.map(f => (
            <button
              key={f.id}
              onClick={() => setFilterActor(f.id)}
              aria-pressed={filterActor === f.id}
              className={`h-7 whitespace-nowrap rounded-[6px] px-2.5 text-xs transition-colors duration-150 ${
                filterActor === f.id ? 'bg-paper text-ink' : 'text-ink-3 hover:text-ink'
              }`}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      <section className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
        <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
          <h3 className="text-xs font-medium text-ink">Events</h3>
          <span className="num font-mono text-[10px] text-ink-3">
            {filteredEvents.length} shown
          </span>
        </div>

        <div className="divide-y divide-line">
          {filteredEvents.length === 0 ? (
            <p className="px-4 py-8 text-center text-[11px] text-ink-3">
              No events for this actor.
            </p>
          ) : (
            filteredEvents.map(evt => {
              const isExpanded = expandedId === evt.id;

              return (
                <div key={evt.id}>
                  <button
                    onClick={() => setExpandedId(isExpanded ? null : evt.id)}
                    aria-expanded={isExpanded}
                    className="flex w-full items-center justify-between gap-4 px-4 py-2.5 text-left transition-colors duration-150 hover:bg-paper/70"
                  >
                    <div className="flex min-w-0 items-baseline gap-2.5">
                      <span className="truncate text-xs text-ink">
                        {evt.event_type.replace(/_/g, ' ').toLowerCase()}
                      </span>
                      <span className="shrink-0 font-mono text-[10px] text-ink-3">
                        {actorLabel(evt.actor_type)}
                      </span>
                      <span className="hidden truncate font-mono text-[10px] text-ink-4 sm:inline">
                        {evt.actor_id}
                      </span>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <span className="num font-mono text-[10px] text-ink-4">
                        {new Date(evt.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                      {isExpanded ? (
                        <ChevronDown className="h-3.5 w-3.5 text-ink-4" />
                      ) : (
                        <ChevronRight className="h-3.5 w-3.5 text-ink-4" />
                      )}
                    </div>
                  </button>

                  {isExpanded && evt.details && (
                    <div className="border-t border-line bg-paper px-4 py-2.5">
                      <pre className="overflow-x-auto whitespace-pre-wrap font-mono text-[10px] leading-relaxed text-ink-2">
                        {JSON.stringify(evt.details, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </section>
    </div>
  );
}
