import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, Zap, X, Info } from 'lucide-react';

export default function ToastNotification({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      onClose();
    }, 4500);
    return () => clearTimeout(timer);
  }, [toast, onClose]);

  if (!toast) return null;

  const { type = 'success', title, message, workpegHook } = toast;

  return (
    <div className="fixed bottom-6 right-6 z-50 max-w-sm w-full bg-white rounded-2xl border border-slate-200 shadow-2xl p-4 flex items-start gap-3 animate-slide-up">
      <div className={`h-8 w-8 rounded-xl flex items-center justify-center shrink-0 mt-0.5 ${
        type === 'error' ? 'bg-rose-100 text-rose-600' :
        type === 'warning' ? 'bg-amber-100 text-amber-600' :
        type === 'info' ? 'bg-blue-100 text-blue-600' :
        'bg-emerald-100 text-emerald-600'
      }`}>
        {type === 'error' ? <AlertTriangle className="h-4 w-4" /> :
         type === 'warning' ? <AlertTriangle className="h-4 w-4" /> :
         type === 'info' ? <Info className="h-4 w-4" /> :
         <Zap className="h-4 w-4" />}
      </div>

      <div className="flex-1 min-w-0">
        <h4 className="text-xs font-extrabold text-slate-900">{title}</h4>
        <p className="text-[11px] text-slate-600 mt-0.5 leading-relaxed">{message}</p>
        {workpegHook && (
          <div className="mt-1.5 inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-slate-100 text-slate-600 font-mono text-[9px]">
            <span>Hook:</span>
            <span className="font-semibold text-emerald-700">{workpegHook}</span>
          </div>
        )}
      </div>

      <button
        onClick={onClose}
        className="p-1 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition"
      >
        <X className="h-3.5 w-3.5" />
      </button>
    </div>
  );
}
