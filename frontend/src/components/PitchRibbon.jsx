import React, { useState } from 'react';
import { ChevronDown } from 'lucide-react';

export default function PitchRibbon({
  onRunScenario,
  isResetting,
  currentScenario
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const scenarios = [
    {
      id: 'CHECK_IN_FLOW',
      title: 'Check-in and power release',
      desc: 'Guest checks in, folio settles, relay closes',
    },
    {
      id: 'CHECK_OUT_FLOW',
      title: 'Express checkout cutoff',
      desc: 'Guest leaves, circuit opens, standby draw ends',
    },
    {
      id: 'ROGUE_DRAW_ALERT',
      title: 'Rogue draw on 204',
      desc: '1.45 kW injected into a vacant, unpaid room',
    },
    {
      id: 'HOUSEKEEPING_OVERRIDE',
      title: 'Housekeeping override',
      desc: '30-minute cleaning access, self-expiring',
    },
  ];

  return (
    <div className="border-b border-line bg-surface">
      <div className="mx-auto flex max-w-[1400px] items-center justify-between px-6 py-2 lg:px-8">
        <div className="flex items-baseline gap-2">
          <span className="font-mono text-[10px] text-ink-4">DEMO</span>
          <span className="text-xs text-ink-2">
            Scripted scenarios for the walkthrough
            {isResetting ? ' · resetting' : ''}
          </span>
        </div>

        <button
          onClick={() => setIsCollapsed(!isCollapsed)}
          aria-expanded={!isCollapsed}
          className="flex items-center gap-1 rounded-control px-1.5 py-1 text-[11px] text-ink-3 transition-colors duration-150 hover:text-ink"
        >
          <span>{isCollapsed ? 'Show' : 'Hide'}</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform duration-150 ${isCollapsed ? '' : 'rotate-180'}`} />
        </button>
      </div>

      {!isCollapsed && (
        <div className="mx-auto max-w-[1400px] px-6 pb-3 lg:px-8">
          <div className="grid grid-cols-1 gap-1.5 sm:grid-cols-2 lg:grid-cols-4">
            {scenarios.map((sc, index) => {
              const isActive = currentScenario === sc.id;
              return (
                <button
                  key={sc.id}
                  onClick={() => onRunScenario(sc.id)}
                  aria-pressed={isActive}
                  className={`flex items-start gap-2.5 rounded-panel border px-3 py-2 text-left transition-colors duration-150 ${
                    isActive
                      ? 'border-brass/40 bg-brass-soft'
                      : 'border-line bg-surface hover:border-line-strong'
                  }`}
                >
                  <span className={`num mt-[1px] font-mono text-[11px] ${isActive ? 'text-brass-ink' : 'text-ink-4'}`}>
                    {index + 1}
                  </span>
                  <span className="min-w-0">
                    <span className={`block text-xs font-medium ${isActive ? 'text-brass-ink' : 'text-ink'}`}>
                      {sc.title}
                    </span>
                    <span className="mt-0.5 block text-[11px] leading-snug text-ink-3">
                      {sc.desc}
                    </span>
                  </span>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
