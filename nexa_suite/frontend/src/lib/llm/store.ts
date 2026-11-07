/* ============================================================================
   MULTI-LLM · Persistence
   ----------------------------------------------------------------------------
   Loads/saves the Multi-LLM settings + analytics to localStorage, defensively
   merging with defaults (so new providers/fields never break an old blob).
   ========================================================================== */
import { providerRegistry } from "./registry";
import type { LLMAnalytics, LLMSettings, ProviderConfig, ProviderId } from "./types";

const SETTINGS_KEY = "nexa.llm.settings";
const ANALYTICS_KEY = "nexa.llm.analytics";
const SETTINGS_VERSION = 1;

/** External providers in their default priority order (backend excluded — it is
 *  always appended as the final safety net by the router). */
export const EXTERNAL_PRIORITY: ProviderId[] = ["openai", "gemini", "claude", "deepseek", "ollama"];

function defaultConfig(id: ProviderId): ProviderConfig {
  const meta = providerRegistry.meta(id);
  return {
    id,
    enabled: id === "nexa-backend", // backend on by default; external opt-in
    apiKey: "",
    defaultModel: meta.defaultModel,
    baseUrl: meta.defaultBaseUrl,
  };
}

export function defaultSettings(): LLMSettings {
  const providers = {} as Record<ProviderId, ProviderConfig>;
  for (const meta of providerRegistry.allMeta()) {
    providers[meta.id] = defaultConfig(meta.id);
  }
  return {
    version: SETTINGS_VERSION,
    selection: "auto",
    priority: [...EXTERNAL_PRIORITY],
    providers,
  };
}

function isProviderId(value: string): value is ProviderId {
  return providerRegistry.has(value as ProviderId);
}

export function loadSettings(): LLMSettings {
  const base = defaultSettings();
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return base;
    const parsed = JSON.parse(raw) as Partial<LLMSettings>;

    if (parsed.selection) base.selection = parsed.selection;

    if (Array.isArray(parsed.priority)) {
      const clean = parsed.priority.filter((id): id is ProviderId => typeof id === "string" && isProviderId(id) && id !== "nexa-backend");
      // keep any newly-added providers that weren't in the stored list
      const merged = [...clean, ...EXTERNAL_PRIORITY.filter((id) => !clean.includes(id))];
      base.priority = merged;
    }

    if (parsed.providers) {
      for (const meta of providerRegistry.allMeta()) {
        const stored = parsed.providers[meta.id];
        if (stored) {
          base.providers[meta.id] = {
            ...base.providers[meta.id],
            ...stored,
            id: meta.id, // never trust a stored id
          };
        }
      }
    }
  } catch {
    return defaultSettings();
  }
  return base;
}

export function saveSettings(settings: LLMSettings): void {
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  } catch {
    // persistence is best-effort
  }
}

function today(): string {
  return new Date().toISOString().slice(0, 10);
}

export function defaultAnalytics(): LLMAnalytics {
  return { date: today(), requestsToday: 0, fallbackCount: 0, currentProvider: null, lastError: null };
}

export function loadAnalytics(): LLMAnalytics {
  try {
    const raw = localStorage.getItem(ANALYTICS_KEY);
    if (!raw) return defaultAnalytics();
    const parsed = JSON.parse(raw) as LLMAnalytics;
    // Roll counters over at midnight.
    if (parsed.date !== today()) {
      return { ...defaultAnalytics(), currentProvider: parsed.currentProvider ?? null };
    }
    return { ...defaultAnalytics(), ...parsed };
  } catch {
    return defaultAnalytics();
  }
}

export function saveAnalytics(analytics: LLMAnalytics): void {
  try {
    localStorage.setItem(ANALYTICS_KEY, JSON.stringify(analytics));
  } catch {
    // best-effort
  }
}
