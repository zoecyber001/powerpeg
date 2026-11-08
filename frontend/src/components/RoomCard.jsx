import React from 'react';
import { 
  Zap, Power, User, CheckCircle2, AlertTriangle, ShieldCheck, Cpu
} from 'lucide-react';

export default function RoomCard({
  roomDetail,
  onCheckIn,
  onConfirmPayment,
  onCheckOut,
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

  return (
    <div className={`bg-white border rounded-2xl p-5 transition flex flex-col justify-between shadow-card hover:shadow-elevation relative overflow-hidden ${
      hasAlert 
        ? 'border-rose-400 ring-2 ring-rose-50' 
        : isAuth 
        ? 'border-slate-200 hover:border-emerald-300' 
        : 'border-slate-200'
    }`}>
      {hasAlert && (
        <div className="absolute top-0 inset-x-0 h-1 bg-rose-500" />
      )}

      <div>
        <div className="flex items-start justify-between gap-3 mb-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-extrabold text-slate-900 tracking-tight">{room.room_code}</span>
              {device && device.device_type === 'AZ3166' && (
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-md bg-emerald-50 text-emerald-700 border border-emerald-200 flex items-center gap-1">
                  <Cpu className="h-3 w-3" />
                  <span>Physical Switch</span>
                </span>
              )}
            </div>
            <p className="text-xs font-medium text-slate-500 mt-0.5">{room.display_name}</p>
          </div>

          <div className={`flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider ${
            isAuth 
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
              : 'bg-slate-100 text-slate-600 border border-slate-200'
          }`}>
            <span className={`h-2 w-2 rounded-full ${isAuth ? 'bg-emerald-500 animate-pulse' : 'bg-slate-400'}`} />
            <span>{isAuth ? 'Power On' : 'Power Cut'}</span>
          </div>
        </div>

        {hasAlert && (
          <div className="mb-4 p-3 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
            <div className="flex items-center justify-between font-bold gap-2 mb-1">
              <span className="flex items-center gap-1.5">
                <AlertTriangle className="h-4 w-4 text-rose-600" />
                <span>Rogue Power Detected</span>
              </span>
              <button
                onClick={() => onAcknowledgeAlert(activeAlert.id)}
                className="text-[10px] px-2 py-0.5 bg-rose-600 hover:bg-rose-700 rounded text-white font-semibold transition"
              >
                Dismiss
              </button>
            </div>
            <p className="text-[11px] text-rose-700 leading-tight">
              Drawing {power.toFixed(2)} kW while room access is not authorized.
            </p>
          </div>
        )}

        <div className="bg-slate-50 rounded-xl p-3.5 border border-slate-100 mb-4 space-y-2.5">
          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 flex items-center gap-1.5 font-medium">
              <User className="h-3.5 w-3.5 text-slate-400" />
              <span>Guest:</span>
            </span>
            <span className="font-bold text-slate-800">
              {hasBooking ? active_booking.guest_label : 'Vacant'}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs">
            <span className="text-slate-500 flex items-center gap-1.5 font-medium">
              <CheckCircle2 className="h-3.5 w-3.5 text-slate-400" />
              <span>Payment:</span>
            </span>
            <span className={`font-semibold ${
              isPaid 
                ? 'text-emerald-700 bg-emerald-100/70 px-2 py-0.5 rounded text-[11px]' 
                : isPending 
                ? 'text-amber-700 bg-amber-100/70 px-2 py-0.5 rounded text-[11px]' 
                : 'text-slate-400 text-[11px]'
            }`}>
              {isPaid ? 'Verified' : isPending ? 'Pending Payment' : 'No Active Stay'}
            </span>
          </div>

          <div className="flex items-center justify-between text-xs pt-2 border-t border-slate-200/60">
            <span className="text-slate-500 flex items-center gap-1.5 font-medium">
              <Zap className="h-3.5 w-3.5 text-slate-400" />
              <span>Power Draw:</span>
            </span>
            <span className={`font-mono font-bold ${power > 0.05 ? 'text-emerald-700' : 'text-slate-400'}`}>
              {power > 0.05 ? `${power.toFixed(2)} kW (Active)` : '0.00 kW (Standby)'}
            </span>
          </div>
        </div>
      </div>

      <div className="space-y-2 pt-2 border-t border-slate-100">
        {!hasBooking ? (
          <button
            onClick={() => onCheckIn(room.id)}
            disabled={isLoading}
            className="w-full py-2.5 px-3 rounded-xl bg-slate-900 hover:bg-slate-800 active:scale-98 text-xs font-semibold text-white transition flex items-center justify-center gap-1.5 shadow-sm disabled:opacity-50"
          >
            <span>+ Check In Guest</span>
          </button>
        ) : isPending ? (
          <button
            onClick={() => onConfirmPayment(active_booking.id)}
            disabled={isLoading}
            className="w-full py-2.5 px-3 rounded-xl bg-emerald-600 hover:bg-emerald-700 active:scale-98 text-xs font-bold text-white transition flex items-center justify-center gap-1.5 shadow-md shadow-emerald-600/20 disabled:opacity-50"
          >
            <Power className="h-3.5 w-3.5" />
            <span>Verify Payment & Turn Power On</span>
          </button>
        ) : (
          <button
            onClick={() => onCheckOut(active_booking.id)}
            disabled={isLoading}
            className="w-full py-2.5 px-3 rounded-xl bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 active:scale-98 text-xs font-bold transition flex items-center justify-center gap-1.5 disabled:opacity-50"
          >
            <Power className="h-3.5 w-3.5" />
            <span>Check Out & Cut Power</span>
          </button>
        )}

        <button
          onClick={() => onOpenDetails(room.id)}
          className="w-full text-center py-1.5 text-xs font-medium text-slate-500 hover:text-slate-800 transition"
        >
          View room usage & switch details →
        </button>
      </div>
    </div>
  );
}
