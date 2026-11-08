import React from 'react';
import { 
  Zap, Power, User, CheckCircle2, AlertTriangle, 
  ShieldCheck, Cpu, Clock, Sparkles, ChevronRight, Activity 
} from 'lucide-react';

export default function RoomCard({
  roomDetail,
  onCheckIn,
  onConfirmPayment,
  onCheckOut,
  onHousekeeping,
  onAcknowledgeAlert,
  onOpenDetails,
  isLoading
}) {
  const { room, device, active_booking, authorisation, latest_telemetry, active_alerts } = roomDetail;
  const isAuth = authorisation?.authorised ?? false;
  const hasBooking = !!active_booking;
  const isPaid = active_booking?.payment?.payment_status === 'confirmed';
  const isPending = active_booking?.payment?.payment_status === 'pending';
  const power = latest_telemetry?.power || 0;
  const hasAlert = (active_alerts || []).length > 0;
  const activeAlert = hasAlert ? active_alerts[0] : null;

  const powerPercent = Math.min(100, Math.round((power / 2.5) * 100));

  return (
    <div className={`bg-white border rounded-3xl p-5 transition-all duration-200 flex flex-col justify-between shadow-card hover:shadow-elevation relative overflow-hidden group ${
      hasAlert 
        ? 'border-rose-400 ring-2 ring-rose-50 shadow-rose-100' 
        : isAuth 
        ? 'border-emerald-200/80 hover:border-emerald-300' 
        : 'border-slate-200/90'
    }`}>
      {hasAlert && (
        <div className="absolute top-0 inset-x-0 h-1.5 bg-rose-500 animate-pulse" />
      )}

      <div>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold text-slate-900 tracking-tight font-mono">
                {room.room_code}
              </span>
              {device && device.device_type === 'AZ3166' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-800 border border-emerald-200/80 flex items-center gap-1">
                  <Cpu className="h-3 w-3 text-emerald-600" />
                  <span>Physical Switch</span>
                </span>
              )}
            </div>
            <p className="text-xs font-medium text-slate-400 mt-0.5">
              {room.display_name}
            </p>
          </div>

          <div>
            {hasAlert ? (
              <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500 text-white shadow-sm animate-bounce">
                <AlertTriangle className="h-3 w-3" />
                <span>UNBILLED DRAW</span>
              </span>
            ) : isAuth ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-50 text-emerald-800 border border-emerald-200">
                <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" />
                <span>POWER ENERGIZED</span>
              </span>
            ) : isPending ? (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-50 text-amber-800 border border-amber-200">
                <Clock className="h-3 w-3 text-amber-600" />
                <span>PAYMENT PENDING</span>
              </span>
            ) : (
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-100 text-slate-600">
                <span className="h-2 w-2 rounded-full bg-slate-400" />
                <span>SAFE CUTOFF</span>
              </span>
            )}
          </div>
        </div>

        {hasAlert && activeAlert && (
          <div className="mb-4 p-3 rounded-2xl bg-rose-50 border border-rose-200 text-rose-900 text-xs">
            <div className="flex items-center justify-between gap-2 mb-1">
              <span className="font-extrabold flex items-center gap-1 text-[11px]">
                <AlertTriangle className="h-3.5 w-3.5 text-rose-600" />
                <span>{activeAlert.alert_type}</span>
              </span>
              <button
                onClick={() => onAcknowledgeAlert(activeAlert.id)}
                className="text-[10px] font-bold text-rose-700 hover:text-rose-900 underline"
              >
                Clear
              </button>
            </div>
            <p className="text-[11px] text-rose-800 leading-snug">
              {activeAlert.description}
            </p>
          </div>
        )}

        <div className="p-3.5 rounded-2xl bg-slate-50/80 border border-slate-100 space-y-2 mb-4">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Guest Status</span>
            <span className="font-extrabold text-slate-800">
              {hasBooking ? active_booking.guest_label : 'Vacant • Ready'}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 font-medium">Circuit State</span>
            <span className="font-mono font-bold text-slate-800 text-[11px]">
              {isAuth ? 'CLOSED (LIVE RELAY)' : 'OPEN (SAFE CUTOFF)'}
            </span>
          </div>

          <div className="pt-2 border-t border-slate-200/60">
            <div className="flex items-center justify-between text-xs mb-1.5">
              <span className="text-slate-500 font-medium flex items-center gap-1">
                <Activity className="h-3 w-3 text-slate-400" />
                <span>Demand Load</span>
              </span>
              <span className="font-mono font-extrabold text-slate-900">
                {power.toFixed(2)} kW
              </span>
            </div>
            <div className="w-full bg-slate-200/70 h-1.5 rounded-full overflow-hidden">
              <div 
                className={`h-full rounded-full transition-all duration-500 ${
                  hasAlert ? 'bg-rose-500' : isAuth ? 'bg-emerald-500' : 'bg-slate-300'
                }`}
                style={{ width: `${Math.max(powerPercent, isAuth ? 8 : 0)}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      <div className="pt-3 border-t border-slate-100 space-y-2">
        {!hasBooking ? (
          <div className="grid grid-cols-2 gap-2">
            <button
              onClick={() => onCheckIn(roomDetail)}
              disabled={isLoading}
              className="py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-extrabold text-xs transition shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <User className="h-3.5 w-3.5" />
              <span>Check In</span>
            </button>
            <button
              onClick={() => onHousekeeping(room.id)}
              disabled={isLoading}
              className="py-2.5 px-3 rounded-xl border border-slate-200 text-slate-700 hover:bg-slate-50 font-bold text-xs transition flex items-center justify-center gap-1.5 disabled:opacity-50"
            >
              <Clock className="h-3.5 w-3.5 text-slate-400" />
              <span>Clean (30m)</span>
            </button>
          </div>
        ) : isPending ? (
          <button
            onClick={() => onConfirmPayment(active_booking.id)}
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-amber-500 hover:bg-amber-600 text-white font-extrabold text-xs transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Zap className="h-4 w-4" />
            <span>Verify Payment & Energize Circuit</span>
          </button>
        ) : (
          <button
            onClick={() => onCheckOut(active_booking.id)}
            disabled={isLoading}
            className="w-full py-2.5 px-4 rounded-xl bg-slate-900 hover:bg-slate-800 text-white font-extrabold text-xs transition shadow-sm flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Power className="h-3.5 w-3.5 text-rose-400" />
            <span>Express Check Out (Cuts Power)</span>
          </button>
        )}

        <button
          onClick={() => onOpenDetails(room.id)}
          className="w-full py-1.5 text-center text-[11px] font-semibold text-slate-500 hover:text-slate-800 transition flex items-center justify-center gap-1"
        >
          <span>Room Inspector & Breaker History</span>
          <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
