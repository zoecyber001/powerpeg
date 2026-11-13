import React from 'react';
import { Cpu, Clock, ChevronRight } from 'lucide-react';
import Breaker from './Breaker';

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
  const isPending = active_booking?.payment?.payment_status === 'pending';
  const isPaid = active_booking?.payment?.payment_status === 'confirmed';
  const power = latest_telemetry?.power || 0;
  const hasAlert = (active_alerts || []).length > 0;
  const activeAlert = hasAlert ? active_alerts[0] : null;

  const folio = !hasBooking ? 'No folio' : isPaid ? 'Settled' : 'Pending';
  const folioTone = !hasBooking ? 'text-ink-3' : isPaid ? 'text-ink' : 'text-brass-ink';

  return (
    <div
      className={`flex flex-col justify-between rounded-card border bg-surface shadow-card transition-colors duration-150 ${
        hasAlert ? 'border-brick/40' : 'border-line hover:border-line-strong'
      }`}
    >
      <div className="px-4 pt-4">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[15px] font-medium tracking-tight text-ink">
                {room.room_code}
              </span>
              {device?.device_type === 'AZ3166' && (
                <span className="inline-flex items-center gap-1 font-mono text-[10px] text-ink-3">
                  <Cpu className="h-3 w-3 text-ink-4" />
                  <span>AZ3166</span>
                </span>
              )}
            </div>
            <p className="mt-0.5 truncate text-[11px] text-ink-3">{room.display_name}</p>
          </div>

          <Breaker on={isAuth} alert={hasAlert} compact />
        </div>

        {activeAlert && (
          <div className="mt-3 rounded-panel border border-brick/25 bg-brick-soft px-2.5 py-2">
            <div className="flex items-start justify-between gap-2">
              <p className="font-mono text-[10px] text-brick-ink/80">
                {activeAlert.alert_type.replace(/_/g, ' ').toLowerCase()}
              </p>
              <button
                onClick={() => onAcknowledgeAlert(activeAlert.id)}
                className="text-[10px] text-brick-ink/80 underline decoration-brick/30 underline-offset-2 transition-colors duration-150 hover:text-brick-ink"
              >
                Clear
              </button>
            </div>
            <p className="mt-1 text-[11px] leading-snug text-brick-ink">{activeAlert.description}</p>
          </div>
        )}

        <dl className="mt-3 divide-y divide-line border-y border-line">
          <div className="flex items-baseline justify-between py-1.5">
            <dt className="text-[11px] text-ink-3">Guest</dt>
            <dd className="ml-3 truncate text-xs font-medium text-ink">
              {hasBooking ? active_booking.guest_label : 'Vacant'}
            </dd>
          </div>
          <div className="flex items-baseline justify-between py-1.5">
            <dt className="text-[11px] text-ink-3">Folio</dt>
            <dd className={`ml-3 text-xs font-medium ${folioTone}`}>{folio}</dd>
          </div>
          <div className="flex items-baseline justify-between py-1.5">
            <dt className="text-[11px] text-ink-3">Demand</dt>
            <dd className={`num ml-3 font-mono text-xs ${power > 0.05 ? 'text-ink' : 'text-ink-3'}`}>
              {power.toFixed(2)} kW
            </dd>
          </div>
        </dl>
      </div>

      <div className="px-4 pb-3 pt-3">
        {!hasBooking ? (
          <div className="flex items-center gap-2">
            <button
              onClick={() => onCheckIn(roomDetail)}
              disabled={isLoading}
              className="h-8 flex-1 rounded-control bg-ink px-3 text-xs font-medium text-paper transition-colors duration-150 hover:bg-ink-2 active:scale-[0.99] disabled:opacity-50"
            >
              Check in
            </button>
            <button
              onClick={() => onHousekeeping(room.id)}
              disabled={isLoading}
              className="h-8 rounded-control border border-line px-2.5 text-xs text-ink-2 transition-colors duration-150 hover:border-line-strong hover:text-ink disabled:opacity-50"
              title="30-minute cleaning access"
            >
              Clean 30m
            </button>
          </div>
        ) : isPending ? (
          <button
            onClick={() => onConfirmPayment(active_booking.id)}
            disabled={isLoading}
            className="flex h-8 w-full items-center justify-center gap-1.5 rounded-control bg-brass-ink px-3 text-xs font-medium text-paper transition-colors duration-150 hover:bg-[#6b4610] active:scale-[0.99] disabled:opacity-50"
          >
            <Clock className="h-3.5 w-3.5" />
            <span>Take payment, close circuit</span>
          </button>
        ) : (
          <button
            onClick={() => onCheckOut(active_booking.id)}
            disabled={isLoading}
            className="h-8 w-full rounded-control border border-line px-3 text-xs font-medium text-ink transition-colors duration-150 hover:border-line-strong active:scale-[0.99] disabled:opacity-50"
          >
            Check out, open circuit
          </button>
        )}

        <button
          onClick={() => onOpenDetails(room.id)}
          className="mt-1 flex h-7 w-full items-center justify-center gap-1 text-[11px] text-ink-3 transition-colors duration-150 hover:text-ink"
        >
          <span>Inspector</span>
          <ChevronRight className="h-3 w-3" />
        </button>
      </div>
    </div>
  );
}
