import React, { useState } from 'react';
import { X } from 'lucide-react';

export default function CheckInModal({
  isOpen,
  room,
  onClose,
  onSubmit,
  isLoading
}) {
  const [guestName, setGuestName] = useState('');
  const [nights, setNights] = useState(1);
  const [settlePaymentNow, setSettlePaymentNow] = useState(true);

  if (!isOpen || !room) return null;

  const roomRate = room.room_code === 'ROOM-204' ? 195 : room.room_code === 'ROOM-101' ? 240 : 135;
  const totalAmount = roomRate * nights;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!guestName.trim()) return;

    onSubmit({
      roomId: room.id,
      guestLabel: guestName.trim(),
      nights,
      settlePaymentNow,
      amount: totalAmount,
    });
  };

  const presetGuests = [
    'Elena Rostova',
    'David Kim',
    'Carlos Mendez',
    'Amara Okafor',
  ];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/30 p-4">
      <div className="w-full max-w-[440px] animate-rise overflow-hidden rounded-card border border-line bg-surface shadow-pop">
        <div className="flex items-start justify-between border-b border-line px-4 py-3">
          <div>
            <p className="text-[11px] text-ink-3">Check in guest</p>
            <div className="mt-0.5 flex items-baseline gap-2">
              <h3 className="font-mono text-[15px] font-medium text-ink">{room.room_code}</h3>
              <span className="truncate text-[11px] text-ink-3">{room.display_name}</span>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-[6px] p-1 text-ink-4 transition-colors duration-150 hover:bg-paper hover:text-ink"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 px-4 py-4">
          <div>
            <label htmlFor="guest-name" className="mb-1 block text-[11px] text-ink-3">
              Guest name
            </label>
            <input
              id="guest-name"
              type="text"
              value={guestName}
              onChange={(e) => setGuestName(e.target.value)}
              placeholder="Elena Rostova"
              className="h-9 w-full rounded-control border border-line bg-surface px-3 text-[13px] text-ink placeholder:text-ink-4 focus:border-line-strong"
              required
              autoFocus
            />
            <div className="mt-1.5 flex items-center gap-1.5 overflow-x-auto pb-0.5">
              {presetGuests.map((preset) => (
                <button
                  type="button"
                  key={preset}
                  onClick={() => setGuestName(preset)}
                  className="shrink-0 rounded-[6px] border border-line px-1.5 py-0.5 text-[11px] text-ink-3 transition-colors duration-150 hover:border-line-strong hover:text-ink"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label htmlFor="stay-nights" className="mb-1 block text-[11px] text-ink-3">
                Nights
              </label>
              <select
                id="stay-nights"
                value={nights}
                onChange={(e) => setNights(Number(e.target.value))}
                className="h-9 w-full cursor-pointer appearance-none rounded-control border border-line bg-surface px-3 text-[13px] text-ink focus:border-line-strong"
              >
                <option value={1}>1</option>
                <option value={2}>2</option>
                <option value={3}>3</option>
                <option value={5}>5</option>
                <option value={7}>7</option>
              </select>
            </div>

            <div>
              <span className="mb-1 block text-[11px] text-ink-3">Folio</span>
              <div className="flex h-9 items-center justify-between rounded-control border border-line bg-paper px-3">
                <span className="num font-mono text-[11px] text-ink-3">${roomRate} × {nights}</span>
                <span className="num font-mono text-[13px] font-medium text-ink">${totalAmount}</span>
              </div>
            </div>
          </div>

          <div className="rounded-panel border border-line bg-paper px-3 py-2.5">
            <label className="flex cursor-pointer items-start gap-2.5">
              <input
                type="checkbox"
                checked={settlePaymentNow}
                onChange={(e) => setSettlePaymentNow(e.target.checked)}
                className="mt-0.5 h-3.5 w-3.5 cursor-pointer rounded-[3px] border-line-strong accent-ink"
              />
              <span>
                <span className="block text-xs font-medium text-ink">Settle the folio now</span>
                <span className="mt-0.5 block text-[11px] leading-relaxed text-ink-3">
                  {settlePaymentNow
                    ? 'Payment confirms on check-in and the payment hook closes the relay.'
                    : 'Folio stays pending and the circuit stays open until payment is verified.'}
                </span>
              </span>
            </label>
          </div>

          <div className="flex items-center justify-end gap-2 pt-1">
            <button
              type="button"
              onClick={onClose}
              className="h-8 rounded-control px-3 text-xs text-ink-2 transition-colors duration-150 hover:text-ink"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !guestName.trim()}
              className="h-8 rounded-control bg-ink px-3 text-xs font-medium text-paper transition-colors duration-150 hover:bg-ink-2 active:scale-[0.99] disabled:opacity-50"
            >
              {isLoading ? 'Working' : settlePaymentNow ? 'Check in and release power' : 'Check in, hold power'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
