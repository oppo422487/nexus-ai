/* ============================================================================
   INTERACTION PROVIDER  (Phase C)
   ----------------------------------------------------------------------------
   Wraps the app once (inside DesignProvider). Bridges the event bus into React
   context, runs the single global pointer tracker, derives the adaptive effect
   budget, and mounts the global interaction layers into a body-level portal so
   they sit above the shell without affecting layout or interactivity.

   Pages inherit all of this automatically; nothing here touches backend, APIs,
   routing, or app state.
   ========================================================================== */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { InteractionContext, type InteractionContextValue } from "./context";
import { interactionBus, type InteractionEvent, type InteractionListener, type NotificationInput } from "./events";

/** Renderer-side integration seam. A future backend adapter, SSE client, or the
    Electron main/preload bridge can drive animations via `window.nexaInteraction`
    without importing anything — the counterpart to importing `interactionBus`. */
declare global {
  interface Window {
    nexaInteraction?: {
      emit: (event: InteractionEvent) => void;
      notify: (input: NotificationInput) => void;
      subscribe: (listener: InteractionListener) => () => void;
    };
  }
}
import { usePointerTracking } from "./hooks/usePointer";
import { useInteractionQuality } from "./hooks/useInteractionQuality";
import { MagneticCursor } from "./components/global/MagneticCursor";
import { PointerReflection } from "./components/global/PointerReflection";
import { NotificationCenter } from "./components/global/NotificationCenter";
import { ThinkingOverlay } from "./components/global/ThinkingOverlay";
import { CommandExecutionOverlay } from "./components/global/CommandExecutionOverlay";
import { FloatingVoiceOrb } from "./components/global/FloatingVoiceOrb";

export function InteractionProvider({ children }: { children: ReactNode }) {
  const { quality, reducedMotion, coarsePointer } = useInteractionQuality();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  // Expose the renderer-side bridge for future backend/Electron event sources.
  useEffect(() => {
    window.nexaInteraction = {
      emit: (event) => interactionBus.emit(event),
      notify: (input) => interactionBus.emit({ type: "notify", payload: input }),
      subscribe: (listener) => interactionBus.subscribe(listener),
    };
    return () => {
      delete window.nexaInteraction;
    };
  }, []);

  // A single pointer stream feeds cursor, reflection, and CSS pointer vars.
  usePointerTracking(quality !== "off" && !coarsePointer);

  const value = useMemo<InteractionContextValue>(
    () => ({
      emit: (event) => interactionBus.emit(event),
      subscribe: (listener) => interactionBus.subscribe(listener),
      notify: (input) => interactionBus.emit({ type: "notify", payload: input }),
      reducedMotion,
      quality,
      coarsePointer,
    }),
    [reducedMotion, quality, coarsePointer],
  );

  return (
    <InteractionContext.Provider value={value}>
      {children}
      {mounted &&
        createPortal(
          <div className="nxi-root" data-quality={quality}>
            <PointerReflection />
            <MagneticCursor />
            <ThinkingOverlay />
            <CommandExecutionOverlay />
            <NotificationCenter />
            <FloatingVoiceOrb />
          </div>,
          document.body,
        )}
    </InteractionContext.Provider>
  );
}
