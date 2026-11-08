import React from 'react';
import { 
  Zap, Power, ShieldCheck, AlertTriangle, Cpu, User, 
  CreditCard, Clock, ChevronRight, CheckCircle2 
} from 'lucide-react';

export default function RoomRackTable({
  rooms,
  onCheckIn,
  onConfirmPayment,
  onCheckOut,
  onHousekeeping,
  onOpenDetails,
  isLoading
}) {
  return (
    <div className="bg-white border border-slate-200/90 rounded-2xl shadow-card overflow-hidden">
      <div className="p-4 border-b border-slate-100 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-extrabold text-slate-900">
            Property Room Rack & Circuit Matrix
          </h3>
          <p className="text-[11px] text-slate-400">
            Synchronized with Workpeg table registry
          </p>
        </div>
        <span className="text-xs font-semibold text-slate-500">
          {rooms.length} Total Units
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-50/80 border-b border-slate-200/80 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
              <th className="py-3 px-4">Room & Unit</th>
              <th className="py-3 px-4">Guest Reservation</th>
              <th className="py-3 px-4">Billing & Folio</th>
              <th className="py-3 px-4">Circuit Relay</th>
              <th className="py-3 px-4">Live Load</th>
              <th className="py-3 px-4 text-right">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
            {rooms.map((r) => {
              const { room, device, active_booking, authorisation, latest_telemetry, active_alerts } = r;
              const isAuth = authorisation?.authorised ?? false;
              const hasAlert = (active_alerts || []).length > 0;
              const isPaid = active_booking?.payment?.payment_status === 'confirmed';
              const isPending = active_booking?.payment?.payment_status === 'pending';
              const power = latest_telemetry?.power || 0;

              return (
                <tr 
                  key={room.id}
                  className={`hover:bg-slate-50/60 transition ${hasAlert ? 'bg-rose-50/30' : ''}`}
                >
                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <span className="font-extrabold text-sm text-slate-900 font-mono">
                        {room.room_code}
                      </span>
                      {device?.device_type === 'AZ3166' && (
                        <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-emerald-800 flex items-center gap-1">
                          <Cpu className="h-2.5 w-2.5" />
                          <span>IoT Node</span>
                        </span>
                      )}
                    </div>
                    <span className="text-[11px] text-slate-400 block mt-0.5">
                      {room.display_name}
                    </span>
                  </td>

                  <td className="py-3.5 px-4">
                    {active_booking ? (
                      <div>
                        <span className="font-bold text-slate-800 block">
                          {active_booking.guest_label}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          Booking #{active_booking.id}
                        </span>
                      </div>
                    ) : (
                      <span className="text-slate-400 text-xs italic">Vacant</span>
                    )}
                  </td>

                  <td className="py-3.5 px-4">
                    {active_booking ? (
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                        isPaid 
                          ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                          : 'bg-amber-50 text-amber-700 border border-amber-200'
                      }`}>
                        {isPaid ? <CheckCircle2 className="h-3 w-3" /> : <Clock className="h-3 w-3" />}
                        {isPaid ? 'Settled ($150)' : 'Pending Settle'}
                      </span>
                    ) : (
                      <span className="text-slate-400 text-xs">—</span>
                    )}
                  </td>

                  <td className="py-3.5 px-4">
                    <div className="flex items-center gap-2">
                      <span className={`h-2 w-2 rounded-full ${
                        isAuth ? 'bg-emerald-500 animate-pulse' : 'bg-slate-300'
                      }`} />
                      <span className={`font-bold ${
                        isAuth ? 'text-emerald-700' : 'text-slate-500'
                      }`}>
                        {isAuth ? 'ENERGIZED [ON]' : 'SAFE CUTOFF [OFF]'}
                      </span>
                    </div>
                    {authorisation?.reason && (
                      <span className="text-[10px] text-slate-400 block truncate max-w-[150px]">
                        {authorisation.reason}
                      </span>
                    )}
                  </td>

                  <td className="py-3.5 px-4 font-mono">
                    <span className={`font-bold ${power > 0.05 ? 'text-slate-900' : 'text-slate-400'}`}>
                      {power.toFixed(2)} kW
                    </span>
                    <span className="text-[10px] text-slate-400 block">
                      {power > 0.05 ? 'Active load' : 'Zero standby'}
                    </span>
                  </td>

                  <td className="py-3.5 px-4 text-right">
                    <div className="flex items-center justify-end gap-1.5">
                      {!active_booking ? (
                        <>
                          <button
                            onClick={() => onCheckIn(r)}
                            disabled={isLoading}
                            className="px-3 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs transition shadow-sm"
                          >
                            Check In
                          </button>
                          <button
                            onClick={() => onHousekeeping(room.id)}
                            disabled={isLoading}
                            className="px-2 py-1 rounded-lg border border-slate-200 hover:bg-slate-50 text-slate-600 text-xs font-semibold transition"
                            title="30m cleaning override"
                          >
                            Clean (30m)
                          </button>
                        </>
                      ) : isPending ? (
                        <button
                          onClick={() => onConfirmPayment(active_booking.id)}
                          disabled={isLoading}
                          className="px-3 py-1 rounded-lg bg-amber-500 hover:bg-amber-600 text-white font-bold text-xs transition shadow-sm"
                        >
                          Settle & Energize
                        </button>
                      ) : (
                        <button
                          onClick={() => onCheckOut(active_booking.id)}
                          disabled={isLoading}
                          className="px-3 py-1 rounded-lg border border-rose-200 text-rose-700 hover:bg-rose-50 font-bold text-xs transition"
                        >
                          Express Check Out
                        </button>
                      )}

                      <button
                        onClick={() => onOpenDetails(room.id)}
                        className="p-1 rounded-lg hover:bg-slate-100 text-slate-400 hover:text-slate-600 transition"
                        title="Room Inspector"
                      >
                        <ChevronRight className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
