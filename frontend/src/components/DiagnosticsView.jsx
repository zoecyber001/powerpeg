import React from 'react';
import { 
  Cpu, Flame, ShieldAlert, CheckCircle2, RotateCcw, 
  Wifi, Server, ShieldCheck, Activity, Terminal
} from 'lucide-react';

export default function DiagnosticsView({
  room204Detail,
  injectionMode,
  onSetInjection,
  onResetDemo,
  isResetting
}) {
  const device = room204Detail?.device;
  const relayState = device?.reported_relay_state || 'OFF';
  const isOnline = device?.connection_status === 'online';

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-xl font-extrabold text-slate-900 tracking-tight">
          Switch Diagnostics & Scenario Lab
        </h2>
        <p className="text-xs font-medium text-slate-500 mt-0.5">
          Hardware telemetry verification, MXChip AZ3166 inspection, and live scenario simulation
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="h-8 w-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                <Cpu className="h-4 w-4" />
              </div>
              <div>
                <h3 className="text-sm font-extrabold text-slate-900">
                  MXChip AZ3166 IoT Switch
                </h3>
                <p className="text-[11px] text-slate-500">Physical access control node (Room 204)</p>
              </div>
            </div>

            <span className={`text-[11px] font-bold px-2.5 py-1 rounded-full flex items-center gap-1.5 ${
              isOnline 
                ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                : 'bg-rose-50 text-rose-700 border border-rose-200'
            }`}>
              <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? 'bg-emerald-500 animate-pulse' : 'bg-rose-500'}`} />
              {isOnline ? 'Online & Synced' : 'Offline'}
            </span>
          </div>

          <div className="bg-slate-900 rounded-2xl p-4 text-emerald-400 font-mono shadow-inner border border-slate-800">
            <div className="flex items-center justify-between pb-2 border-b border-slate-800 text-[10px] text-slate-400">
              <span>AZ3166 OLED 128x64 DISPLAY</span>
              <span className="text-slate-500">I2C SSD1306</span>
            </div>
            <div className="py-4 space-y-1 text-center">
              <div className="text-slate-400 text-xs tracking-wider font-sans uppercase">== PEGPOWER PMS ==</div>
              <div className="text-white text-base font-extrabold tracking-widest">ROOM-204</div>
              <div className="flex items-center justify-center gap-2 mt-1">
                <span className="text-xs text-slate-400">CIRCUIT:</span>
                <span className={`px-2 py-0.5 rounded text-xs font-bold ${
                  relayState === 'ON' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                }`}>
                  [{relayState}]
                </span>
              </div>
              <div className="text-[10px] text-slate-500 mt-2">
                RGB LED: {relayState === 'ON' ? 'GREEN (ARMED)' : 'RED (SAFE CUTOFF)'}
              </div>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 text-[11px] block">Device Serial</span>
              <span className="font-mono font-bold text-slate-800">{device?.device_code || 'AZ3166-01'}</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 text-[11px] block">Firmware Build</span>
              <span className="font-mono font-bold text-slate-800">v1.2.0-workpeg</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 text-[11px] block">Heartbeat Cadence</span>
              <span className="font-bold text-slate-800">Every 5.0s</span>
            </div>
            <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
              <span className="text-slate-400 text-[11px] block">Simulated Relay</span>
              <span className={`font-bold ${relayState === 'ON' ? 'text-emerald-600' : 'text-slate-600'}`}>
                {relayState === 'ON' ? 'Active Closed' : 'Safe Open'}
              </span>
            </div>
          </div>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card space-y-5">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
              <Flame className="h-4 w-4" />
            </div>
            <div>
              <h3 className="text-sm font-extrabold text-slate-900">
                Demonstration Scenario Injection
              </h3>
              <p className="text-[11px] text-slate-500">Live pitch triggers for anomaly & anti-theft workflows</p>
            </div>
          </div>

          <p className="text-xs text-slate-600 leading-relaxed">
            Test the automated reconciliation engine. When electricity is drawn inside a room without a paid booking, PegPower flags a security anomaly within 2 seconds.
          </p>

          <div className="space-y-3 pt-2">
            <button
              onClick={() => onSetInjection(room204Detail?.room?.id, 'FORCE_ROGUE_DRAW')}
              className={`w-full p-4 rounded-xl text-left border transition flex items-start justify-between gap-4 ${
                injectionMode === 'FORCE_ROGUE_DRAW'
                  ? 'bg-rose-50 border-rose-300 ring-2 ring-rose-100'
                  : 'bg-white border-slate-200 hover:border-rose-300 hover:bg-rose-50/40'
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <ShieldAlert className="h-4 w-4 text-rose-600" />
                  <span className="text-xs font-extrabold text-rose-900">
                    Scenario A: Simulate Rogue Electricity Draw
                  </span>
                </div>
                <p className="text-[11px] text-rose-700/80 mt-1">
                  Injects 1.45 kW into Room 204 while circuit is unbilled to trigger real-time conflict detection.
                </p>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                injectionMode === 'FORCE_ROGUE_DRAW' ? 'bg-rose-600 text-white' : 'bg-slate-100 text-slate-600'
              }`}>
                {injectionMode === 'FORCE_ROGUE_DRAW' ? 'Active' : 'Trigger'}
              </span>
            </button>

            <button
              onClick={() => onSetInjection(room204Detail?.room?.id, 'NORMAL')}
              className={`w-full p-4 rounded-xl text-left border transition flex items-start justify-between gap-4 ${
                injectionMode === 'NORMAL'
                  ? 'bg-emerald-50 border-emerald-300 ring-2 ring-emerald-100'
                  : 'bg-white border-slate-200 hover:border-emerald-300 hover:bg-emerald-50/40'
              }`}
            >
              <div>
                <div className="flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-600" />
                  <span className="text-xs font-extrabold text-emerald-900">
                    Scenario B: Restore Normal Baseline
                  </span>
                </div>
                <p className="text-[11px] text-emerald-700/80 mt-1">
                  Restores standard software load profiles correlated strictly to PMS guest occupancy.
                </p>
              </div>
              <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase tracking-wider shrink-0 ${
                injectionMode === 'NORMAL' ? 'bg-emerald-600 text-white' : 'bg-slate-100 text-slate-600'
              }`}>
                {injectionMode === 'NORMAL' ? 'Active' : 'Restore'}
              </span>
            </button>
          </div>

          <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
            <span className="text-xs font-semibold text-slate-500">Reset Demo Environment</span>
            <button
              onClick={onResetDemo}
              disabled={isResetting}
              className="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <RotateCcw className={`h-3.5 w-3.5 ${isResetting ? 'animate-spin' : ''}`} />
              <span>{isResetting ? 'Resetting...' : 'Reset to Default'}</span>
            </button>
          </div>
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
        <h3 className="text-sm font-extrabold text-slate-900 mb-3">
          Architecture Boundaries & Safety Compliance
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="font-bold text-slate-800 block mb-1">Workpeg Peg Framework</span>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Native Workpeg app with custom schema hooks (<code className="text-emerald-700">on_payment_post_save</code>) that trigger circuit activation upon booking settlement.
            </p>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="font-bold text-slate-800 block mb-1">Hardware Isolation Safety</span>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              AZ3166 IoT board only controls firmware-level simulated relay and OLED/RGB LEDs. Zero physical mains voltage or live switching occurs.
            </p>
          </div>
          <div className="p-3 bg-slate-50 rounded-xl border border-slate-100">
            <span className="font-bold text-slate-800 block mb-1">2-Second Anomaly Loop</span>
            <p className="text-slate-500 text-[11px] leading-relaxed">
              Software telemetry simulator broadcasts voltage, current, and active kW. The reconciliation engine audits unauthorized draw every 2 seconds.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
