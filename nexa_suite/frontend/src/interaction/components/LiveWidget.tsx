/* LiveWidget — wraps a dashboard widget with a subtle entrance and a "live"
   pulse when its data changes. Pass a changing `value` (or `pulseKey`) and the
   widget flashes a soft accent ring to signal fresh data. Reusable + opt-in. */
import { useEffect, useRef, useState, type ReactNode } from "react";
import { motion, useAnimationControls } from "framer-motion";
import { useInteraction } from "../context";
import { motionTokens } from "@/design/motion";

export interface LiveWidgetProps {
  children: ReactNode;
  /** Any value that, when it changes, signals fresh data and triggers a pulse. */
  pulseKey?: string | number;
  className?: string;
}

export function LiveWidget({ children, pulseKey, className }: LiveWidgetProps) {
  const { reducedMotion } = useInteraction();
  const controls = useAnimationControls();
  const mounted = useRef(false);
  const [firstPaint] = useState(() => !reducedMotion);

  useEffect(() => {
    if (!mounted.current) {
      mounted.current = true;
      return; // don't pulse on initial mount
    }
    if (reducedMotion) return;
    controls.start({
      boxShadow: [
        "0 0 0 0 rgba(34,211,238,0)",
        "0 0 0 2px rgba(34,211,238,0.4)",
        "0 0 0 0 rgba(34,211,238,0)",
      ],
      transition: { duration: 1.2, ease: "easeOut" },
    });
  }, [pulseKey, reducedMotion, controls]);

  return (
    <motion.div
      className={`nxi-live ${className ?? ""}`}
      initial={firstPaint ? { opacity: 0, y: 12 } : false}
      animate={controls}
      whileInView={firstPaint ? { opacity: 1, y: 0 } : undefined}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: motionTokens.duration.slow, ease: motionTokens.easing.out }}
    >
      {children}
    </motion.div>
  );
}
