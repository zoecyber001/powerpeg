import React from 'react';
import { BedDouble, Zap, ShieldCheck, DollarSign } from 'lucide-react';

export default function ExecutiveBento({ overview, rooms }) {
  const totalRooms = rooms.length || 3;
  const occupiedCount = rooms.filter(r => !!r.active_booking).length;
  const authorisedCount = rooms.filter(r => r.authorisation?.authorised).length;
  const totalPower = rooms.reduce((acc, r) => acc + (r.latest_telemetry?.power || 0), 0);
  const occupancyPercent = Math.round((occupiedCount / totalRooms) * 100);

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500">Property Occupancy</span>
          <div className="h-8 w-8 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
            <BedDouble className="h-4 w-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
            {occupiedCount} / {totalRooms}
          </span>
          <span className="text-xs font-bold text-slate-500">({occupancyPercent}%)</span>
        </div>
        <div className="w-full bg-slate-100 h-1.5 rounded-full mt-3 overflow-hidden">
          <div 
            className="bg-blue-600 h-full rounded-full transition-all duration-500" 
            style={{ width: `${occupancyPercent}%` }}
          />
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500">Electricity Enabled</span>
          <div className="h-8 w-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
            <ShieldCheck className="h-4 w-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
            {authorisedCount}
          </span>
          <span className="text-xs font-medium text-slate-500">of {totalRooms} rooms powered</span>
        </div>
        <div className="flex items-center gap-2 mt-3 text-[11px] text-emerald-700 font-semibold">
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500 animate-pulse" />
          <span>Checkout cutoff armed</span>
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500">Live Active Demand</span>
          <div className="h-8 w-8 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
            <Zap className="h-4 w-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-extrabold text-slate-900 font-mono tracking-tight">
            {totalPower.toFixed(2)}
          </span>
          <span className="text-xs font-bold text-slate-500">kW</span>
        </div>
        <div className="flex items-center gap-1.5 mt-3 text-[11px] text-slate-400">
          <span>Continuous software telemetry</span>
        </div>
      </div>

      <div className="bg-white border border-slate-200/90 rounded-2xl p-4 shadow-card">
        <div className="flex items-center justify-between mb-3">
          <span className="text-xs font-semibold text-slate-500">Unbilled Waste Prevented</span>
          <div className="h-8 w-8 rounded-xl bg-purple-50 text-purple-600 flex items-center justify-center">
            <DollarSign className="h-4 w-4" />
          </div>
        </div>
        <div className="flex items-baseline gap-1.5">
          <span className="text-2xl font-extrabold text-slate-900 tracking-tight">
            $38.50
          </span>
          <span className="text-xs font-semibold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded">
            Auto Cutoff
          </span>
        </div>
        <div className="flex items-center gap-1.5 mt-3 text-[11px] text-slate-400">
          <span>Zero power wasted post-checkout</span>
        </div>
      </div>
    </div>
  );
}
