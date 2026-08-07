import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import Icon from '../components/Icon';

const ToastContext = createContext({ notify: () => {} });

// eslint-disable-next-line react-refresh/only-export-components
export const useToast = () => useContext(ToastContext);

let seq = 0;

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const timersRef = useRef(new Map());

  const dismiss = useCallback((id) => {
    setToasts((current) => current.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      window.clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const notify = useCallback(
    (message, { tone = 'info', duration = 2600 } = {}) => {
      const id = ++seq;
      setToasts((current) => [...current, { id, message, tone }]);
      const timer = window.setTimeout(() => dismiss(id), duration);
      timersRef.current.set(id, timer);
      return id;
    },
    [dismiss],
  );

  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((t) => window.clearTimeout(t));
      timers.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ notify, dismiss }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 left-1/2 z-[200] flex w-full max-w-sm -translate-x-1/2 flex-col items-center gap-2 px-3"
        aria-live="polite"
        aria-atomic="false"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="status"
            className={`pointer-events-auto flex w-full items-center gap-2.5 rounded-2xl border px-4 py-2.5 text-[13px] shadow-glass backdrop-blur-2xl animate-message-in ${
              toast.tone === 'error'
                ? 'border-brand-mist-400/25 bg-brand-mist-500/[0.12] text-brand-mist-100'
                : 'border-brand-200/15 bg-[#032f30]/85 text-slate-200'
            }`}
          >
            <Icon
              name={toast.tone === 'error' ? 'shield' : 'sparkles'}
              className={`h-4 w-4 shrink-0 ${toast.tone === 'error' ? 'text-brand-mist-300' : 'text-brand-300'}`}
            />
            <span className="flex-1">{toast.message}</span>
            <button
              type="button"
              onClick={() => dismiss(toast.id)}
              className="shrink-0 rounded-lg p-0.5 text-slate-500 transition hover:text-slate-200 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand-300/40"
              aria-label="Dismiss notification"
            >
              <Icon name="close" className="h-3.5 w-3.5" />
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}
