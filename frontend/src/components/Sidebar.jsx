import React from 'react';
import { 
  Building2, BedDouble, Zap, AlertTriangle, History, Sliders, ChevronDown, CheckCircle2
} from 'lucide-react';

export default function Sidebar({
  activeTab,
  setActiveTab,
  activeAlertCount,
  onResetDemo,
  isResetting
}) {
  const navItems = [
    { id: 'rooms', label: 'Rooms & Power', icon: BedDouble },
    { id: 'energy', label: 'Energy Analytics', icon: Zap },
    { id: 'alerts', label: 'Incidents', icon: AlertTriangle, count: activeAlertCount },
    { id: 'audit', label: 'Audit Trail', icon: History },
    { id: 'tools', label: 'Switch Diagnostics', icon: Sliders },
  ];

  return (
    <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between shrink-0 select-none">
      <div>
        <div className="p-5 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-xl bg-emerald-600 flex items-center justify-center shadow-md shadow-emerald-600/20">
              <Zap className="h-5 w-5 text-white fill-white" />
            </div>
            <div>
              <div className="flex items-center gap-1.5">
                <span className="font-extrabold text-base tracking-tight text-slate-900">PegPower</span>
                <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800">
                  PMS
                </span>
              </div>
              <p className="text-[11px] font-medium text-slate-400">Power Access Platform</p>
            </div>
          </div>

          <div className="mt-4 p-2.5 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
            <div className="flex items-center gap-2 overflow-hidden">
              <Building2 className="h-4 w-4 text-slate-500 shrink-0" />
              <div className="truncate">
                <p className="text-xs font-bold text-slate-800 truncate">The Grand Palm</p>
                <p className="text-[10px] text-slate-400">Ocean Wing • 3 Rooms</p>
              </div>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400 shrink-0" />
          </div>
        </div>

        <nav className="p-3 space-y-1">
          {navItems.map((item) => {
            const Icon = item.icon;
            const isActive = activeTab === item.id;
            return (
              <button
                key={item.id}
                onClick={() => setActiveTab(item.id)}
                className={`w-full flex items-center justify-between px-3.5 py-2.5 rounded-xl text-xs font-semibold transition ${
                  isActive
                    ? 'bg-emerald-50 text-emerald-800 border border-emerald-200/60 shadow-sm'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <div className="flex items-center gap-2.5">
                  <Icon className={`h-4 w-4 ${isActive ? 'text-emerald-600' : 'text-slate-400'}`} />
                  <span>{item.label}</span>
                </div>
                {item.count > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-rose-500 text-white animate-pulse">
                    {item.count}
                  </span>
                )}
              </button>
            );
          })}
        </nav>
      </div>

      <div className="p-4 border-t border-slate-100 space-y-3">
        <div className="flex items-center gap-2.5 p-2 rounded-xl bg-slate-50">
          <div className="h-8 w-8 rounded-full bg-slate-200 flex items-center justify-center font-bold text-xs text-slate-700">
            SJ
          </div>
          <div className="truncate flex-1">
            <p className="text-xs font-bold text-slate-800 truncate">Sarah Jenkins</p>
            <p className="text-[10px] text-slate-400">Front Desk Manager</p>
          </div>
          <span className="h-2 w-2 rounded-full bg-emerald-500 ring-4 ring-emerald-100" />
        </div>

        <button
          onClick={onResetDemo}
          disabled={isResetting}
          className="w-full py-2 px-3 rounded-xl border border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50 text-xs font-medium transition flex items-center justify-center gap-1.5 disabled:opacity-50"
        >
          <span>Reset Demo Data</span>
        </button>
      </div>
    </aside>
  );
}
