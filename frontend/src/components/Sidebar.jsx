import React from 'react';
import {
  BedDouble, Zap, AlertTriangle, History, Sliders, Building2, RotateCcw
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  activeAlertCount,
  onResetDemo,
  isResetting
}) {
  const navItems = [
    { id: 'rooms', label: 'Rooms & power', icon: BedDouble },
    { id: 'energy', label: 'Energy', icon: Zap },
    { id: 'alerts', label: 'Incidents', icon: AlertTriangle, count: activeAlertCount },
    { id: 'audit', label: 'Audit trail', icon: History },
    { id: 'tools', label: 'Switch diagnostics', icon: Sliders },
  ];

  return (
    <aside className="w-[248px] shrink-0 select-none border-r border-line bg-surface flex flex-col justify-between">
      <div>
        <div className="px-5 pt-5 pb-4">
          <div className="flex items-baseline gap-2">
            <span className="text-[15px] font-medium tracking-tight text-ink">PegPower</span>
            <span className="font-mono text-[10px] text-ink-4">PMS</span>
          </div>
          <p className="mt-0.5 text-[11px] text-ink-3">Room power, tied to the folio</p>
        </div>

        <div className="mx-5 mb-5 flex items-center gap-2 border-t border-line pt-4">
          <Building2 className="h-4 w-4 shrink-0 text-ink-4" />
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-ink">The Grand Palm</p>
            <p className="num truncate font-mono text-[10px] text-ink-3">Ocean Wing · 3 rooms</p>
          </div>
        </div>

        <nav aria-label="Sections" className="px-3">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                aria-current={isActive ? 'page' : undefined}
                className={`mb-0.5 flex h-9 w-full items-center justify-between rounded-control px-2.5 text-[13px] transition-colors duration-150 ${
                  isActive
                    ? 'bg-paper text-ink shadow-card'
                    : 'text-ink-2 hover:bg-paper hover:text-ink'
                }`}
              >
                <span className="flex items-center gap-2.5">
                  <Icon className={`h-4 w-4 shrink-0 ${isActive ? 'text-ink' : 'text-ink-4'}`} />
                  <span>{item.label}</span>
                </span>
                {item.count > 0 && (
                  <span className="num font-mono text-[11px] text-brick-ink">{item.count}</span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="border-t border-line px-3 py-3">
        <div className="flex items-center gap-2.5 px-2.5 py-2">
          <span className="flex h-7 w-7 items-center justify-center rounded-full border border-line bg-paper font-mono text-[10px] text-ink-2">
            SJ
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-xs font-medium text-ink">Sarah Jenkins</p>
            <p className="truncate text-[11px] text-ink-3">Front desk manager</p>
          </div>
        </div>

        <button
          onClick={onResetDemo}
          disabled={isResetting}
          className="mt-1 flex h-8 w-full items-center justify-center gap-2 rounded-control border border-line text-[11px] text-ink-2 transition-colors duration-150 hover:border-line-strong hover:text-ink disabled:opacity-50"
        >
          <RotateCcw className={`h-3 w-3 ${isResetting ? 'animate-spin' : ''}`} />
          <span>{isResetting ? 'Resetting' : 'Reset demo data'}</span>
        </button>
      </div>
    </aside>
  );
}
