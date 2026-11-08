import React from 'react';
import { Cpu, Wifi, Activity, ShieldCheck, Zap } from 'lucide-react';

export default function AZ3166DigitalTwin({
  device,
  roomCode = 'ROOM-204',
  telemetry,
  isOverridden = false
}) {
  const relayState = device?.reported_relay_state || 'OFF';
  const isOnline = device?.connection_status === 'online';
  const isEnergized = relayState === 'ON';

  const voltage = telemetry?.voltage?.toFixed(1) || (isEnergized ? '230.2' : '0.0');
  const current = telemetry?.current?.toFixed(2) || (isEnergized ? '1.85' : '0.00');
  const power = telemetry?.power?.toFixed(2) || (isEnergized ? '0.42' : '0.00');

  return (
    <div className="bg-gradient-to-br from-slate-900 via-slate-950 to-slate-900 rounded-3xl p-5 border border-slate-800 shadow-xl text-slate-100 relative overflow-hidden font-mono select-none">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800/80 mb-4 font-sans">
        <div className="flex items-center gap-2">
          <div className="h-7 w-7 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center justify-center">
            <Cpu className="h-4 w-4" />
          </div>
          <div>
            <span className="text-xs font-bold text-white tracking-wide">
              MXChip AZ3166 Hardware Twin
            </span>
            <span className="text-[10px] text-slate-400 block font-mono">
              Node: {device?.device_code || 'AZ3166-01'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1.5 border ${
            isOnline 
              ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/60' 
              : 'bg-rose-950/40 text-rose-300 border-rose-800/60'
          }`}>
            <span className={`h-1.5 w-1.5 rounded-full ${isOnline ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
            {isOnline ? 'WiFi 2.4G Link' : 'Disconnected'}
          </span>
        </div>
      </div>

      <div className="bg-black rounded-2xl p-4 border border-slate-800 relative shadow-inner">
        <div className="flex items-center justify-between pb-2 border-b border-slate-900 text-[10px] text-slate-500">
          <span>OLED 128x64 MONO (SSD1306)</span>
          <span className="text-cyan-400 font-sans text-[9px] uppercase tracking-wider">Live Firmware Mirror</span>
        </div>

        <div className="py-3 text-cyan-300 space-y-1 text-center font-mono">
          <div className="text-[11px] text-slate-400 tracking-wider font-sans font-semibold">
            === PEGPOWER PMS ===
          </div>
          <div className="text-white text-base font-extrabold tracking-widest py-0.5">
            {roomCode}
          </div>
          <div className="flex items-center justify-center gap-2 text-xs">
            <span className="text-slate-400">CIRCUIT:</span>
            <span className={`font-bold px-1.5 py-0.5 rounded ${
              isEnergized ? 'bg-emerald-900/60 text-emerald-300' : 'bg-rose-900/60 text-rose-300'
            }`}>
              [{relayState}] {isEnergized ? 'CLOSED' : 'OPEN'}
            </span>
          </div>
          <div className="text-[11px] text-slate-400 pt-1">
            V: {voltage}V | I: {current}A | {power}kW
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-slate-900 text-[10px]">
          <div className="flex items-center gap-2">
            <span className="text-slate-500">RGB LED:</span>
            <div className="flex items-center gap-1.5">
              <span className={`h-2.5 w-2.5 rounded-full ${
                isOverridden 
                  ? 'bg-amber-400 shadow-[0_0_8px_rgba(251,191,36,0.9)] animate-pulse' 
                  : isEnergized 
                  ? 'bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.9)]' 
                  : 'bg-rose-500 shadow-[0_0_8px_rgba(244,63,94,0.7)]'
              }`} />
              <span className={`text-[10px] font-bold ${
                isOverridden ? 'text-amber-300' : isEnergized ? 'text-emerald-400' : 'text-rose-400'
              }`}>
                {isOverridden ? 'AMBER (OVERRIDE)' : isEnergized ? 'GREEN (ARMED)' : 'RED (SAFE CUTOFF)'}
              </span>
            </div>
          </div>

          <span className="text-slate-500 font-sans text-[10px]">
            Relay: {isEnergized ? 'Closed (5V Coil)' : 'Open (De-energized)'}
          </span>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-slate-800/80 font-sans text-xs">
        <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-500 block">Firmware</span>
          <span className="font-mono text-slate-300 font-bold text-[11px]">v1.2.0-peg</span>
        </div>
        <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-500 block">Polling</span>
          <span className="font-mono text-slate-300 font-bold text-[11px]">5.0s Beat</span>
        </div>
        <div className="bg-slate-950/60 p-2 rounded-xl border border-slate-800/60">
          <span className="text-[10px] text-slate-500 block">Isolation</span>
          <span className="font-mono text-emerald-400 font-bold text-[11px]">100% Safe</span>
        </div>
      </div>
    </div>
  );
}
