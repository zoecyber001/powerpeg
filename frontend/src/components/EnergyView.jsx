import React from 'react';
import { Zap, TrendingDown, ArrowUpRight, BarChart2 } from 'lucide-react';
import { ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, BarChart, Bar, CartesianGrid } from 'recharts';

export default function EnergyView({ rooms, telemetryHistory }) {
  const chartData = (telemetryHistory || []).map((t, idx) => ({
    time: t.observed_at ? new Date(t.observed_at).toLocaleTimeString() : `${idx}s`,
    room204: Number(t.power?.toFixed(2) || 0),
    propertyTotal: Number((t.power + 0.95).toFixed(2))
  }));

  const roomComparison = rooms.map(r => ({
    room: r.room.room_code,
    power: Number((r.latest_telemetry?.power || 0).toFixed(2)),
    status: r.authorisation?.authorised ? 'Authorized' : 'Cut'
  }));

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 block mb-1">Peak Load Today</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-slate-900 font-mono">2.45</span>
            <span className="text-xs font-bold text-slate-500">kW</span>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold mt-2 block">
            Within 5.0 kW property capacity
          </span>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 block mb-1">Average Room Consumption</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-slate-900 font-mono">0.85</span>
            <span className="text-xs font-bold text-slate-500">kW / occupied room</span>
          </div>
          <span className="text-[11px] text-slate-400 mt-2 block">
            Standard AC + lighting baseline
          </span>
        </div>

        <div className="bg-white border border-slate-200/90 rounded-2xl p-5 shadow-card">
          <span className="text-xs font-semibold text-slate-500 block mb-1">Monthly Loss Prevention</span>
          <div className="flex items-baseline gap-1.5">
            <span className="text-2xl font-extrabold text-emerald-700 font-mono">$184.20</span>
          </div>
          <span className="text-[11px] text-emerald-700 font-semibold mt-2 block">
            Estimated power saved outside stays
          </span>
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
              Property Real-Time Electricity Demand
            </h2>
            <p className="text-xs text-slate-400">Continuous aggregated load telemetry across all circuits</p>
          </div>
          <span className="text-xs px-2.5 py-1 bg-emerald-50 text-emerald-700 rounded-full font-bold border border-emerald-200">
            Live Stream
          </span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
              <defs>
                <linearGradient id="totalLoadGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
              <XAxis dataKey="time" stroke="#94A3B8" fontSize={11} tickLine={false} />
              <YAxis stroke="#94A3B8" fontSize={11} tickLine={false} />
              <Tooltip
                contentStyle={{ backgroundColor: '#FFFFFF', borderColor: '#E2E8F0', borderRadius: '10px', fontSize: '12px', boxShadow: '0 4px 6px -1px rgba(0,0,0,0.05)' }}
              />
              <Area
                type="monotone"
                dataKey="propertyTotal"
                name="Total Property (kW)"
                stroke="#059669"
                strokeWidth={2.5}
                fill="url(#totalLoadGrad)"
                isAnimationActive={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-6 shadow-card">
        <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide mb-4">
          Active Circuit Distribution By Room
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {rooms.map(r => (
            <div key={r.room.id} className="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
              <div>
                <p className="font-bold text-slate-800 text-sm">{r.room.room_code}</p>
                <p className="text-[11px] text-slate-400">{r.room.display_name}</p>
              </div>
              <div className="text-right">
                <p className="font-mono font-bold text-slate-900 text-sm">
                  {(r.latest_telemetry?.power || 0).toFixed(2)} kW
                </p>
                <span className={`text-[10px] font-bold uppercase ${
                  r.authorisation?.authorised ? 'text-emerald-700' : 'text-slate-400'
                }`}>
                  {r.authorisation?.authorised ? 'Authorized' : 'Secured'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
