import React, { useState } from 'react';
import { X, User, CreditCard, Calendar, ShieldCheck, Zap, Sparkles } from 'lucide-react';

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
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-3xl border border-slate-200/90 shadow-2xl max-w-lg w-full overflow-hidden transition-all transform scale-100">
        <div className="p-6 border-b border-slate-100 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center border border-emerald-100">
              <Zap className="h-5 w-5" />
            </div>
            <div>
              <h3 className="text-base font-extrabold text-slate-900">
                Check In Guest • {room.room_code}
              </h3>
              <p className="text-xs font-medium text-slate-400">
                {room.display_name}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-5">
          <div>
            <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
              Guest Full Name
            </label>
            <div className="relative">
              <User className="h-4 w-4 text-slate-400 absolute left-3.5 top-3" />
              <input
                type="text"
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                placeholder="e.g. Elena Rostova"
                className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 outline-none text-sm text-slate-800 transition font-medium"
                required
                autoFocus
              />
            </div>
            <div className="flex items-center gap-1.5 mt-2 overflow-x-auto pb-1">
              <span className="text-[10px] text-slate-400 font-semibold uppercase shrink-0">Suggestions:</span>
              {presetGuests.map((preset) => (
                <button
                  type="button"
                  key={preset}
                  onClick={() => setGuestName(preset)}
                  className="px-2 py-0.5 rounded-md bg-slate-100 hover:bg-slate-200 text-slate-600 text-[11px] font-medium transition shrink-0"
                >
                  {preset}
                </button>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Stay Duration
              </label>
              <div className="relative">
                <Calendar className="h-4 w-4 text-slate-400 absolute left-3.5 top-3" />
                <select
                  value={nights}
                  onChange={(e) => setNights(Number(e.target.value))}
                  className="w-full pl-10 pr-4 py-2.5 rounded-xl border border-slate-200 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-100 outline-none text-sm text-slate-800 transition font-medium bg-white appearance-none cursor-pointer"
                >
                  <option value={1}>1 Night</option>
                  <option value={2}>2 Nights</option>
                  <option value={3}>3 Nights</option>
                  <option value={5}>5 Nights</option>
                  <option value={7}>7 Nights</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-bold text-slate-700 uppercase tracking-wider mb-2">
                Total Folio Rate
              </label>
              <div className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 flex items-center justify-between">
                <span className="text-xs text-slate-500">${roomRate} × {nights}n</span>
                <span className="text-base font-extrabold text-slate-900 font-mono">${totalAmount}</span>
              </div>
            </div>
          </div>

          <div className="p-4 rounded-2xl border border-slate-200 bg-slate-50/80 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-start gap-2.5">
                <CreditCard className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                <div>
                  <span className="text-xs font-bold text-slate-900 block">
                    Verify Payment & Energize Circuit
                  </span>
                  <p className="text-[11px] text-slate-500 leading-relaxed mt-0.5">
                    {settlePaymentNow
                      ? 'Payment confirmed on check-in. Workpeg webhook will immediately dispatch POWER_ON to the room switch.'
                      : 'Leave payment pending. Circuit will remain safely cutoff until payment is verified.'}
                  </p>
                </div>
              </div>
              <input
                type="checkbox"
                checked={settlePaymentNow}
                onChange={(e) => setSettlePaymentNow(e.target.checked)}
                className="h-4 w-4 rounded text-emerald-600 focus:ring-emerald-500 border-slate-300 mt-0.5 cursor-pointer"
              />
            </div>
          </div>

          <div className="pt-2 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2.5 rounded-xl border border-slate-200 text-slate-600 hover:bg-slate-50 text-xs font-semibold transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading || !guestName.trim()}
              className="px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition shadow-sm flex items-center gap-2 disabled:opacity-50"
            >
              <Sparkles className="h-4 w-4" />
              <span>{isLoading ? 'Processing...' : settlePaymentNow ? 'Check In & Enable Power' : 'Check In (Payment Pending)'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
