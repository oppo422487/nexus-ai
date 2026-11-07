/* ============================================================================
   OMEGA FX  — passive click-ripple effect
   ----------------------------------------------------------------------------
   Listens (capture phase, non-blocking) for pointer-downs anywhere and spawns a
   short-lived ripple element at the cursor. It never calls preventDefault or
   stopPropagation, the ripple nodes are pointer-events:none and self-remove, so
   this cannot affect any click target or app logic. Honours reduced motion and
   cleans up its listener on unmount.
   ========================================================================== */
import { useEffect } from "react";

export function OmegaFX() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (media.matches) return;

    const onPointerDown = (e: PointerEvent) => {
      // Only primary (left/touch) presses; skip synthetic events without coords.
      if (e.button !== 0) return;
      const ripple = document.createElement("span");
      ripple.className = "nx-omega-ripple";
      ripple.style.left = `${e.clientX}px`;
      ripple.style.top = `${e.clientY}px`;
      document.body.appendChild(ripple);
      const remove = () => ripple.remove();
      ripple.addEventListener("animationend", remove, { once: true });
      // Safety net in case animationend never fires (e.g. tab hidden).
      window.setTimeout(remove, 900);
    };

    window.addEventListener("pointerdown", onPointerDown, { capture: true, passive: true });
    return () => window.removeEventListener("pointerdown", onPointerDown, { capture: true } as EventListenerOptions);
  }, []);

  return null;
}

export default OmegaFX;
