/* ============================================================================
   INTERACTION · CONTEXT
   React access to the interaction bus + runtime motion/quality flags. A no-op
   default keeps reusable primitives safe to render outside the provider.
   ========================================================================== */

import { createContext, useContext } from "react";
import { interactionBus, type InteractionEvent, type InteractionListener, type NotificationInput } from "./events";

export type InteractionQuality = "full" | "lite" | "off";

export interface InteractionContextValue {
  emit: (event: InteractionEvent) => void;
  subscribe: (listener: InteractionListener) => () => void;
  /** Convenience wrapper around emit("notify"). */
  notify: (input: NotificationInput) => void;
  /** True when the user prefers reduced motion. */
  reducedMotion: boolean;
  /** Adaptive effect budget: full = all effects, lite = essentials, off = none. */
  quality: InteractionQuality;
  /** True on coarse-pointer (touch) devices where cursor effects are disabled. */
  coarsePointer: boolean;
}

export const InteractionContext = createContext<InteractionContextValue>({
  emit: (event) => interactionBus.emit(event),
  subscribe: (listener) => interactionBus.subscribe(listener),
  notify: (input) => interactionBus.emit({ type: "notify", payload: input }),
  reducedMotion: false,
  quality: "full",
  coarsePointer: false,
});

export function useInteraction(): InteractionContextValue {
  return useContext(InteractionContext);
}
