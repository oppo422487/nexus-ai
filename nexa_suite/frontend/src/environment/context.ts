/* ============================================================================
   ENVIRONMENT · context
   Shares the active quality preset + reduced-motion flag with scene components.
   The provider lives INSIDE the R3F <Canvas> so children in the WebGL tree can
   consume it (R3F does not auto-bridge outer-tree context).
   ========================================================================== */

import { createContext, useContext } from "react";
import { QUALITY_PRESETS, type QualityPreset } from "./config";

export interface EnvironmentContextValue {
  preset: QualityPreset;
  reducedMotion: boolean;
}

export const EnvironmentContext = createContext<EnvironmentContextValue>({
  preset: QUALITY_PRESETS.medium,
  reducedMotion: false,
});

export function useEnvironment(): EnvironmentContextValue {
  return useContext(EnvironmentContext);
}
