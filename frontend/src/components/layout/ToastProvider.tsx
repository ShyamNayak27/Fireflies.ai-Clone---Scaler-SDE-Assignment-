"use client";

import { createContext, useCallback, useContext, useRef, useState } from "react";

type ToastKind = "info" | "success" | "error";
type Toast = { id: number; message: string; kind: ToastKind };

type ToastContextValue = {
  show: (message: string, kind?: ToastKind) => void;
};

const ToastContext = createContext<ToastContextValue | null>(null);

const KIND_COLOR: Record<ToastKind, string> = {
  info: "var(--text)",
  success: "var(--accent-success)",
  error: "#e0503f",
};

/**
 * One small, app-wide toast stack — mounted once in the root layout (see
 * layout.tsx) so any component can call `useToast().show(...)` instead of
 * inventing its own inline notification (IconRail's "coming soon" bubble used
 * to be exactly that ad-hoc pattern before this existed).
 */
export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const nextId = useRef(0);

  const show = useCallback((message: string, kind: ToastKind = "info") => {
    const id = nextId.current++;
    setToasts((prev) => [...prev, { id, message, kind }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3200);
  }, []);

  return (
    <ToastContext.Provider value={{ show }}>
      {children}
      <div
        className="pointer-events-none fixed bottom-4 left-1/2 z-[100] flex -translate-x-1/2 flex-col items-center gap-2"
        aria-live="polite"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="status"
            className="pointer-events-auto flex items-center gap-2 rounded-[var(--radius-control)] px-4 py-2.5 text-sm font-medium text-white shadow-lg"
            style={{ background: "var(--text)" }}
          >
            <span
              className="h-1.5 w-1.5 flex-none rounded-full"
              style={{ background: KIND_COLOR[t.kind] }}
              aria-hidden
            />
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) throw new Error("useToast must be used inside <ToastProvider>");
  return ctx;
}
