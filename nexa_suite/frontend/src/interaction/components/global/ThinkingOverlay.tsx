/* ThinkingOverlay — a subtle top-centre "Nexa is thinking" pill, shown while an
   `ai:thinking` event is active. Event-driven and inert until a future backend
   adapter (or UI) emits. A minimum visible time avoids flicker on fast events. */
import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { INTERACTION_CONFIG } from "../../config";
import { useInteraction } from "../../context";
import { ThinkingIndicator } from "../ThinkingIndicator";

export function ThinkingOverlay() {
  const { subscribe } = useInteraction();
  const [visible, setVisible] = useState(false);
  const [label, setLabel] = useState<string | undefined>();
  const shownAt = useRef(0);
  const hideTimer = useRef(0);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type !== "ai:thinking") return;
      if (event.payload.active) {
        window.clearTimeout(hideTimer.current);
        setLabel(event.payload.label ?? "Nexa is thinking");
        setVisible(true);
        shownAt.current = performance.now();
      } else {
        const elapsed = performance.now() - shownAt.current;
        const wait = Math.max(0, INTERACTION_CONFIG.feedback.thinkingMinVisibleMs - elapsed);
        hideTimer.current = window.setTimeout(() => setVisible(false), wait);
      }
    });
    return () => {
      unsub();
      window.clearTimeout(hideTimer.current);
    };
  }, [subscribe]);

  return (
    <AnimatePresence>
      {visible && (
        <motion.div
          className="nxi-thinking-pill"
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ type: "spring", stiffness: 300, damping: 26 }}
        >
          <ThinkingIndicator label={label} />
        </motion.div>
      )}
    </AnimatePresence>
  );
}
