/* CommandExecutionOverlay — animated feedback for command execution, driven by
   `command:execute` events (status: start → success | error). Shows a bottom-
   centre status chip that morphs with the result and auto-dismisses. Inert
   until an event is emitted; a natural fit for the existing confirm/execute
   flow to connect in a later phase. */
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { INTERACTION_CONFIG } from "../../config";
import { useInteraction } from "../../context";
import type { CommandStatus } from "../../events";

interface CommandView {
  id: string;
  label: string;
  status: CommandStatus;
}

export function CommandExecutionOverlay() {
  const { subscribe, reducedMotion } = useInteraction();
  const [command, setCommand] = useState<CommandView | null>(null);
  const hideTimer = useRef(0);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "command:execute") return;
      const { id = "cmd", label, status } = event.payload;
      window.clearTimeout(hideTimer.current);
      setCommand({ id, label, status });
      if (status !== "start") {
        hideTimer.current = window.setTimeout(
          () => setCommand(null),
          INTERACTION_CONFIG.feedback.commandDurationMs,
        );
      }
    });
    return () => {
      unsub();
      window.clearTimeout(hideTimer.current);
    };
  }, [subscribe]);

  return (
    <AnimatePresence>
      {command && (
        <motion.div
          key={command.id + command.status}
          className={`nxi-command ${command.status}`}
          initial={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.96 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={reducedMotion ? { opacity: 0 } : { opacity: 0, y: 16, scale: 0.96 }}
          transition={{ type: "spring", stiffness: 320, damping: 26 }}
        >
          <span className="nxi-command-icon">
            {command.status === "start" && (
              <motion.span
                animate={reducedMotion ? undefined : { rotate: 360 }}
                transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
                style={{ display: "inline-flex" }}
              >
                <Loader2 size={16} />
              </motion.span>
            )}
            {command.status === "success" && <CheckCircle2 size={16} />}
            {command.status === "error" && <XCircle size={16} />}
          </span>
          <span className="nxi-command-label">{command.label}</span>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
