import React, { useState } from 'react';
import { ArrowRight, Check } from 'lucide-react';

export default function AlertsView({
  alerts,
  onAcknowledgeAlert,
  onOpenRoom,
  rooms = []
}) {
  const [filter, setFilter] = useState('ACTIVE');

  const activeAlerts = (alerts || []).filter(a => a.status === 'ACTIVE');
  const acknowledgedAlerts = (alerts || []).filter(a => a.status !== 'ACTIVE');
  const displayedAlerts = filter === 'ACTIVE' ? activeAlerts : acknowledgedAlerts;

  const getRoomForAlert = (alert) => rooms.find(r => r.room.id === alert.room_id) || null;

  const affectedRooms = new Set(activeAlerts.map(a => a.room_id)).size;

  const cells = [
    { label: 'Active incidents', value: `${activeAlerts.length}`, note: activeAlerts.length > 0 ? 'Needs a decision' : 'Nothing open' },
    { label: 'Acknowledged', value: `${acknowledgedAlerts.length}`, note: 'Still on the record' },
    { label: 'Rooms affected', value: `${affectedRooms}`, note: `of ${rooms.length} circuits` },
  ];

  const filters = [
    { id: 'ACTIVE', label: 'Active', count: activeAlerts.length },
    { id: 'RESOLVED', label: 'Acknowledged', count: acknowledgedAlerts.length },
  ];

  return (
    <div className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-base font-medium text-ink">Incidents</h2>
          <p className="mt-0.5 text-xs text-ink-3">
            Draw compared against the folio for each room
          </p>
        </div>

        <div className="flex items-center gap-0.5 rounded-control border border-line bg-surface p-0.5">
          {filters.map(f => (
            <button
              key={f.id}
              onClick={() => setFilter(f.id)}
              aria-pressed={filter === f.id}
              className={`flex h-7 items-center gap-1.5 rounded-[6px] px-2.5 text-xs transition-colors duration-150 ${
                filter === f.id ? 'bg-paper text-ink' : 'text-ink-3 hover:text-ink'
              }`}
            >
              <span>{f.label}</span>
              <span className="num font-mono text-[10px] text-ink-4">{f.count}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 overflow-hidden rounded-card border border-line bg-surface shadow-card sm:grid-cols-3">
        {cells.map((cell, index) => (
          <div key={cell.label} className={`px-4 py-3.5 ${index > 0 ? 'border-t border-line sm:border-l sm:border-t-0' : ''}`}>
            <p className="text-[11px] text-ink-3">{cell.label}</p>
            <p className="num mt-1 font-mono text-[22px] leading-none tracking-tight text-ink">{cell.value}</p>
            <p className="mt-1.5 text-[11px] text-ink-3">{cell.note}</p>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        {displayedAlerts.length === 0 ? (
          <div className="rounded-card border border-line bg-surface px-4 py-10 text-center shadow-card">
            <p className="text-[13px] text-ink">
              {filter === 'ACTIVE' ? 'Everything reconciles' : 'Nothing acknowledged yet'}
            </p>
            <p className="mx-auto mt-1 max-w-[380px] text-[11px] leading-relaxed text-ink-3">
              {filter === 'ACTIVE'
                ? 'Every room drawing power has a paid folio behind it.'
                : 'Acknowledged incidents stay on the record, with their time.'}
            </p>
          </div>
        ) : (
          displayedAlerts.map(alert => {
            const isCritical = alert.severity === 'CRITICAL';
            const roomData = getRoomForAlert(alert);

            return (
              <article
                key={alert.id}
                className={`rounded-card border border-l-2 bg-surface px-4 py-3 shadow-card ${
                  alert.status === 'ACTIVE'
                    ? isCritical ? 'border-line border-l-brick' : 'border-line border-l-brass'
                    : 'border-line border-l-line-strong'
                }`}
              >
                <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-baseline gap-2">
                      <span className={`font-mono text-[10px] ${isCritical ? 'text-brick-ink' : 'text-brass-ink'}`}>
                        {alert.severity.toLowerCase()}
                      </span>
                      <h3 className="text-[13px] font-medium text-ink">
                        {alert.alert_type.replace(/_/g, ' ').toLowerCase()}
                      </h3>
                      <span className="num font-mono text-[10px] text-ink-4">
                        {new Date(alert.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                      </span>
                      {alert.status !== 'ACTIVE' && (
                        <span className="text-[10px] text-ink-3">acknowledged</span>
                      )}
                    </div>

                    <p className="mt-1 max-w-[640px] text-xs leading-relaxed text-ink-2">
                      {alert.description}
                    </p>

                    {roomData && (
                      <p className="mt-1 font-mono text-[10px] text-ink-3">
                        {roomData.room.room_code} · {roomData.room.display_name}
                      </p>
                    )}
                  </div>

                  <div className="flex shrink-0 items-center gap-3">
                    {roomData && onOpenRoom && (
                      <button
                        onClick={() => onOpenRoom(roomData.room.id)}
                        className="flex items-center gap-1 text-xs text-ink-2 transition-colors duration-150 hover:text-ink"
                      >
                        <span>Open room</span>
                        <ArrowRight className="h-3 w-3" />
                      </button>
                    )}

                    {alert.status === 'ACTIVE' && (
                      <button
                        onClick={() => onAcknowledgeAlert(alert.id)}
                        className="flex h-8 items-center gap-1.5 rounded-control bg-ink px-3 text-xs font-medium text-paper transition-colors duration-150 hover:bg-ink-2 active:scale-[0.99]"
                      >
                        <Check className="h-3.5 w-3.5" />
                        <span>Acknowledge</span>
                      </button>
                    )}
                  </div>
                </div>
              </article>
            );
          })
        )}
      </div>
    </div>
  );
}
