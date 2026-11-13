import React from 'react';
import {
  ResponsiveContainer, AreaChart, Area, XAxis, YAxis, Tooltip, CartesianGrid
} from 'recharts';

export default function EnergyView({ rooms, telemetryHistory, roomCode = 'ROOM-204' }) {
  const chartData = (telemetryHistory || []).map((t, idx) => ({
    time: t.observed_at
      ? new Date(t.observed_at).toLocaleTimeString([], { minute: '2-digit', second: '2-digit' })
      : `${idx}s`,
    power: Number(t.power?.toFixed(2) || 0),
  }));

  const recorded = chartData.some(point => point.power > 0.05);

  const ranked = rooms
    .map(r => ({
      id: r.room.id,
      code: r.room.room_code,
      name: r.room.display_name,
      power: Number((r.latest_telemetry?.power || 0).toFixed(2)),
      live: r.authorisation?.authorised ?? false,
    }))
    .sort((a, b) => b.power - a.power);

  const peak = ranked.reduce((max, r) => Math.max(max, r.power), 0);
  const drawing = ranked.filter(r => r.power > 0.05).length;
  const occupied = rooms.filter(r => !!r.active_booking).length;
  const average = occupied > 0
    ? ranked.reduce((sum, r) => sum + r.power, 0) / occupied
    : 0;
  const maxPower = Math.max(peak, 0.01);

  const cells = [
    { label: 'Peak draw', value: peak.toFixed(2), unit: 'kW', note: 'Highest of the rooms above' },
    { label: 'Average per occupied room', value: average.toFixed(2), unit: 'kW', note: `${occupied} occupied now` },
    { label: 'Rooms drawing', value: `${drawing}`, note: `of ${rooms.length} circuits` },
  ];

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-1 overflow-hidden rounded-card border border-line bg-surface shadow-card sm:grid-cols-3">
        {cells.map((cell, index) => (
          <div key={cell.label} className={`px-4 py-3.5 ${index > 0 ? 'border-t border-line sm:border-l sm:border-t-0' : ''}`}>
            <p className="text-[11px] text-ink-3">{cell.label}</p>
            <p className="mt-1 flex items-baseline gap-1">
              <span className="num font-mono text-[22px] leading-none tracking-tight text-ink">{cell.value}</span>
              {cell.unit && <span className="font-mono text-[11px] text-ink-3">{cell.unit}</span>}
            </p>
            <p className="mt-1.5 text-[11px] text-ink-3">{cell.note}</p>
          </div>
        ))}
      </div>

      <section className="rounded-card border border-line bg-surface shadow-card">
        <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
          <div>
            <h2 className="text-xs font-medium text-ink">{roomCode} demand</h2>
            <p className="mt-0.5 text-[11px] text-ink-3">Software simulator, two-second samples</p>
          </div>
          <span className="font-mono text-[10px] text-ink-3">{chartData.length} samples</span>
        </div>

        <div className="h-64 w-full px-3 py-3">
          {chartData.length > 0 && recorded ? (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData} margin={{ top: 4, right: 18, left: -8, bottom: 0 }}>
                <CartesianGrid stroke="#E5DFD6" strokeDasharray="2 4" vertical={false} />
                <XAxis
                  dataKey="time"
                  stroke="#9C948A"
                  fontSize={10}
                  tickLine={false}
                  minTickGap={44}
                  tickMargin={6}
                  axisLine={{ stroke: '#E5DFD6' }}
                  fontFamily="IBM Plex Mono, monospace"
                />
                <YAxis
                  stroke="#9C948A"
                  fontSize={10}
                  tickLine={false}
                  axisLine={false}
                  domain={[0, 'auto']}
                  fontFamily="IBM Plex Mono, monospace"
                />
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
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex h-full items-center justify-center font-mono text-[11px] text-ink-3">
              {chartData.length === 0 ? 'No telemetry samples yet' : 'Circuit open · no load recorded'}
            </div>
          )}
        </div>
      </section>

      <section className="rounded-card border border-line bg-surface shadow-card">
        <div className="flex items-baseline justify-between border-b border-line px-4 py-2.5">
          <h2 className="text-xs font-medium text-ink">By room</h2>
          <span className="font-mono text-[10px] text-ink-3">kW</span>
        </div>

        <ul className="divide-y divide-line">
          {ranked.map(r => (
            <li key={r.id} className="flex items-center gap-3 px-4 py-2.5">
              <div className="w-[104px] shrink-0">
                <p className="font-mono text-xs text-ink">{r.code}</p>
                <p className="truncate text-[10px] text-ink-3">{r.name}</p>
              </div>

              <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-line">
                <span
                  className={`block h-full ${r.live ? 'bg-brass' : 'bg-ink-4'}`}
                  style={{ width: `${(r.power / maxPower) * 100}%` }}
                />
              </div>

              <span className={`num w-12 shrink-0 text-right font-mono text-xs ${r.power > 0.05 ? 'text-ink' : 'text-ink-3'}`}>
                {r.power.toFixed(2)}
              </span>
              <span className="w-[52px] shrink-0 text-right text-[11px] text-ink-3">
                {r.live ? 'live' : 'cut off'}
              </span>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
