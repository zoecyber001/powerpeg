import React from 'react';
import { ShieldCheck, ShieldAlert } from 'lucide-react';

export default function MultiRoomGrid({ rooms }) {
  const secondaryRooms = (rooms || []).filter(r => r.room.room_code !== 'ROOM-204');

  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-sm font-bold uppercase tracking-wider text-white">
            Multi-Room Scaling Fleet
          </h2>
          <p className="text-xs text-slate-400">
            Virtual controllers running parallel telemetry & authorization evaluation
          </p>
        </div>
        <span className="text-xs text-slate-500 font-mono">
          {secondaryRooms.length} Virtual Nodes
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {secondaryRooms.map(({ room, device, active_booking, authorisation, latest_telemetry }) => {
          const isAuth = authorisation?.authorised ?? false;
          const power = latest_telemetry?.power || 0;

          return (
            <div 
              key={room.id}
              className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 hover:border-slate-700 transition"
            >
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className="font-bold text-white text-sm">{room.room_code}</span>
                  <span className="text-xs text-slate-400">{room.display_name}</span>
                </div>
                <span className={`flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase border ${
                  isAuth 
                    ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-300' 
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}>
                  {isAuth ? <ShieldCheck className="h-3 w-3" /> : <ShieldAlert className="h-3 w-3" />}
                  {isAuth ? 'AUTHORISED' : 'DENIED'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-xs mb-3">
                <div className="bg-slate-900/40 p-2 rounded border border-slate-800/50">
                  <span className="text-[10px] text-slate-400 block">Stay Status</span>
                  <span className="font-semibold text-slate-200 truncate block">
                    {active_booking?.guest_label || 'No Guest / Vacant'}
                  </span>
                </div>
                <div className="bg-slate-900/40 p-2 rounded border border-slate-800/50">
                  <span className="text-[10px] text-slate-400 block">Virtual Load (Simulated)</span>
                  <span className={`font-mono font-bold ${power > 0.05 ? 'text-emerald-400' : 'text-slate-400'}`}>
                    {power.toFixed(2)} kW
                  </span>
                </div>
              </div>

              <div className="flex items-center justify-between text-[11px] text-slate-500 pt-2 border-t border-slate-800">
                <span>Controller: {device?.device_code || 'None'}</span>
                <span>Relay: [{device?.reported_relay_state || 'OFF'}]</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
