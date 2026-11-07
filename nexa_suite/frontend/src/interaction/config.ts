/* ============================================================================
   INTERACTION · CONFIG  (Phase C)
   ----------------------------------------------------------------------------
   Single source of truth for interaction physics and timing. No component
   hardcodes a magnetism strength, damping factor, or duration — they all read
   from here so the whole feel can be tuned in one place.
   ========================================================================== */

export const INTERACTION_CONFIG = {
  /** Global pointer smoothing (0..1 lerp per frame). */
  pointer: { smoothing: 0.2 },

  /** Magnetic cursor ring + dot. */
  cursor: {
    dotSize: 6,
    ringSize: 32,
    ringHoverScale: 1.75,
    ringPressScale: 0.9,
    dotDamping: 0.35,
    ringDamping: 0.16,
  },

  /** Pointer-follow ambient reflection (one cheap transform-only element). */
  reflection: {
    size: 560,
    opacity: 0.12,
    damping: 0.12,
  },

  /** Magnetic hover physics for opt-in elements (useMagnetic / PremiumButton). */
  magnetic: {
    strength: 0.28,
    radius: 100,
    maxOffset: 12,
    stiffness: 220,
    damping: 18,
  },

  /** Notification centre. */
  notification: {
    defaultDurationMs: 4200,
    max: 4,
  },

  /** AI thinking + command-execution overlays. */
  feedback: {
    thinkingMinVisibleMs: 450,
    commandDurationMs: 2600,
  },

  /** Energy borders + connecting lines. */
  energy: {
    borderDurationS: 6,
    lineOpacity: 0.32,
  },

  /** Voice orb visualiser. */
  voice: {
    idlePulseS: 3.2,
    ringCount: 3,
  },
} as const;

/** Elements the magnetic cursor should react to (grow/soften over). */
export const MAGNETIC_TARGETS =
  "[data-magnetic],.nx-btn,.nx-icon-btn,.nx-cmd-send,.nxos-nav-item,.nx-suggestion";

/** Broader set treated as "interactive" for cursor state. */
export const INTERACTIVE_TARGETS = `${MAGNETIC_TARGETS},a,button,input,textarea,select,[role="button"],[tabindex]`;
