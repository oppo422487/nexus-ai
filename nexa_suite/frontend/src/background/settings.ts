/* ============================================================================
   AI GLOBE BACKGROUND · Settings
   ----------------------------------------------------------------------------
   Persisted enable + quality with a tiny observable store (useSyncExternalStore
   friendly). Deliberately light — it does NOT import the engine or three/globe,
   so reading settings never pulls in the heavy WebGL bundle.
   ========================================================================== */
import type { QualitySetting } from "./quality";

export interface BackgroundSettings {
  enabled: boolean;
  quality: QualitySetting;
}

const KEY = "nexa.background";

export const DEFAULT_BACKGROUND_SETTINGS: BackgroundSettings = {
  enabled: true, // premium experience on by default; one toggle to the fast UI
  quality: "auto",
};

type Listener = () => void;

class BackgroundStore {
  private settings: BackgroundSettings = this.load();
  private listeners = new Set<Listener>();
  private _version = 0;

  get version(): number {
    return this._version;
  }

  private load(): BackgroundSettings {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return { ...DEFAULT_BACKGROUND_SETTINGS };
      return { ...DEFAULT_BACKGROUND_SETTINGS, ...(JSON.parse(raw) as Partial<BackgroundSettings>) };
    } catch {
      return { ...DEFAULT_BACKGROUND_SETTINGS };
    }
  }

  get(): BackgroundSettings {
    return this.settings;
  }

  update(patch: Partial<BackgroundSettings>): void {
    this.settings = { ...this.settings, ...patch };
    try {
      localStorage.setItem(KEY, JSON.stringify(this.settings));
    } catch {
      /* best-effort */
    }
    this._version += 1;
    for (const l of this.listeners) l();
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }
}

export const backgroundStore = new BackgroundStore();
