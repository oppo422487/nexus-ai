/* ThinkingIndicator — a small inline "AI is thinking" cue: three phased dots
   with an optional label. Reusable anywhere; respects reduced motion. */
import { motion } from "framer-motion";
import { useInteraction } from "../context";

export interface ThinkingIndicatorProps {
  label?: string;
  className?: string;
}

export function ThinkingIndicator({ label, className }: ThinkingIndicatorProps) {
  const { reducedMotion } = useInteraction();
  return (
    <span className={`nxi-thinking ${className ?? ""}`} role="status" aria-live="polite">
      <span className="nxi-thinking-dots" aria-hidden="true">
        {[0, 1, 2].map((i) => (
          <motion.i
            key={i}
            animate={reducedMotion ? { opacity: 0.6 } : { opacity: [0.2, 1, 0.2], y: [0, -2, 0] }}
            transition={{ duration: 1.1, repeat: Infinity, ease: "easeInOut", delay: i * 0.16 }}
          />
        ))}
      </span>
      {label && <span className="nxi-thinking-label">{label}</span>}
    </span>
  );
}
