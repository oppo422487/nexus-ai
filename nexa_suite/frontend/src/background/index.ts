/* ============================================================================
   AI GLOBE BACKGROUND · public surface
   ----------------------------------------------------------------------------
   Intentionally does NOT re-export globeEngine — that module stays behind a
   dynamic import so three/globe never enter the main bundle.
   ========================================================================== */
export { AIGlobeBackground } from "./AIGlobeBackground";
export { useBackgroundSettings } from "./useBackgroundSettings";
export { backgroundStore, DEFAULT_BACKGROUND_SETTINGS } from "./settings";
export type { BackgroundSettings } from "./settings";
export type { QualitySetting, QualityTier } from "./quality";
