/* ============================================================================
   INTERACTION · EVENT BUS  (Phase C — architecture core)
   ----------------------------------------------------------------------------
   A tiny, strongly-typed pub/sub. The whole interaction layer is event-driven:
   UI or (in a later phase) backend adapters emit semantic events, and the
   global interaction layers translate them into motion. This is the seam that
   makes future backend-triggered animations trivial to connect — an adapter
   calls `interactionBus.emit(...)`, no component wiring required.

   Nothing here touches the backend, APIs, routing, or app state.
   ========================================================================== */

export type NotificationTone = "info" | "success" | "warning" | "error";

export interface NotificationInput {
  title: string;
  message?: string;
  tone?: NotificationTone;
  /** Auto-dismiss after N ms; 0 keeps it until dismissed. */
  durationMs?: number;
}

export type VoiceState = "idle" | "listening" | "processing";
export type CommandStatus = "start" | "success" | "error";

/** The full set of interaction events. Extend this union to add new signals. */
export type InteractionEvent =
  | { type: "notify"; payload: NotificationInput }
  | { type: "ai:thinking"; payload: { active: boolean; label?: string } }
  | { type: "command:execute"; payload: { id?: string; label: string; status: CommandStatus } }
  | { type: "voice"; payload: { state?: VoiceState; level?: number } };

export type InteractionEventType = InteractionEvent["type"];
export type InteractionListener = (event: InteractionEvent) => void;

export class InteractionBus {
  private listeners = new Set<InteractionListener>();

  subscribe(listener: InteractionListener): () => void {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  }

  emit(event: InteractionEvent): void {
    // Copy to a list first so a listener that unsubscribes mid-dispatch is safe.
    for (const listener of Array.from(this.listeners)) {
      try {
        listener(event);
      } catch {
        /* one bad listener must never break the rest of the pipeline */
      }
    }
  }

  clear(): void {
    this.listeners.clear();
  }
}

/** App-wide singleton. Non-React emitters (future backend adapters) import this
    directly; the InteractionProvider bridges it into React context. */
export const interactionBus = new InteractionBus();
