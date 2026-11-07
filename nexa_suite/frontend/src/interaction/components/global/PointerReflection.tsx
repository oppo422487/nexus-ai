/* PointerReflection — a single soft light that follows the pointer, giving the
   whole surface a sense of dynamic, physical lighting/reflection. One element,
   transform-only (no per-frame repaint), screen-blended. Disabled for reduced
   motion / low quality. Fixed, pointer-events: none. */
import { motion, useSpring, useTransform } from "framer-motion";
import { INTERACTION_CONFIG } from "../../config";
import { useInteraction } from "../../context";
import { pointerActive, pointerX, pointerY } from "../../hooks/usePointer";

export function PointerReflection() {
  const { reducedMotion, quality } = useInteraction();
  const cfg = INTERACTION_CONFIG.reflection;
  const half = cfg.size / 2;

  const sx = useSpring(pointerX, { stiffness: 120, damping: 26, mass: 0.8 });
  const sy = useSpring(pointerY, { stiffness: 120, damping: 26, mass: 0.8 });
  const x = useTransform(sx, (v) => v - half);
  const y = useTransform(sy, (v) => v - half);
  const opacity = useSpring(pointerActive, { stiffness: 140, damping: 30 });

  if (reducedMotion || quality === "off") return null;

  return (
    <motion.div
      className="nxi-reflection"
      aria-hidden="true"
      style={{ x, y, opacity, width: cfg.size, height: cfg.size, ["--nxi-refl-opacity" as string]: cfg.opacity }}
    />
  );
}
