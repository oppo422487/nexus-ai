/* ============================================================================
   ENVIRONMENT · usePerformance
   ----------------------------------------------------------------------------
   React state for the environment's runtime: whether rendering should be paused
   (tab hidden / window blurred / minimized), whether the user prefers reduced
   motion, and the current adaptive quality tier (with a setter the in-canvas
   PerformanceMonitor drives). One hook, consumed once by the EnvironmentEngine.
   ========================================================================== */

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { QUALITY_PRESETS, type QualityTier, type QualityPreset } from "../config";
import { detectInitialTier, stepTier } from "../components/PerformanceManager";

export interface PerformanceState {
  /** Rendering should stop entirely (never allocate frames). */
  paused: boolean;
  /** User prefers reduced motion — render a static frame, no animation. */
  reducedMotion: boolean;
  quality: QualityTier;
  preset: QualityPreset;
  /** Ask the adaptive loop to move one tier up/down (clamped). */
  adjustQuality: (direction: 1 | -1) => void;
}

export function usePerformance(): PerformanceState {
  const [quality, setQuality] = useState<QualityTier>(() => detectInitialTier());
  const [paused, setPaused] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);

  // Cooldown so adaptive changes don't oscillate frame-to-frame.
  const lastChange = useRef(0);

  // Pause when the document is hidden or the window loses focus/minimizes.
  useEffect(() => {
    const evaluate = () => {
      const hidden = typeof document !== "undefined" && document.hidden;
      setPaused(!!hidden || !document.hasFocus());
    };
    evaluate();
    document.addEventListener("visibilitychange", evaluate);
    window.addEventListener("focus", evaluate);
    window.addEventListener("blur", evaluate);
    return () => {
      document.removeEventListener("visibilitychange", evaluate);
      window.removeEventListener("focus", evaluate);
      window.removeEventListener("blur", evaluate);
    };
  }, []);

  // Reduced-motion preference.
  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const update = () => setReducedMotion(mq.matches);
    update();
    mq.addEventListener?.("change", update);
    return () => mq.removeEventListener?.("change", update);
  }, []);

  const adjustQuality = useCallback((direction: 1 | -1) => {
    const now = performance.now();
    if (now - lastChange.current < 4000) return; // 4s cooldown between steps
    lastChange.current = now;
    setQuality((current) => stepTier(current, direction));
  }, []);

  const preset = QUALITY_PRESETS[quality];

  return useMemo(
    () => ({ paused, reducedMotion, quality, preset, adjustQuality }),
    [paused, reducedMotion, quality, preset, adjustQuality],
  );
}
