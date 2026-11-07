/* MagneticCursor — a custom cursor ring + dot that trail the pointer with
   spring physics and swell over interactive targets. The native cursor is kept
   (so text/click affordances stay normal); this is an additive premium layer.
   Consumes the single shared pointer stream. Disabled for reduced motion /
   touch. Fixed, pointer-events: none. */
import { useEffect, useState } from "react";
import { motion, useSpring } from "framer-motion";
import { INTERACTION_CONFIG, MAGNETIC_TARGETS } from "../../config";
import { useInteraction } from "../../context";
import { pointerActive, pointerX, pointerY } from "../../hooks/usePointer";

export function MagneticCursor() {
  const { reducedMotion, coarsePointer, quality } = useInteraction();
  const cfg = INTERACTION_CONFIG.cursor;
  const [hovering, setHovering] = useState(false);
  const [pressing, setPressing] = useState(false);

  const ringX = useSpring(pointerX, { stiffness: 260, damping: 26, mass: 0.6 });
  const ringY = useSpring(pointerY, { stiffness: 260, damping: 26, mass: 0.6 });
  const dotX = useSpring(pointerX, { stiffness: 520, damping: 34 });
  const dotY = useSpring(pointerY, { stiffness: 520, damping: 34 });
  const opacity = useSpring(pointerActive, { stiffness: 200, damping: 30 });

  const disabled = reducedMotion || coarsePointer || quality === "off";

  useEffect(() => {
    if (disabled) return;
    const over = (e: PointerEvent) => {
      const el = e.target as Element | null;
      setHovering(!!el?.closest?.(MAGNETIC_TARGETS));
    };
    const down = () => setPressing(true);
    const up = () => setPressing(false);
    document.addEventListener("pointerover", over, true);
    document.addEventListener("pointerdown", down, true);
    document.addEventListener("pointerup", up, true);
    return () => {
      document.removeEventListener("pointerover", over, true);
      document.removeEventListener("pointerdown", down, true);
      document.removeEventListener("pointerup", up, true);
    };
  }, [disabled]);

  if (disabled) return null;

  const ringScale = pressing ? cfg.ringPressScale : hovering ? cfg.ringHoverScale : 1;

  return (
    <div className="nxi-cursor" aria-hidden="true">
      <motion.span
        className="nxi-cursor-ring"
        data-hovering={hovering || undefined}
        style={{ x: ringX, y: ringY, opacity, width: cfg.ringSize, height: cfg.ringSize }}
        animate={{ scale: ringScale }}
        transition={{ type: "spring", stiffness: 300, damping: 22 }}
      />
      <motion.span
        className="nxi-cursor-dot"
        style={{ x: dotX, y: dotY, opacity, width: cfg.dotSize, height: cfg.dotSize }}
      />
    </div>
  );
}
