/* ============================================================================
   ENVIRONMENT · AI ACTIVITY  (OMEGA-2 — cinematic modes)
   ----------------------------------------------------------------------------
   The OS's nervous system. A multi-channel model — thinking / command / voice —
   each a smoothed 0..1 weight, plus a decaying command burst. Bus events set the
   TARGETS; the single ActivityDriver eases the channels toward them every frame
   (one clock, one timing source), so modes crossfade smoothly (thinking→command,
   voice→thinking, …) with no pops. Scene + DOM read the channels and react
   DIFFERENTLY per mode. Event-driven, no polling, no duplicated React state
   (a plain module ref avoids re-renders).
   ========================================================================== */

import { interactionBus } from "@/interaction";

export type AiMode = "idle" | "thinking" | "command" | "voice";

export interface AiChannels {
  thinking: number;
  command: number;
  voice: number;
}

export const aiActivity = {
  /** Where each channel is heading (set by bus events). */
  target: { thinking: 0, command: 0, voice: 0 } as AiChannels,
  /** Smoothed current channel weights (eased each frame by the driver). */
  channel: { thinking: 0, command: 0, voice: 0 } as AiChannels,
  /** Short-lived spike on command execution — the "flash". */
  commandBurst: 0,
  /** Overall intensity (max channel + burst) — OMEGA-1 compatible. */
  value: 0,
  /** Derived coarse mode. */
  mode: "idle" as AiMode,
};

let unsubscribe: (() => void) | null = null;

/** Wire the bus → per-channel targets. Idempotent; returns a teardown. */
export function initAiActivity(): () => void {
  if (unsubscribe) return unsubscribe;

  const off = interactionBus.subscribe((event) => {
    switch (event.type) {
      case "ai:thinking":
        aiActivity.target.thinking = event.payload.active ? 1 : 0;
        break;
      case "command:execute":
        if (event.payload.status === "start") {
          aiActivity.target.command = 1;
          aiActivity.commandBurst = 1;
        } else {
          // success / error — a confirmation ripple, then settle
          aiActivity.target.command = 0;
          aiActivity.commandBurst = 1;
        }
        break;
      case "voice":
        if (event.payload.state === "listening") aiActivity.target.voice = 0.55;
        else if (event.payload.state === "processing") aiActivity.target.voice = 1;
        else if (event.payload.state === "idle") aiActivity.target.voice = 0;
        break;
      default:
        break;
    }
  });

  unsubscribe = () => {
    off();
    unsubscribe = null;
  };
  return unsubscribe;
}

/* Channel reads for scene components (smoothed). */
export const thinkingLevel = (): number => aiActivity.channel.thinking;
export const commandLevel = (): number => aiActivity.channel.command;
export const commandBurst = (): number => aiActivity.commandBurst;
export const voiceLevel = (): number => aiActivity.channel.voice;
/** Overall intensity — kept for OMEGA-1 consumers. */
export const activityLevel = (): number => aiActivity.value;
