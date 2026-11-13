import React from 'react';

/**
 * Folio-style summary strip: label, figure, and one honest comparison.
 * No icon tiles, no sparklines, no progress bars dressed up as data.
 */
export default function ExecutiveBento({ overview, rooms }) {
  const totalRooms = rooms.length;
  const occupied = rooms.filter(r => !!r.active_booking).length;
  const live = rooms.filter(r => r.authorisation?.authorised).length;
  const pendingFolios = rooms.filter(
    r => r.active_booking?.payment?.payment_status === 'pending'
  ).length;
  const demand = rooms.reduce((sum, r) => sum + (r.latest_telemetry?.power || 0), 0);

  const cells = [
    {
      label: 'Rooms occupied',
      value: totalRooms > 0 ? `${occupied}/${totalRooms}` : '—',
      note: totalRooms > 0 ? `${Math.round((occupied / totalRooms) * 100)}% of the wing` : 'No rooms on file',
    },
    {
      label: 'Circuits live',
      value: totalRooms > 0 ? `${live}` : '—',
      note: `${totalRooms - live} cut off at the relay`,
    },
    {
      label: 'Live demand',
      value: demand.toFixed(2),
      unit: 'kW',
      note: occupied > 0 ? 'Across rooms drawing now' : 'Nothing drawing',
    },
    {
      label: 'Folios pending',
      value: `${pendingFolios}`,
      note: pendingFolios > 0 ? 'Power held until settled' : 'All settled',
      tone: pendingFolios > 0 ? 'brass' : 'ink',
    },
  ];

  return (
    <div className="grid grid-cols-2 overflow-hidden rounded-card border border-line bg-surface shadow-card lg:grid-cols-4">
      {cells.map((cell, index) => (
        <div
          key={cell.label}
          className={`px-4 py-3.5 ${index > 0 ? 'border-l border-line' : ''} ${index === 2 ? 'max-lg:border-t max-lg:border-l-0' : ''} ${index === 3 ? 'max-lg:border-t' : ''}`}
        >
          <p className="text-[11px] text-ink-3">{cell.label}</p>
          <p className="mt-1 flex items-baseline gap-1">
            <span className={`num font-mono text-[22px] leading-none tracking-tight ${cell.tone === 'brass' ? 'text-brass-ink' : 'text-ink'}`}>
              {cell.value}
            </span>
            {cell.unit && <span className="font-mono text-[11px] text-ink-3">{cell.unit}</span>}
          </p>
          <p className="mt-1.5 text-[11px] text-ink-3">{cell.note}</p>
        </div>
      ))}
    </div>
  );
}
