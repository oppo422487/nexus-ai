/* ============================================================================
   INTERACTION ENGINE — public surface
   ----------------------------------------------------------------------------
   The app root mounts <InteractionProvider>; everything else (primitives,
   hooks, the event bus) is importable for opt-in use by pages and, in a later
   phase, backend event adapters.
   ========================================================================== */

// Provider + context
export { InteractionProvider } from "./InteractionProvider";
export { useInteraction } from "./context";
export type { InteractionContextValue, InteractionQuality } from "./context";

// Event bus (architecture core for future backend-driven animations)
export { interactionBus, InteractionBus } from "./events";
export type {
  InteractionEvent,
  InteractionEventType,
  InteractionListener,
  NotificationInput,
  NotificationTone,
  VoiceState,
  CommandStatus,
} from "./events";

// Reusable primitives
export { VoiceOrb } from "./components/VoiceOrb";
export type { VoiceOrbProps } from "./components/VoiceOrb";
export { ThinkingIndicator } from "./components/ThinkingIndicator";
export { EnergyBorder } from "./components/EnergyBorder";
export { EnergyLines } from "./components/EnergyLines";
export { PremiumButton } from "./components/PremiumButton";
export type { PremiumButtonProps } from "./components/PremiumButton";
export { LiquidGlass } from "./components/LiquidGlass";
export { LiveWidget } from "./components/LiveWidget";

// Hooks
export { useMagnetic } from "./hooks/useMagnetic";
export { useMicLevel } from "./hooks/useMicLevel";
export { useInteractionQuality } from "./hooks/useInteractionQuality";
