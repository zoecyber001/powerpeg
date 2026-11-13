import React, { useEffect } from 'react';
import { X } from 'lucide-react';

export default function ToastNotification({ toast, onClose }) {
  useEffect(() => {
    if (!toast) return;
    const timer = setTimeout(() => {
      onClose();
    }, 6000);
    return () => clearTimeout(timer);
  }, [toast, onClose]);

  if (!toast) return null;

  const { type = 'success', title, message, workpegHook } = toast;

  const rule =
    type === 'error' ? 'border-l-brick' :
    type === 'warning' ? 'border-l-brass' :
    type === 'info' ? 'border-l-line-strong' :
    'border-l-moss';

  return (
    <div
      role="status"
      className={`fixed bottom-5 right-5 z-50 w-full max-w-[340px] animate-rise rounded-card border border-line border-l-2 bg-surface p-3 shadow-pop ${rule}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-xs font-medium text-ink">{title}</p>
          <p className="mt-1 text-[11px] leading-relaxed text-ink-2">{message}</p>
          {workpegHook && (
            <p className="mt-1.5 truncate font-mono text-[10px] text-ink-3">
              hook · {workpegHook}
            </p>
          )}
        </div>

        <button
          onClick={onClose}
          aria-label="Dismiss"
          className="rounded-[6px] p-1 text-ink-4 transition-colors duration-150 hover:bg-paper hover:text-ink"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
