/* ============================================================================
   MOTION ARCHITECTURE  (Phase A — tokens only)
   ----------------------------------------------------------------------------
   Motion values as data, mirroring the CSS motion tokens in tokens.css so JS
   (framer-motion) and CSS stay in sync. Phase A ships only subtle, meaningful
   transitions — no advanced/continuous animation. Richer choreography arrives
   in a later phase and should still consume these tokens.
   ========================================================================== */

/** Durations in seconds (framer-motion uses seconds; CSS uses ms). */
export const duration = {
  instant: 0.08,
  fast: 0.12,
  base: 0.2,
  slow: 0.32,
  slower: 0.48,
} as const;

/** Cubic-bezier easings, matching the CSS `--nx-ease-*` tokens. */
export const easing = {
  standard: [0.22, 0.68, 0.28, 1],
  out: [0.16, 1, 0.3, 1],
  in: [0.4, 0, 1, 1],
  inOut: [0.65, 0, 0.35, 1],
  spring: [0.34, 1.56, 0.64, 1],
} as const;

/** Standard transition presets. */
export const transition = {
  base: { duration: duration.base, ease: easing.standard },
  enter: { duration: duration.slow, ease: easing.out },
} as const;

/** Reusable framer-motion variants for the subtle Phase-A motions. */
export const variants = {
  /** Page/section entrance: rise + fade. */
  rise: {
    initial: { opacity: 0, y: 16 },
    animate: { opacity: 1, y: 0 },
  },
  fade: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
  },
} as const;

export type MotionTokens = {
  duration: typeof duration;
  easing: typeof easing;
  transition: typeof transition;
  variants: typeof variants;
  /** True when the user prefers reduced motion; consumers should skip motion. */
  reduced: boolean;
};

export const motionTokens: Omit<MotionTokens, "reduced"> = {
  duration,
  easing,
  transition,
  variants,
};
