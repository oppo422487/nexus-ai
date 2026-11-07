/* NotificationCenter — animated toast stack driven entirely by the event bus.
   Emit `{ type: "notify", payload }` (or call ctx.notify) from anywhere — UI
   today, backend adapters tomorrow — and a toast animates in, auto-dismisses,
   and animates out. Only the toasts capture pointer events. */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Info, TriangleAlert, XCircle, X } from "lucide-react";
import { INTERACTION_CONFIG } from "../../config";
import { useInteraction } from "../../context";
import type { NotificationTone } from "../../events";

interface Toast {
  id: string;
  title: string;
  message?: string;
  tone: NotificationTone;
}

const TONE_ICON = {
  info: Info,
  success: CheckCircle2,
  warning: TriangleAlert,
  error: XCircle,
} as const;

export function NotificationCenter() {
  const { subscribe, reducedMotion } = useInteraction();
  const [toasts, setToasts] = useState<Toast[]>([]);

  useEffect(() => {
    const timers = new Map<string, number>();
    const dismiss = (id: string) => setToasts((prev) => prev.filter((t) => t.id !== id));

    const unsub = subscribe((event) => {
      if (event.type !== "notify") return;
      const id = `t-${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const toast: Toast = {
        id,
        title: event.payload.title,
        message: event.payload.message,
        tone: event.payload.tone ?? "info",
      };
      setToasts((prev) => [...prev, toast].slice(-INTERACTION_CONFIG.notification.max));
      const duration = event.payload.durationMs ?? INTERACTION_CONFIG.notification.defaultDurationMs;
      if (duration > 0) {
        timers.set(id, window.setTimeout(() => dismiss(id), duration));
      }
    });

    return () => {
      unsub();
      timers.forEach((t) => window.clearTimeout(t));
    };
  }, [subscribe]);

  return (
    <div className="nxi-toasts" aria-live="polite">
      <AnimatePresence>
        {toasts.map((toast) => {
          const Icon = TONE_ICON[toast.tone];
          return (
            <motion.div
              key={toast.id}
              className={`nxi-toast ${toast.tone}`}
              layout={!reducedMotion}
              initial={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 32, scale: 0.96 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={reducedMotion ? { opacity: 0 } : { opacity: 0, x: 32, scale: 0.96 }}
              transition={{ type: "spring", stiffness: 320, damping: 28 }}
            >
              <span className="nxi-toast-icon"><Icon size={16} /></span>
              <div className="nxi-toast-body">
                <strong>{toast.title}</strong>
                {toast.message && <span>{toast.message}</span>}
              </div>
              <button
                type="button"
                className="nxi-toast-close"
                aria-label="Dismiss"
                onClick={() => setToasts((prev) => prev.filter((t) => t.id !== toast.id))}
              >
                <X size={13} />
              </button>
            </motion.div>
          );
        })}
      </AnimatePresence>
    </div>
  );
}
