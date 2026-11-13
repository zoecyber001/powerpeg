import React from 'react';
import { ChevronRight } from 'lucide-react';
import Breaker from './Breaker';

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
    <div className="overflow-hidden rounded-card border border-line bg-surface shadow-card">
      <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
        <h3 className="text-xs font-medium text-ink">Room rack</h3>
        <span className="num font-mono text-[10px] text-ink-3">{rooms.length} units</span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full border-collapse text-left">
          <thead>
            <tr className="border-b border-line text-[11px] text-ink-3">
              <th className="px-4 py-2 font-normal">Room</th>
              <th className="px-4 py-2 font-normal">Guest</th>
              <th className="px-4 py-2 font-normal">Folio</th>
              <th className="px-4 py-2 font-normal">Circuit</th>
              <th className="px-4 py-2 font-normal">Load</th>
              <th className="px-4 py-2 text-right font-normal">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rooms.map((r) => {
              const { room, device, active_booking, authorisation, latest_telemetry, active_alerts } = r;
              const isAuth = authorisation?.authorised ?? false;
              const hasAlert = (active_alerts || []).length > 0;
              const isPaid = active_booking?.payment?.payment_status === 'confirmed';
              const isPending = active_booking?.payment?.payment_status === 'pending';
              const power = latest_telemetry?.power || 0;
              const loadPercent = Math.min(100, Math.round((power / 2.5) * 100));

              return (
                <tr
                  key={room.id}
                  className={`transition-colors duration-150 ${
                    hasAlert ? 'bg-brick-soft/50' : 'hover:bg-paper/70'
                  }`}
                >
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-[13px] font-medium text-ink">{room.room_code}</span>
                      {device?.device_type === 'AZ3166' && (
                        <span className="font-mono text-[10px] text-ink-4">AZ3166</span>
                      )}
                    </div>
                    <span className="mt-0.5 block truncate text-[11px] text-ink-3">{room.display_name}</span>
                  </td>

                  <td className="px-4 py-2.5">
                    {active_booking ? (
                      <div className="min-w-0">
                        <span className="block truncate text-xs text-ink">{active_booking.guest_label}</span>
                        <span className="num block font-mono text-[10px] text-ink-4">#{active_booking.id}</span>
                      </div>
                    ) : (
                      <span className="text-xs text-ink-3">Vacant</span>
                    )}
                  </td>

                  <td className="px-4 py-2.5">
                    {active_booking ? (
                      <span className={`text-xs ${isPaid ? 'text-ink' : 'text-brass-ink'}`}>
                        {isPaid ? 'Settled' : 'Pending'}
                      </span>
                    ) : (
                      <span className="text-xs text-ink-4">—</span>
                    )}
                  </td>

                  <td className="px-4 py-2.5">
                    <Breaker on={isAuth} alert={hasAlert} compact />
                    {authorisation?.reason && (
                      <span className="mt-0.5 block max-w-[170px] truncate text-[10px] text-ink-4">
                        {authorisation.reason}
                      </span>
                    )}
                  </td>

                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <span className={`num font-mono text-xs ${power > 0.05 ? 'text-ink' : 'text-ink-3'}`}>
                        {power.toFixed(2)}
                      </span>
                      <span className="h-1 w-14 overflow-hidden rounded-full bg-line">
                        <span
                          className={`block h-full transition-[width] duration-300 ${hasAlert ? 'bg-brick' : isAuth ? 'bg-brass' : 'bg-ink-4'}`}
                          style={{ width: `${loadPercent}%` }}
                        />
                      </span>
                    </div>
                  </td>

                  <td className="px-4 py-2.5">
                    <div className="flex items-center justify-end gap-3">
                      {!active_booking ? (
                        <>
                          <button
                            onClick={() => onCheckIn(r)}
                            disabled={isLoading}
                            className="text-xs font-medium text-ink underline decoration-line-strong underline-offset-2 transition-colors duration-150 hover:decoration-ink disabled:opacity-50"
                          >
                            Check in
                          </button>
                          <button
                            onClick={() => onHousekeeping(room.id)}
                            disabled={isLoading}
                            className="text-xs text-ink-3 transition-colors duration-150 hover:text-ink disabled:opacity-50"
                            title="30-minute cleaning access"
                          >
                            Clean
                          </button>
                        </>
                      ) : isPending ? (
                        <button
                          onClick={() => onConfirmPayment(active_booking.id)}
                          disabled={isLoading}
                          className="text-xs font-medium text-brass-ink underline decoration-brass/40 underline-offset-2 transition-colors duration-150 hover:decoration-brass-ink disabled:opacity-50"
                        >
                          Take payment
                        </button>
                      ) : (
                        <button
                          onClick={() => onCheckOut(active_booking.id)}
                          disabled={isLoading}
                          className="text-xs text-ink-2 transition-colors duration-150 hover:text-ink disabled:opacity-50"
                        >
                          Check out
                        </button>
                      )}

                      <button
                        onClick={() => onOpenDetails(room.id)}
                        className="rounded-[6px] p-1 text-ink-4 transition-colors duration-150 hover:bg-paper hover:text-ink"
                        title="Inspector"
                      >
                        <ChevronRight className="h-3.5 w-3.5" />
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
