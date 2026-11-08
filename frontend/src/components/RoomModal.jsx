import React, { useState } from 'react';
import { X, Zap, Power, User, CheckCircle2, AlertTriangle, ShieldCheck, Cpu } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip } from 'recharts';

export default function RoomModal({
  roomDetail,
  telemetryHistory,
  onClose,
  onManualOverride,
  isOverriding
}) {
  if (!roomDetail) return null;

  const { room, device, active_booking, authorisation, latest_telemetry } = roomDetail;
  const isAuth = authorisation?.authorised ?? false;
  const power = latest_telemetry?.power || 0;
  const [overrideReason, setOverrideReason] = useState('Staff operational override');

  const chartData = (telemetryHistory || []).map((t, idx) => ({
    time: t.observed_at ? new Date(t.observed_at).toLocaleTimeString() : `${idx}s`,
    power: Number(t.power?.toFixed(2) || 0)
  }));

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fade-in">
      <div className="bg-white border border-slate-200 rounded-2xl w-full max-w-2xl overflow-hidden shadow-2xl relative">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50/60">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-white border border-slate-200 flex items-center justify-center shadow-sm">
              <Zap className="h-5 w-5 text-emerald-600" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-extrabold text-slate-900">{room.room_code}</h2>
                <span className="text-xs text-slate-500">• {room.display_name}</span>
              </div>
              <p className="text-[11px] text-slate-400">Smart Power Circuit Details</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 space-y-5">
          <div className="grid grid-cols-2 gap-4">
            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-xs font-semibold text-slate-500 block mb-1">Circuit State</span>
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${isAuth ? 'bg-emerald-500' : 'bg-slate-400'}`} />
                <span className="text-sm font-bold text-slate-900">
                  {isAuth ? 'Power Enabled (230V)' : 'Power Cut (0V)'}
                </span>
              </div>
              <p className="text-[11px] text-slate-500 mt-2">
                {authorisation?.reason || 'Evaluation in sync'}
              </p>
            </div>

            <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
              <span className="text-xs font-semibold text-slate-500 block mb-1">Live Power Draw</span>
              <span className={`text-2xl font-bold font-mono ${power > 0.05 ? 'text-emerald-700' : 'text-slate-400'}`}>
                {power.toFixed(2)} kW
              </span>
              <p className="text-[11px] text-slate-500 mt-2">
                Switch: {device ? `${device.device_code} (${device.connection_status})` : 'Virtual'}
              </p>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">
                Live Load Waveform (kW)
              </span>
              <span className="text-[10px] font-semibold text-slate-400">
                Independent simulator telemetry
              </span>
            </div>
            <div className="h-36 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 0, right: 0, left: -25, bottom: 0 }}>
                  <defs>
                    <linearGradient id="powerSparkLight" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.25}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#94A3B8" fontSize={10} tickLine={false} />
                  <YAxis stroke="#94A3B8" fontSize={10} tickLine={false} />
                  <Tooltip
                    contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '10px', fontSize: '11px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}
                  />
                  <Area
                    type="monotone"
                    dataKey="power"
                    stroke="#059669"
                    strokeWidth={2}
                    fill="url(#powerSparkLight)"
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-50 border border-slate-100">
            <span className="text-xs font-bold text-slate-700 block mb-2">Staff Manual Override</span>
            <div className="flex flex-col sm:flex-row items-center gap-2">
              <input
                type="text"
                value={overrideReason}
                onChange={(e) => setOverrideReason(e.target.value)}
                placeholder="Reason (e.g. VIP guest arrival, maintenance)"
                className="w-full px-3 py-2 rounded-xl bg-white border border-slate-200 text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:border-emerald-500 shadow-sm"
              />
              <button
                onClick={() => onManualOverride(room.id, !isAuth, overrideReason)}
                disabled={isOverriding}
                className={`whitespace-nowrap px-4 py-2 rounded-xl text-xs font-bold transition ${
                  isAuth
                    ? 'bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200'
                    : 'bg-emerald-600 hover:bg-emerald-700 text-white shadow-sm'
                }`}
              >
                {isAuth ? 'Force Power Off' : 'Force Power On'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
