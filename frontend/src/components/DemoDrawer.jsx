import React from 'react';
import { X, Flame, ShieldAlert, Cpu, History, RotateCcw, CheckCircle2 } from 'lucide-react';

export default function DemoDrawer({
  isOpen,
  onClose,
  room204Detail,
  injectionMode,
  onSetInjection,
  auditEvents,
  onResetDemo,
  isResetting
}) {
  if (!isOpen) return null;

  const device = room204Detail?.device;
  const relayState = device?.reported_relay_state || 'OFF';

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#0C1222] border-l border-slate-800 shadow-2xl p-6 flex flex-col justify-between overflow-y-auto">
      <div>
        <div className="flex items-center justify-between pb-4 border-b border-slate-800 mb-6">
          <div className="flex items-center gap-2">
            <Cpu className="h-5 w-5 text-indigo-400" />
            <h2 className="text-sm font-bold text-white uppercase tracking-wider">
              Staff & Simulation Tools
            </h2>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg bg-slate-900 text-slate-400 hover:text-white border border-slate-800 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="space-y-6">
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
            <span className="text-xs font-bold text-slate-300 block mb-2 uppercase tracking-wide">
              Physical Hardware Switch (AZ3166)
            </span>
            <div className="rounded-lg bg-black border border-slate-800 p-3 font-mono text-emerald-400 text-xs space-y-1">
              <div className="flex items-center justify-between text-[11px] text-slate-500">
                <span>ROOM-204</span>
                <span className={`h-2 w-2 rounded-full ${relayState === 'ON' ? 'bg-emerald-400' : 'bg-rose-500'}`} />
              </div>
              <div className="text-white font-bold">Relay State: [{relayState}]</div>
              <div className="text-slate-400 text-[10px]">Device: {device?.device_code || 'AZ3166-01'}</div>
              <div className="text-slate-500 text-[10px]">Connection: {device?.connection_status || 'offline'}</div>
            </div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <Flame className="h-4 w-4 text-amber-400" />
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wide">
                Simulate Incident Scenarios
              </span>
            </div>
            <p className="text-[11px] text-slate-400 mb-3">
              Test automated theft and anomaly detection when rooms are vacant:
            </p>

            <div className="space-y-2">
              <button
                onClick={() => onSetInjection(room204Detail.room.id, 'FORCE_ROGUE_DRAW')}
                className={`w-full py-2.5 px-3 rounded-lg text-xs font-semibold transition border flex items-center justify-center gap-1.5 ${
                  injectionMode === 'FORCE_ROGUE_DRAW'
                    ? 'bg-rose-600 text-white border-rose-500'
                    : 'bg-rose-950/30 hover:bg-rose-950/50 text-rose-300 border-rose-800/80'
                }`}
              >
                <ShieldAlert className="h-3.5 w-3.5" />
                <span>Simulate Rogue Electricity Draw (Room 204)</span>
              </button>

              <button
                onClick={() => onSetInjection(room204Detail.room.id, 'NORMAL')}
                className={`w-full py-2 px-3 rounded-lg text-xs font-semibold transition border ${
                  injectionMode === 'NORMAL'
                    ? 'bg-slate-800 text-white border-slate-700'
                    : 'bg-slate-900 hover:bg-slate-800 text-slate-400 border-slate-800'
                }`}
              >
                Restore Normal Operations
              </button>
            </div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-bold text-slate-300 uppercase tracking-wide flex items-center gap-1.5">
                <History className="h-3.5 w-3.5 text-slate-400" />
                <span>Recent System Events</span>
              </span>
            </div>
            <div className="space-y-2 max-h-48 overflow-y-auto pr-1 text-[11px]">
              {(auditEvents || []).slice(0, 8).map(evt => (
                <div key={evt.id} className="p-2 rounded bg-slate-900/60 border border-slate-800/60">
                  <div className="flex items-center justify-between text-slate-300 font-medium">
                    <span>{evt.event_type}</span>
                    <span className="text-[10px] text-slate-500">
                      {new Date(evt.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="pt-4 border-t border-slate-800 mt-6">
        <button
          onClick={onResetDemo}
          disabled={isResetting}
          className="w-full py-2 px-3 rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold border border-slate-800 transition flex items-center justify-center gap-1.5 disabled:opacity-50"
        >
          <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin' : ''}`} />
          <span>Reset Demo to Clean State</span>
        </button>
      </div>
    </div>
  );
}
