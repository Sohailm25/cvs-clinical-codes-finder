// ABOUTME: Toast notification component for user feedback.
// ABOUTME: Displays temporary messages that auto-dismiss.

import { Check, X, Info } from 'lucide-react';
import { useToastStore } from '../stores/toastStore';

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-24 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`flex items-center gap-2 px-4 py-2.5 rounded-lg shadow-theme-lg animate-in slide-in-from-bottom-2 fade-in duration-200 ${
            toast.type === 'success'
              ? 'bg-[var(--success)] text-white'
              : toast.type === 'error'
              ? 'bg-[var(--error)] text-white'
              : 'bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-default)]'
          }`}
        >
          {toast.type === 'success' && <Check className="w-4 h-4" />}
          {toast.type === 'error' && <X className="w-4 h-4" />}
          {toast.type === 'info' && <Info className="w-4 h-4" />}
          <span className="text-sm font-medium">{toast.message}</span>
          <button
            onClick={() => removeToast(toast.id)}
            className="ml-2 p-0.5 hover:opacity-80 transition-opacity"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}
