/* PremiumButton — an opt-in button with magnetic hover physics, a press spring,
   and a pointer-reactive sheen. Composes the existing `.nx-btn` design-system
   styling (no duplicated button visuals) and layers interaction on top. */
import { forwardRef, type ReactNode } from "react";
import { motion, type HTMLMotionProps } from "framer-motion";
import { useMagnetic } from "../hooks/useMagnetic";
import { useInteraction } from "../context";

export interface PremiumButtonProps extends Omit<HTMLMotionProps<"button">, "ref"> {
  /** Design-system variant class suffix, e.g. "ghost" | "danger". */
  variant?: "primary" | "ghost" | "danger" | "amber";
}

export const PremiumButton = forwardRef<HTMLButtonElement, PremiumButtonProps>(
  function PremiumButton({ variant = "primary", className, children, ...rest }, ref) {
    const { reducedMotion } = useInteraction();
    const { x, y, onPointerMove, onPointerLeave } = useMagnetic();
    const variantClass = variant === "primary" ? "" : variant;

    return (
      <motion.button
        ref={ref}
        className={`nx-btn nxi-btn ${variantClass} ${className ?? ""}`}
        style={{ x, y }}
        onPointerMove={onPointerMove}
        onPointerLeave={onPointerLeave}
        whileTap={reducedMotion ? undefined : { scale: 0.96 }}
        transition={{ type: "spring", stiffness: 300, damping: 20 }}
        {...rest}
      >
        <span className="nxi-btn-sheen" aria-hidden="true" />
        <span className="nxi-btn-content">{children as ReactNode}</span>
      </motion.button>
    );
  },
);
