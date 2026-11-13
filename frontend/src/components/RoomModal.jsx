import React, { useState } from 'react';
import { X, ShieldAlert } from 'lucide-react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';
import AZ3166DigitalTwin from './AZ3166DigitalTwin';
import Breaker from './Breaker';

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
    time: (t.recorded_at || t.observed_at)
      ? new Date(t.recorded_at || t.observed_at).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })
      : `${i * 2}s`,
    power: Number(t.power?.toFixed(2) || 0),
  }));

  const recorded = chartData.some(point => point.power > 0.05);

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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4">
      <div className="flex max-h-[90vh] w-full max-w-[620px] animate-rise flex-col overflow-hidden rounded-card border border-line bg-surface shadow-pop">
        <div className="flex items-start justify-between border-b border-line px-4 py-3">
          <div className="min-w-0">
            <div className="flex items-baseline gap-2">
              <h3 className="font-mono text-[15px] font-medium text-ink">{room.room_code}</h3>
              <span className="truncate text-[11px] text-ink-3">{room.display_name}</span>
            </div>
            <p className="mt-1 flex items-center gap-2 text-[11px] text-ink-3">
              <Breaker on={isAuth} alert={hasAlert} compact />
              <span className="text-ink-4">·</span>
              <span className="truncate">{authorisation?.reason || 'No authorisation on file'}</span>
            </p>
          </div>

          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-[6px] p-1 text-ink-4 transition-colors duration-150 hover:bg-paper hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <div className="flex-1 space-y-4 overflow-y-auto px-4 py-4">
          {isAZ3166 && (
            <AZ3166DigitalTwin
              device={device}
              roomCode={room.room_code}
              telemetry={latest_telemetry}
              isOverridden={authorisation?.reason?.includes('override')}
            />
          )}

          <section>
            <div className="mb-2 flex items-baseline justify-between">
              <h4 className="text-xs font-medium text-ink">Telemetry</h4>
              <span className="num font-mono text-[11px] text-ink-2">
                {latest_telemetry?.power?.toFixed(2) || '0.00'} kW
              </span>
            </div>

            <div className="h-36 w-full rounded-panel border border-line bg-paper p-2">
              {chartData.length > 0 && recorded ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={chartData} margin={{ top: 4, right: 4, left: 4, bottom: 0 }}>
                    <CartesianGrid stroke="#E5DFD6" strokeDasharray="2 4" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis domain={[0, 'auto']} hide />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E5DFD6',
                        borderRadius: '8px',
                        color: '#1D1B17',
                        fontSize: '11px',
                        fontFamily: 'IBM Plex Mono, monospace',
                        boxShadow: '0 12px 32px -12px rgba(29,27,23,0.28)',
                      }}
                      labelStyle={{ color: '#6F6960' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="power"
                      name="kW"
                      stroke="#A9721C"
                      strokeWidth={1.5}
                      fill="#A9721C"
                      fillOpacity={0.08}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center font-mono text-[11px] text-ink-3">
                  Circuit open · no load recorded
                </div>
              )}
            </div>
          </section>

          <section>
            <h4 className="mb-2 text-xs font-medium text-ink">Folio</h4>
            <div className="rounded-panel border border-line">
              {active_booking ? (
                <dl className="divide-y divide-line text-xs">
                  <div className="flex items-baseline justify-between px-3 py-2">
                    <dt className="text-[11px] text-ink-3">Guest</dt>
                    <dd className="ml-3 font-medium text-ink">{active_booking.guest_label}</dd>
                  </div>
                  <div className="flex items-baseline justify-between px-3 py-2">
                    <dt className="text-[11px] text-ink-3">Payment</dt>
                    <dd className={`ml-3 font-medium ${active_booking.payment?.payment_status === 'confirmed' ? 'text-moss' : 'text-brass-ink'}`}>
                      {active_booking.payment?.payment_status === 'confirmed' ? 'Settled' : 'Pending'}
                    </dd>
                  </div>
                  <div className="flex items-baseline justify-between px-3 py-2">
                    <dt className="text-[11px] text-ink-3">Booking</dt>
                    <dd className="num ml-3 font-mono text-[11px] text-ink-2">PEG-RES-{active_booking.id}</dd>
                  </div>
                </dl>
              ) : (
                <p className="px-3 py-2.5 text-[11px] text-ink-3">
                  Vacant. Nothing billable, circuit open.
                </p>
              )}
            </div>
          </section>

          <section className="rounded-panel border border-line px-3 py-3">
            <div className="flex items-center gap-1.5">
              <ShieldAlert className="h-3.5 w-3.5 text-ink-4" />
              <h4 className="text-xs font-medium text-ink">Staff override</h4>
            </div>

            <div className="mt-2.5 grid grid-cols-2 gap-2.5">
              <div>
                <label htmlFor="override-duration" className="mb-1 block text-[11px] text-ink-3">
                  Duration
                </label>
                <select
                  id="override-duration"
                  value={selectedDuration}
                  onChange={(e) => setSelectedDuration(Number(e.target.value))}
                  className="h-9 w-full cursor-pointer appearance-none rounded-control border border-line bg-surface px-2.5 text-xs text-ink focus:border-line-strong"
                >
                  <option value={30}>30 min · housekeeping</option>
                  <option value={60}>60 min · maintenance</option>
                  <option value={120}>2 hours · VIP prep</option>
                </select>
              </div>

              <div>
                <label htmlFor="override-reason" className="mb-1 block text-[11px] text-ink-3">
                  Reason
                </label>
                <input
                  id="override-reason"
                  type="text"
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Turn-down cleaning"
                  className="h-9 w-full rounded-control border border-line bg-surface px-2.5 text-xs text-ink placeholder:text-ink-4 focus:border-line-strong"
                />
              </div>
            </div>

            <div className="mt-3 flex items-center gap-2">
              <button
                onClick={() => handleApplyOverride(true)}
                disabled={isOverriding}
                className="h-8 flex-1 rounded-control bg-ink px-3 text-xs font-medium text-paper transition-colors duration-150 hover:bg-ink-2 active:scale-[0.99] disabled:opacity-50"
              >
                {isOverriding ? 'Applying' : 'Grant temporary power'}
              </button>
              <button
                onClick={() => handleApplyOverride(false)}
                disabled={isOverriding}
                className="h-8 flex-1 rounded-control border border-brick/30 px-3 text-xs font-medium text-brick-ink transition-colors duration-150 hover:bg-brick-soft active:scale-[0.99] disabled:opacity-50"
              >
                Emergency cutoff
              </button>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
