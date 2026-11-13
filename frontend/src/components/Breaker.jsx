import React from 'react';

/**
 * The product's one signature detail: a breaker toggle.
 * Nub up means the circuit is closed and live; down means it is open and cut.
 * Used in the rack, the room card and the inspector, and nowhere else.
 */
export default function Breaker({ on, alert = false, label = true, compact = false }) {
  const nub = alert ? 'bg-brick' : on ? 'bg-brass' : 'bg-ink-4';

  return (
    <span className="inline-flex items-center gap-2">
      <span
        aria-hidden="true"
        className={`relative inline-flex w-[11px] items-center justify-center rounded-[4px] border transition-colors duration-150 ${
          compact ? 'h-4' : 'h-[18px]'
        } ${on ? 'border-brass/40 bg-brass-soft' : 'border-line-strong bg-paper'}`}
      >
        <span
          className={`absolute h-[6px] w-[6px] rounded-[2px] transition-transform duration-150 ${nub} ${
            on ? '-translate-y-[4px]' : 'translate-y-[4px]'
          }`}
        />
      </span>
      {label && (
        <span className={`${compact ? 'text-[11px]' : 'text-xs'} ${on ? 'text-ink' : 'text-ink-3'}`}>
          {alert ? 'Draw unbilled' : on ? 'Closed · live' : 'Open · cut off'}
        </span>
      )}
    </span>
  );
}
