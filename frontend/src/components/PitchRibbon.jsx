import React, { useState } from 'react';
import { 
  Sparkles, CheckCircle2, Power, AlertTriangle, Clock, 
  RotateCcw, ChevronDown, ChevronUp, Play, Zap, ShieldCheck
} from 'lucide-react';

export default function PitchRibbon({
  onRunScenario,
  onResetDemo,
  isResetting,
  currentScenario
}) {
  const [isCollapsed, setIsCollapsed] = useState(false);

  const scenarios = [
    {
      id: 'CHECK_IN_FLOW',
      title: '1. Check-In & Power Release',
      desc: 'Guest checks in & pays -> Workpeg hook triggers -> AZ3166 relay closes -> Power ON',
      icon: Zap,
      color: 'emerald'
    },
    {
      id: 'CHECK_OUT_FLOW',
      title: '2. Express Checkout Cutoff',
      desc: 'Guest departs -> Circuit instantly cuts power -> Halts standby waste',
      icon: Power,
      color: 'slate'
    },
    {
      id: 'ROGUE_DRAW_ALERT',
      title: '3. Rogue Power Anomaly',
      desc: 'Injects 1.45 kW into vacant Room 204 -> Workpeg raises critical security alert in < 2s',
      icon: AlertTriangle,
      color: 'rose'
    },
    {
      id: 'HOUSEKEEPING_OVERRIDE',
      title: '4. Housekeeping (30m)',
      desc: 'Staff cleaning power override with 30-min auto-expiration countdown',
      icon: Clock,
      color: 'amber'
    }
  ];

  return (
    <div className="bg-white border-b border-slate-200/90 shadow-sm relative z-20">
      <div className="max-w-7xl mx-auto px-6 py-2.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
          <span className="text-xs font-extrabold uppercase tracking-wider text-slate-800 flex items-center gap-1.5">
            <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
            <span>Interactive Pitch Scenarios</span>
          </span>
          <span className="hidden md:inline-block text-[11px] font-medium text-slate-400">
            • 1-click end-to-end user stories for judges
          </span>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={onResetDemo}
            disabled={isResetting}
            className="px-3 py-1 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-semibold transition flex items-center gap-1.5 disabled:opacity-50"
          >
            <RotateCcw className={`h-3 w-3 ${isResetting ? 'animate-spin' : ''}`} />
            <span>Reset Demo</span>
          </button>

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition"
          >
            {isCollapsed ? <ChevronDown className="h-4 w-4" /> : <ChevronUp className="h-4 w-4" />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="max-w-7xl mx-auto px-6 pb-3 pt-1">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-2.5">
            {scenarios.map((sc) => {
              const Icon = sc.icon;
              const isActive = currentScenario === sc.id;

              return (
                <button
                  key={sc.id}
                  onClick={() => onRunScenario(sc.id)}
                  className={`p-2.5 rounded-xl border text-left transition flex items-start gap-2.5 ${
                    isActive
                      ? 'bg-emerald-50 border-emerald-300 ring-2 ring-emerald-100 shadow-sm'
                      : 'bg-slate-50/70 hover:bg-white border-slate-200/90 hover:border-slate-300 hover:shadow-sm'
                  }`}
                >
                  <div className={`h-7 w-7 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${
                    sc.color === 'emerald' ? 'bg-emerald-100 text-emerald-700' :
                    sc.color === 'rose' ? 'bg-rose-100 text-rose-700' :
                    sc.color === 'amber' ? 'bg-amber-100 text-amber-700' :
                    'bg-slate-200 text-slate-700'
                  }`}>
                    <Icon className="h-3.5 w-3.5" />
                  </div>

                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-1">
                      <span className="font-extrabold text-xs text-slate-900 truncate">
                        {sc.title}
                      </span>
                      <Play className="h-2.5 w-2.5 text-slate-400 shrink-0" />
                    </div>
                    <p className="text-[10px] text-slate-500 leading-tight mt-0.5 line-clamp-2">
                      {sc.desc}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
