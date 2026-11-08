import React from 'react';
import { AlertTriangle, AlertOctagon, CheckCircle2, ShieldAlert } from 'lucide-react';

export default function AlertsPanel({ alerts, onAcknowledgeAlert }) {
  const activeAlerts = (alerts || []).filter(a => a.status === 'ACTIVE');

  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-6 shadow-xl flex flex-col h-full">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <AlertTriangle className={`h-5 w-5 ${activeAlerts.length > 0 ? 'text-rose-400 animate-bounce' : 'text-slate-400'}`} />
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">
            Anomaly & Conflict Alerts (FR-12)
          </h2>
        </div>
        <span className={`px-2 py-0.5 rounded text-xs font-bold ${
          activeAlerts.length > 0 ? 'bg-rose-500/20 text-rose-300 border border-rose-500/30' : 'bg-slate-800 text-slate-400'
        }`}>
          {activeAlerts.length} Active
        </span>
      </div>

      <div className="space-y-3 flex-1 overflow-y-auto max-h-[320px] pr-1">
        {activeAlerts.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500">
            <CheckCircle2 className="h-8 w-8 text-emerald-500/40 mb-2" />
            <p className="text-xs">All electrical state vectors reconciled.</p>
            <p className="text-[11px] text-slate-600 mt-1">Zero unauthorized power draw detected.</p>
          </div>
        ) : (
          activeAlerts.map(alert => {
            const isCritical = alert.severity === 'CRITICAL';

            return (
              <div 
                key={alert.id}
                className={`p-3.5 rounded-xl border flex flex-col justify-between gap-3 ${
                  isCritical 
                    ? 'bg-rose-950/30 border-rose-800/80 text-rose-200' 
                    : 'bg-amber-950/20 border-amber-800/80 text-amber-200'
                }`}
              >
                <div>
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className="font-bold text-xs uppercase tracking-wider flex items-center gap-1.5">
                      <AlertOctagon className="h-3.5 w-3.5" />
                      {alert.alert_type}
                    </span>
                    <span className="text-[10px] opacity-75 font-mono">
                      {new Date(alert.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <p className="text-xs leading-relaxed text-slate-300">
                    {alert.description}
                  </p>
                </div>

                <div className="flex items-center justify-between pt-2 border-t border-slate-800/60">
                  <span className="text-[10px] uppercase font-bold tracking-wider px-1.5 py-0.5 rounded bg-black/40">
                    {alert.severity}
                  </span>
                  <button
                    onClick={() => onAcknowledgeAlert(alert.id)}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 active:scale-95 text-[11px] font-semibold text-white border border-slate-700 transition"
                  >
                    Acknowledge
                  </button>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
