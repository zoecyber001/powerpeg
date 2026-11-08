import React from 'react';
import { Zap, AlertTriangle, Cpu, RotateCcw, ShieldCheck } from 'lucide-react';

export default function Header({ overview, isWsConnected, onResetDemo, isResetting }) {
  return (
    <header className="border-b border-slate-800 bg-[#0E1526]/80 backdrop-blur sticky top-0 z-30 px-6 py-4">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-400 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Zap className="h-6 w-6 text-slate-950 fill-slate-950" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-bold tracking-tight text-white">PegPower</h1>
              <span className="text-[10px] font-semibold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                Workpeg Peg
              </span>
            </div>
            <p className="text-xs text-slate-400">
              Electricity access control and real-time anomaly reconciliation
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 md:gap-4">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <span className="relative flex h-2.5 w-2.5">
              {isWsConnected ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              )}
            </span>
            <span className="text-slate-300 font-medium">
              {isWsConnected ? 'Live Bus' : 'Polling'}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <ShieldCheck className="h-4 w-4 text-emerald-400" />
            <span className="text-slate-400">Auth:</span>
            <span className="font-bold text-white">
              {overview?.authorised_rooms ?? 0} / {overview?.total_rooms ?? 0}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <Cpu className="h-4 w-4 text-cyan-400" />
            <span className="text-slate-400">AZ3166:</span>
            <span className={`font-bold ${overview?.devices_online > 0 ? 'text-cyan-400' : 'text-amber-400'}`}>
              {overview?.devices_online > 0 ? 'ONLINE' : 'OFFLINE'}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
            <AlertTriangle className={`h-4 w-4 ${overview?.active_alerts > 0 ? 'text-rose-400 animate-pulse' : 'text-slate-400'}`} />
            <span className="text-slate-400">Alerts:</span>
            <span className={`font-bold ${overview?.active_alerts > 0 ? 'text-rose-400' : 'text-slate-300'}`}>
              {overview?.active_alerts ?? 0}
            </span>
          </div>

          <button
            onClick={onResetDemo}
            disabled={isResetting}
            title="Reset system to clean hackathon demo baseline"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 active:scale-95 transition text-xs font-semibold text-slate-200 border border-slate-700 disabled:opacity-50"
          >
            <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            <span>Reset Demo</span>
          </button>
        </div>
      </div>
    </header>
  );
}
