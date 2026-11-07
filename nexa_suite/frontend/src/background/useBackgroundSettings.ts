/* ============================================================================
   AI GLOBE BACKGROUND · useBackgroundSettings — React binding for the store.
   ========================================================================== */
import { useSyncExternalStore } from "react";
import { backgroundStore, type BackgroundSettings } from "./settings";

export interface UseBackgroundSettings {
  settings: BackgroundSettings;
  setEnabled: (enabled: boolean) => void;
  setQuality: (quality: BackgroundSettings["quality"]) => void;
}

export function useBackgroundSettings(): UseBackgroundSettings {
  useSyncExternalStore(
    (cb) => backgroundStore.subscribe(cb),
    () => backgroundStore.version,
    () => backgroundStore.version,
  );
  return {
    settings: backgroundStore.get(),
    setEnabled: (enabled) => backgroundStore.update({ enabled }),
    setQuality: (quality) => backgroundStore.update({ quality }),
  };
}
