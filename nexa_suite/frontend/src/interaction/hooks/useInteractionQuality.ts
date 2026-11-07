/* ============================================================================
   INTERACTION · useInteractionQuality
   ----------------------------------------------------------------------------
   Derives the effect budget from user preference + device signals. Reduced
   motion disables continuous/physics effects; low-core machines drop to a
   lighter set; coarse-pointer (touch) devices skip cursor/magnetic effects.
   Independent of the WebGL environment's performance manager (DOM concerns).
   ========================================================================== */

import { useEffect, useState } from "react";
import type { InteractionQuality } from "../context";

export interface InteractionQualityState {
  quality: InteractionQuality;
  reducedMotion: boolean;
  coarsePointer: boolean;
}

function computeQuality(reduced: boolean, coarse: boolean): InteractionQuality {
  if (reduced) return "off";
  const cores = typeof navigator !== "undefined" ? navigator.hardwareConcurrency || 4 : 4;
  if (coarse || cores <= 4) return "lite";
  return "full";
}

export function useInteractionQuality(): InteractionQualityState {
  const [state, setState] = useState<InteractionQualityState>(() => ({
    quality: "full",
    reducedMotion: false,
    coarsePointer: false,
  }));

  useEffect(() => {
    const motionMq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const pointerMq = window.matchMedia("(pointer: coarse)");
    const update = () => {
      const reduced = motionMq.matches;
      const coarse = pointerMq.matches;
      setState({ reducedMotion: reduced, coarsePointer: coarse, quality: computeQuality(reduced, coarse) });
    };
    update();
    motionMq.addEventListener?.("change", update);
    pointerMq.addEventListener?.("change", update);
    return () => {
      motionMq.removeEventListener?.("change", update);
      pointerMq.removeEventListener?.("change", update);
    };
  }, []);

  return state;
}
