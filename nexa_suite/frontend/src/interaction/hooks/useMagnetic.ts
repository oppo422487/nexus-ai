/* ============================================================================
   INTERACTION · useMagnetic
   ----------------------------------------------------------------------------
   Hover physics for a single element: while the pointer is near, the element
   eases toward it (clamped), springing back on leave. Returns spring-backed
   x/y MotionValues plus the handlers to attach. Disabled when reduced motion
   or a coarse pointer is active. Pure, reusable, no duplication.
   ========================================================================== */

import { useCallback } from "react";
import { useMotionValue, useSpring, type MotionValue } from "framer-motion";
import { INTERACTION_CONFIG } from "../config";
import { useInteraction } from "../context";

export interface MagneticApi {
  x: MotionValue<number>;
  y: MotionValue<number>;
  onPointerMove: (event: React.PointerEvent<HTMLElement>) => void;
  onPointerLeave: () => void;
}

export function useMagnetic(strengthOverride?: number): MagneticApi {
  const { reducedMotion, coarsePointer } = useInteraction();
  const cfg = INTERACTION_CONFIG.magnetic;
  const rawX = useMotionValue(0);
  const rawY = useMotionValue(0);
  const x = useSpring(rawX, { stiffness: cfg.stiffness, damping: cfg.damping });
  const y = useSpring(rawY, { stiffness: cfg.stiffness, damping: cfg.damping });

  const enabled = !reducedMotion && !coarsePointer;
  const strength = strengthOverride ?? cfg.strength;

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLElement>) => {
      if (!enabled) return;
      const rect = event.currentTarget.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = event.clientX - cx;
      const dy = event.clientY - cy;
      const clamp = (v: number) => Math.max(-cfg.maxOffset, Math.min(cfg.maxOffset, v * strength));
      rawX.set(clamp(dx));
      rawY.set(clamp(dy));
    },
    [enabled, strength, cfg.maxOffset, rawX, rawY],
  );

  const onPointerLeave = useCallback(() => {
    rawX.set(0);
    rawY.set(0);
  }, [rawX, rawY]);

  return { x, y, onPointerMove, onPointerLeave };
}
