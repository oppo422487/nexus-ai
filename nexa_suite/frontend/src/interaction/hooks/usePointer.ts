/* ============================================================================
   INTERACTION · usePointer
   ----------------------------------------------------------------------------
   One rAF-throttled pointer listener for the whole app. Exposes shared
   MotionValues (raw client px) that cursor/reflection layers consume, and
   publishes CSS custom properties so token-driven CSS can react to the pointer
   without any per-frame JS. Mounted exactly once (by the provider).
   ========================================================================== */

import { useEffect } from "react";
import { motionValue } from "framer-motion";

/** Shared, module-level pointer position in client pixels. */
export const pointerX = motionValue(typeof window !== "undefined" ? window.innerWidth / 2 : 0);
export const pointerY = motionValue(typeof window !== "undefined" ? window.innerHeight / 2 : 0);
/** 1 while the pointer is inside the window, 0 when it has left. */
export const pointerActive = motionValue(0);

/** Attach the single global pointer tracker. Call once.
 *
 * Physics-based smoothing: raw pointer events set a *target*; a continuous rAF
 * loop critically-eases the published position toward it, so every tilt /
 * parallax / reflection consumer (WebGL camera, card tilt, spotlight) inherits
 * weighty inertia instead of snapping. The loop self-parks once the value has
 * settled and no new input is arriving, so idle cost is zero. */
export function usePointerTracking(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;
    const root = document.documentElement;

    // target (raw) + smoothed (published) positions
    let tx = pointerX.get();
    let ty = pointerY.get();
    let sx = tx;
    let sy = ty;
    let raf = 0;
    let running = false;

    const SMOOTH = 0.12; // easing factor per frame ≈ spring stiffness
    const EPS = 0.05;

    const publish = () => {
      pointerX.set(sx);
      pointerY.set(sy);
      const w = window.innerWidth || 1;
      const h = window.innerHeight || 1;
      root.style.setProperty("--nx-pointer-x", `${sx.toFixed(1)}px`);
      root.style.setProperty("--nx-pointer-y", `${sy.toFixed(1)}px`);
      root.style.setProperty("--nx-mx", (sx / w - 0.5).toFixed(4));
      root.style.setProperty("--nx-my", (sy / h - 0.5).toFixed(4));
    };

    const tick = () => {
      sx += (tx - sx) * SMOOTH;
      sy += (ty - sy) * SMOOTH;
      publish();
      if (Math.abs(tx - sx) < EPS && Math.abs(ty - sy) < EPS) {
        // settled — snap exactly and park the loop until the next input
        sx = tx;
        sy = ty;
        publish();
        running = false;
        raf = 0;
        return;
      }
      raf = requestAnimationFrame(tick);
    };

    const start = () => {
      if (!running) {
        running = true;
        raf = requestAnimationFrame(tick);
      }
    };

    const onMove = (e: PointerEvent) => {
      tx = e.clientX;
      ty = e.clientY;
      if (pointerActive.get() !== 1) pointerActive.set(1);
      start();
    };
    const onLeave = () => pointerActive.set(0);

    window.addEventListener("pointermove", onMove, { passive: true });
    window.addEventListener("pointerleave", onLeave);
    window.addEventListener("blur", onLeave);
    return () => {
      if (raf) cancelAnimationFrame(raf);
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerleave", onLeave);
      window.removeEventListener("blur", onLeave);
    };
  }, [enabled]);
}
