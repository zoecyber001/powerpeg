import React from 'react';
import { 
  Zap, Power, ShieldAlert, ShieldCheck, UserCheck, CreditCard, 
  Wifi, WifiOff, AlertOctagon, Flame, Clock
} from 'lucide-react';
import { 
  AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer 
} from 'recharts';

export default function RoomHero({
  roomDetail,
  telemetryHistory,
  injectionMode,
  onConfirmPayment,
  onCreateBooking,
  onCancelBooking,
  onSetInjection,
  isActionLoading
}) {
  if (!roomDetail) return null;

  const { room, device, active_booking, authorisation, latest_telemetry } = roomDetail;
  const isAuth = authorisation?.authorised ?? false;
  const isOnline = device?.connection_status === 'online';
  const relayState = device?.reported_relay_state ?? 'OFF';

  const chartData = (telemetryHistory || []).map((t, idx) => ({
    time: t.observed_at ? new Date(t.observed_at).toLocaleTimeString() : `${idx}s`,
    power: Number(t.power?.toFixed(2) || 0),
    voltage: Number(t.voltage?.toFixed(1) || 230),
    current: Number(t.current?.toFixed(2) || 0),
  }));

  return (
    <div className="bg-[#0F172A] border border-slate-800 rounded-2xl overflow-hidden shadow-2xl relative">
      <div className="bg-gradient-to-r from-slate-900 via-slate-800 to-slate-900 px-6 py-4 border-b border-slate-800 flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
            <Zap className="h-5 w-5 text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-bold text-white tracking-wide">{room.room_code}</span>
              <span className="text-xs text-slate-400">({room.display_name})</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
                Primary Physical Hardware Target
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className={`flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider border ${
            isAuth 
              ? 'bg-emerald-500/15 border-emerald-500/30 text-emerald-300' 
              : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
          }`}>
            {isAuth ? <ShieldCheck className="h-4 w-4" /> : <ShieldAlert className="h-4 w-4" />}
            <span>{isAuth ? 'ELECTRICITY AUTHORISED' : 'ACCESS DENIED / REVOKED'}</span>
          </div>
        </div>
      </div>

      <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        <div className="lg:col-span-4 flex flex-col gap-4">
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Edge Controller (AZ3166)
              </span>
              <span className={`flex items-center gap-1.5 text-xs font-bold px-2 py-0.5 rounded ${
                isOnline 
                  ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' 
                  : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'
              }`}>
                {isOnline ? <Wifi className="h-3 w-3" /> : <WifiOff className="h-3 w-3" />}
                {isOnline ? 'CONNECTED' : 'OFFLINE'}
              </span>
            </div>

            <div className="relative rounded-lg bg-black border-2 border-slate-700 p-3.5 font-mono text-emerald-400 shadow-inner">
              <div className="absolute top-2 right-2 flex items-center gap-1">
                <span className="text-[9px] text-slate-500">RGB:</span>
                <span className={`h-2.5 w-2.5 rounded-full ${
                  relayState === 'ON' 
                    ? 'bg-emerald-400 shadow-[0_0_8px_#22c55e]' 
                    : 'bg-rose-500 shadow-[0_0_8px_#ef4444]'
                }`} />
              </div>
              <div className="text-[10px] text-emerald-500/70 uppercase tracking-widest mb-1.5">
                AZ3166 OLED (128x64)
              </div>
              <div className="space-y-1 text-xs">
                <div className="text-emerald-300 font-bold">PegPower | {room.room_code}</div>
                <div className="text-slate-400 text-[11px]">DevID: {device?.device_code || 'AZ3166-01'}</div>
                <div className="flex items-center justify-between pt-1 border-t border-emerald-950">
                  <span className="text-[11px]">RELAY STATE:</span>
                  <span className={`font-bold px-1 rounded text-[11px] ${
                    relayState === 'ON' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'
                  }`}>
                    [{relayState}]
                  </span>
                </div>
                <div className="text-[10px] text-slate-500 truncate">
                  Status: {isAuth ? 'Power Authorized' : 'Power Revoked'}
                </div>
              </div>
            </div>

            <div className="mt-3 flex items-center justify-between text-xs text-slate-400 px-1">
              <span>Firmware: v{device?.firmware_version || '1.0.0'}</span>
              <span>Last Heartbeat: {device?.last_seen_at ? new Date(device.last_seen_at).toLocaleTimeString() : 'Never'}</span>
            </div>
          </div>

          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 flex-1 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  Stay & Payment Authorisation
                </span>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded uppercase border ${
                  active_booking?.booking_status === 'confirmed' 
                    ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' 
                    : 'bg-slate-800 border-slate-700 text-slate-400'
                }`}>
                  {active_booking?.booking_status || 'Vacant'}
                </span>
              </div>

              {active_booking ? (
                <div className="space-y-2 text-xs mb-4">
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Guest:</span>
                    <span className="font-semibold text-white">{active_booking.guest_label}</span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-slate-400">Payment Status:</span>
                    <span className={`font-bold uppercase px-1.5 py-0.5 rounded text-[10px] ${
                      active_booking.payment?.payment_status === 'confirmed'
                        ? 'bg-emerald-500/15 text-emerald-300'
                        : active_booking.payment?.payment_status === 'pending'
                        ? 'bg-amber-500/15 text-amber-300'
                        : 'bg-rose-500/15 text-rose-300'
                    }`}>
                      {active_booking.payment?.payment_status || 'Pending'} (Simulated)
                    </span>
                  </div>
                  <div className="text-[11px] text-slate-400 border-t border-slate-800 pt-2 flex items-center gap-1.5">
                    <Clock className="h-3 w-3 text-slate-500" />
                    <span>{authorisation?.reason || 'Evaluation in progress'}</span>
                  </div>
                </div>
              ) : (
                <div className="py-4 text-center text-xs text-slate-500">
                  No active booking for this room.
                </div>
              )}
            </div>

            <div className="space-y-2 pt-2 border-t border-slate-800">
              {!active_booking ? (
                <button
                  onClick={() => onCreateBooking(room.id)}
                  disabled={isActionLoading}
                  className="w-full py-2 px-3 rounded-lg bg-emerald-600 hover:bg-emerald-500 active:scale-98 transition text-xs font-semibold text-white flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-600/20 disabled:opacity-50"
                >
                  <UserCheck className="h-4 w-4" />
                  <span>Check In Demo Guest (Pending Pay)</span>
                </button>
              ) : active_booking.payment?.payment_status === 'pending' ? (
                <button
                  onClick={() => onConfirmPayment(active_booking.id)}
                  disabled={isActionLoading}
                  className="w-full py-2.5 px-3 rounded-lg bg-gradient-to-r from-emerald-600 to-teal-500 hover:from-emerald-500 hover:to-teal-400 active:scale-98 transition text-xs font-bold text-white flex items-center justify-center gap-1.5 shadow-lg shadow-emerald-500/25 animate-pulse disabled:opacity-50"
                >
                  <CreditCard className="h-4 w-4" />
                  <span>Confirm Simulated Payment (Triggers ON)</span>
                </button>
              ) : (
                <button
                  onClick={() => onCancelBooking(active_booking.id)}
                  disabled={isActionLoading}
                  className="w-full py-2 px-3 rounded-lg bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 active:scale-98 transition text-xs font-semibold flex items-center justify-center gap-1.5 disabled:opacity-50"
                >
                  <Power className="h-4 w-4" />
                  <span>Revoke Stay / Checkout (Triggers OFF)</span>
                </button>
              )}
            </div>
          </div>
        </div>

        <div className="lg:col-span-8 flex flex-col gap-4">
          <div className="bg-slate-950/70 border border-slate-800 rounded-xl p-4 flex-1 flex flex-col">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                  Live Electrical Telemetry
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-extrabold uppercase tracking-wider bg-amber-500/10 border border-amber-500/30 text-amber-400">
                  ⚠ SIMULATED SOFTWARE READINGS
                </span>
              </div>
              <span className="text-[11px] text-slate-500">
                Independent Simulator Engine (2s updates)
              </span>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-2.5">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">Active Power</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className={`text-xl font-bold font-mono ${
                    (latest_telemetry?.power || 0) > 0.05 ? 'text-emerald-400' : 'text-slate-400'
                  }`}>
                    {latest_telemetry?.power?.toFixed(2) || '0.00'}
                  </span>
                  <span className="text-xs text-slate-500">kW</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-2.5">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">AC Current</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="text-xl font-bold font-mono text-cyan-400">
                    {latest_telemetry?.current?.toFixed(2) || '0.00'}
                  </span>
                  <span className="text-xs text-slate-500">A</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-2.5">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">Voltage (RMS)</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="text-xl font-bold font-mono text-indigo-400">
                    {latest_telemetry?.voltage?.toFixed(1) || '230.0'}
                  </span>
                  <span className="text-xs text-slate-500">V</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800/80 rounded-lg p-2.5">
                <span className="text-[10px] font-medium text-slate-400 block uppercase">Accumulated</span>
                <div className="flex items-baseline gap-1 mt-0.5">
                  <span className="text-xl font-bold font-mono text-slate-200">
                    {latest_telemetry?.energy?.toFixed(3) || '0.000'}
                  </span>
                  <span className="text-xs text-slate-500">kWh</span>
                </div>
              </div>
            </div>

            <div className="flex-1 min-h-[160px] w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 5, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="powerGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0.0}/>
                    </linearGradient>
                  </defs>
                  <XAxis dataKey="time" stroke="#475569" fontSize={10} tickLine={false} />
                  <YAxis stroke="#475569" fontSize={10} domain={[0, 'auto']} tickLine={false} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', borderRadius: '8px', fontSize: '11px' }}
                    labelStyle={{ color: '#94a3b8' }}
                  />
                  <Area 
                    type="monotone" 
                    dataKey="power" 
                    name="Power (kW)"
                    stroke="#10b981" 
                    strokeWidth={2}
                    fillOpacity={1} 
                    fill="url(#powerGrad)" 
                    isAnimationActive={false}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-4 pt-3 border-t border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-1.5 text-xs text-slate-400">
                <Flame className="h-4 w-4 text-amber-400" />
                <span className="font-semibold text-slate-300">Pitch Controls:</span>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => onSetInjection(room.id, 'NORMAL')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition border ${
                    injectionMode === 'NORMAL'
                      ? 'bg-slate-700 text-white border-slate-500'
                      : 'bg-slate-900 text-slate-400 border-slate-800 hover:text-white'
                  }`}
                >
                  Normal Load
                </button>

                <button
                  onClick={() => onSetInjection(room.id, 'FORCE_ROGUE_DRAW')}
                  className={`px-2.5 py-1 rounded text-xs font-semibold transition border flex items-center gap-1 ${
                    injectionMode === 'FORCE_ROGUE_DRAW'
                      ? 'bg-rose-600 text-white border-rose-500 animate-pulse'
                      : 'bg-rose-950/40 text-rose-300 border-rose-800 hover:bg-rose-900/50'
                  }`}
                >
                  <AlertOctagon className="h-3 w-3" />
                  <span>Simulate Rogue Power Draw</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
