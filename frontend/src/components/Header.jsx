import React from 'react';
import { 
  Zap, AlertTriangle, RotateCcw, Sliders, CheckCircle2, Shield
} from 'lucide-react';

export default function Header({ 
  filter, 
  setFilter, 
  roomCounts, 
  activeAlertCount, 
  onResetDemo, 
  isResetting, 
  onToggleDemoControls, 
  showDemoControls 
}) {
  return (
    <header className="border-b border-slate-800 bg-[#0A0F1D] sticky top-0 z-30 px-6 py-4">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-emerald-500 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Zap className="h-5 w-5 text-slate-950 fill-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-white">PegPower</h1>
              <span className="text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700">
                Front Desk Ops
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Automated room electricity access & checkout protection
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 bg-slate-900 p-1 rounded-xl border border-slate-800 text-xs">
          <button
            onClick={() => setFilter('all')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 'all' 
                ? 'bg-slate-800 text-white shadow-sm' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All Rooms ({roomCounts.total})
          </button>
          <button
            onClick={() => setFilter('active')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 'active' 
                ? 'bg-emerald-500/20 text-emerald-300 shadow-sm border border-emerald-500/30' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Power On ({roomCounts.active})
          </button>
          <button
            onClick={() => setFilter('vacant')}
            className={`px-3 py-1.5 rounded-lg font-medium transition ${
              filter === 'vacant' 
                ? 'bg-slate-800 text-white shadow-sm' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            Vacant ({roomCounts.vacant})
          </button>
        </div>

        <div className="flex items-center gap-2">
          {activeAlertCount > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-rose-500/15 border border-rose-500/30 text-rose-300 text-xs font-semibold animate-pulse">
              <AlertTriangle className="h-4 w-4" />
              <span>{activeAlertCount} Alert</span>
            </div>
          )}

          <button
            onClick={onToggleDemoControls}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition ${
              showDemoControls 
                ? 'bg-indigo-600 text-white border-indigo-500' 
                : 'bg-slate-900 hover:bg-slate-800 text-slate-300 border-slate-800'
            }`}
            title="Toggle simulation and test controls"
          >
            <Sliders className="h-3.5 w-3.5" />
            <span>Staff Tools</span>
          </button>

          <button
            onClick={onResetDemo}
            disabled={isResetting}
            title="Reset system to clean demo state"
            className="p-2 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-400 hover:text-white border border-slate-800 transition disabled:opacity-50"
          >
            <RotateCcw className={`h-4 w-4 ${isResetting ? 'animate-spin' : ''}`} />
          </button>
        </div>

      </div>
    </header>
  );
}
