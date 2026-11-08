import React, { useState } from 'react';
import { 
  X, Zap, Power, ShieldCheck, User, Clock, AlertTriangle, 
  Cpu, Activity, CreditCard, ShieldAlert 
} from 'lucide-react';
import { 
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip 
} from 'recharts';
import AZ3166DigitalTwin from './AZ3166DigitalTwin';

export default function RoomModal({
  roomDetail,
  telemetryHistory,
  onClose,
  onManualOverride,
  isOverriding
}) {
  const [overrideReason, setOverrideReason] = useState('');
  const [selectedDuration, setSelectedDuration] = useState(30);

  if (!roomDetail) return null;

  const { room, device, active_booking, authorisation, latest_telemetry, active_alerts } = roomDetail;
  const isAuth = authorisation?.authorised ?? false;
  const hasAlert = (active_alerts || []).length > 0;
  const isAZ3166 = device?.device_type === 'AZ3166';

  const chartData = (telemetryHistory || []).map((t, i) => ({
    time: t.recorded_at ? new Date(t.recorded_at).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' }) : `${i * 2}s`,
    power: Number(t.power?.toFixed(2) || 0),
    voltage: Number(t.voltage?.toFixed(1) || 0),
    current: Number(t.current?.toFixed(2) || 0),
  }));

  const handleApplyOverride = (targetState) => {
    onManualOverride(
      room.id,
      targetState,
      overrideReason.trim() || (targetState ? `Staff power override (${selectedDuration}m)` : 'Emergency staff cutoff'),
      selectedDuration
    );
    setOverrideReason('');
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col overflow-hidden">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`h-10 w-10 rounded-2xl flex items-center justify-center border ${
              isAuth 
                ? 'bg-emerald-50 text-emerald-600 border-emerald-100' 
                : 'bg-slate-100 text-slate-500 border-slate-200'
            }`}>
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-lg font-extrabold text-slate-900 font-mono">
                  {room.room_code}
                </h3>
                <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                  isAuth 
                    ? 'bg-emerald-50 text-emerald-700 border-emerald-200' 
                    : 'bg-slate-100 text-slate-600 border-slate-200'
                }`}>
                  {isAuth ? 'Circuit Energized' : 'Safe Cutoff'}
                </span>
              </div>
              <p className="text-xs font-medium text-slate-400">
                {room.display_name}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="p-6 overflow-y-auto space-y-6 flex-1">
          {isAZ3166 && (
            <div>
              <AZ3166DigitalTwin
                device={device}
                roomCode={room.room_code}
                telemetry={latest_telemetry}
                isOverridden={authorisation?.reason?.includes('override')}
              />
            </div>
          )}

          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-slate-800 uppercase tracking-wider flex items-center gap-1.5">
                <Activity className="h-3.5 w-3.5 text-slate-500" />
                <span>Live Electrical Telemetry (2-Second Frequency)</span>
              </span>
              <span className="text-xs font-mono font-bold text-slate-900">
                Current Draw: {latest_telemetry?.power?.toFixed(2) || '0.00'} kW
              </span>
            </div>

            <div className="h-36 w-full bg-slate-50 rounded-2xl border border-slate-200/80 p-2">
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData}>
                    <defs>
                      <linearGradient id="modalPowerGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10B981" stopOpacity={0.25} />
                        <stop offset="95%" stopColor="#10B981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <XAxis dataKey="time" hide />
                    <YAxis domain={[0, 'auto']} hide />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#0F172A',
                        borderRadius: '12px',
                        border: 'none',
                        color: '#FFF',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="power"
                      stroke="#10B981"
                      strokeWidth={2}
                      fill="url(#modalPowerGrad)"
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="h-full flex items-center justify-center text-xs text-slate-400 font-mono">
                  Circuit de-energized. Zero telemetry load.
                </div>
              )}
            </div>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
            <span className="text-xs font-bold text-slate-800 uppercase tracking-wider block">
              Guest Reservation & Billing Folio
            </span>
            {active_booking ? (
              <div className="grid grid-cols-2 gap-3 text-xs">
                <div>
                  <span className="text-slate-400 block text-[11px]">Guest Name</span>
                  <span className="font-bold text-slate-800">{active_booking.guest_label}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Folio Status</span>
                  <span className="font-bold text-emerald-700">
                    {active_booking.payment?.payment_status === 'confirmed' ? 'Paid & Settled ($150)' : 'Pending Settlement'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Reservation ID</span>
                  <span className="font-mono text-slate-600">PEG-RES-00{active_booking.id}</span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[11px]">Workpeg Transaction</span>
                  <span className="font-mono text-slate-600">tx_workpeg_sim_{room.id}84</span>
                </div>
              </div>
            ) : (
              <p className="text-xs text-slate-500">
                No active guest reservation. Room is vacant and circuit is safely locked open.
              </p>
            )}
          </div>

          <div className="p-4 rounded-2xl border border-slate-200/90 space-y-3">
            <div className="flex items-center gap-2">
              <ShieldAlert className="h-4 w-4 text-indigo-600" />
              <span className="text-xs font-bold text-slate-900 uppercase tracking-wider">
                Staff Circuit Override (Housekeeping & Maintenance)
              </span>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">
                  Override Duration
                </label>
                <select
                  value={selectedDuration}
                  onChange={(e) => setSelectedDuration(Number(e.target.value))}
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs font-semibold text-slate-800 outline-none"
                >
                  <option value={30}>30 Minutes (Housekeeping)</option>
                  <option value={60}>60 Minutes (Maintenance)</option>
                  <option value={120}>2 Hours (VIP Prep)</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-semibold text-slate-500 block mb-1">
                  Reason Note
                </label>
                <input
                  type="text"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="e.g. Turn-down cleaning"
                  className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 outline-none font-medium"
                />
              </div>
            </div>

            <div className="pt-2 flex items-center gap-3">
              <button
                onClick={() => handleApplyOverride(true)}
                disabled={isOverriding}
                className="flex-1 py-2 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow-sm disabled:opacity-50"
              >
                {isOverriding ? 'Applying...' : 'Grant Temporary Power'}
              </button>
              <button
                onClick={() => handleApplyOverride(false)}
                disabled={isOverriding}
                className="flex-1 py-2 px-3 rounded-xl border border-rose-300 text-rose-700 hover:bg-rose-50 font-bold text-xs transition disabled:opacity-50"
              >
                {isOverriding ? 'Applying...' : 'Emergency Cutoff'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
