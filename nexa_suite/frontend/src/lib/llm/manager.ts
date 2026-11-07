/* ============================================================================
   MULTI-LLM · ProviderManager
   ----------------------------------------------------------------------------
   The single source of truth for provider configuration, live status, and
   analytics. Owns persistence and a tiny subscription so React views re-render
   on change. The router reads/writes analytics + status through here.
   ========================================================================== */
import { providerRegistry } from "./registry";
import {
  loadSettings,
  saveSettings,
  loadAnalytics,
  saveAnalytics,
  defaultSettings,
} from "./store";
import { LLMError, reasonLabel } from "./errors";
import type {
  LLMAnalytics,
  LLMSettings,
  ModelSelection,
  ProviderConfig,
  ProviderId,
  ProviderMeta,
  ProviderStatus,
} from "./types";

type Listener = () => void;

class ProviderManager {
  private settings: LLMSettings = loadSettings();
  private analytics: LLMAnalytics = loadAnalytics();
  private status = new Map<ProviderId, ProviderStatus>();
  private listeners = new Set<Listener>();
  private _version = 0;

  /** Monotonic change counter — a stable snapshot for useSyncExternalStore. */
  get version(): number {
    return this._version;
  }

  constructor() {
    for (const meta of providerRegistry.allMeta()) {
      this.status.set(meta.id, this.derivedStatus(meta.id));
    }
  }

  /* ---------------- subscription ---------------- */

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private emit(): void {
    this._version += 1;
    for (const listener of this.listeners) listener();
  }

  private commitSettings(): void {
    saveSettings(this.settings);
    this.emit();
  }

  private commitAnalytics(): void {
    saveAnalytics(this.analytics);
    this.emit();
  }

  /* ---------------- reads ---------------- */

  getSettings(): LLMSettings {
    return this.settings;
  }

  getAnalytics(): LLMAnalytics {
    return this.analytics;
  }

  allMeta(): ProviderMeta[] {
    return providerRegistry.allMeta();
  }

  meta(id: ProviderId): ProviderMeta {
    return providerRegistry.meta(id);
  }

  config(id: ProviderId): ProviderConfig {
    return this.settings.providers[id];
  }

  getStatus(id: ProviderId): ProviderStatus {
    return this.status.get(id) ?? this.derivedStatus(id);
  }

  private derivedStatus(id: ProviderId): ProviderStatus {
    const config = this.settings.providers[id];
    const meta = providerRegistry.meta(id);
    if (meta.requiresKey && !config.apiKey.trim()) return "unconfigured";
    return "ready";
  }

  /* ---------------- config mutations ---------------- */

  setSelection(selection: ModelSelection): void {
    this.settings = { ...this.settings, selection };
    this.commitSettings();
  }

  setProviderEnabled(id: ProviderId, enabled: boolean): void {
    this.patchProvider(id, { enabled });
  }

  setApiKey(id: ProviderId, apiKey: string): void {
    this.patchProvider(id, { apiKey });
    this.status.set(id, this.derivedStatus(id));
  }

  setDefaultModel(id: ProviderId, defaultModel: string): void {
    this.patchProvider(id, { defaultModel });
  }

  setBaseUrl(id: ProviderId, baseUrl: string): void {
    this.patchProvider(id, { baseUrl });
  }

  private patchProvider(id: ProviderId, patch: Partial<ProviderConfig>): void {
    this.settings = {
      ...this.settings,
      providers: {
        ...this.settings.providers,
        [id]: { ...this.settings.providers[id], ...patch, id },
      },
    };
    this.commitSettings();
  }

  /** Reorder the external failover priority (drag-and-drop). */
  setPriority(priority: ProviderId[]): void {
    const clean = priority.filter((id) => id !== "nexa-backend" && providerRegistry.has(id));
    this.settings = { ...this.settings, priority: clean };
    this.commitSettings();
  }

  reset(): void {
    this.settings = defaultSettings();
    this.commitSettings();
  }

  /* ---------------- runtime status + analytics (called by router) ------- */

  setStatus(id: ProviderId, status: ProviderStatus): void {
    if (this.status.get(id) !== status) {
      this.status.set(id, status);
      this.emit();
    }
  }

  markSuccess(id: ProviderId): void {
    this.rolloverIfNeeded();
    this.status.set(id, "ready");
    this.analytics = {
      ...this.analytics,
      currentProvider: id,
      requestsToday: this.analytics.requestsToday + 1,
    };
    this.commitAnalytics();
  }

  markFailure(id: ProviderId, error: LLMError): void {
    this.rolloverIfNeeded();
    this.status.set(id, error.kind === "rate-limit" || error.kind === "quota" ? "rate-limited" : "disconnected");
    this.analytics = {
      ...this.analytics,
      lastError: `${providerRegistry.meta(id).label}: ${reasonLabel(error.kind)}`,
    };
    this.commitAnalytics();
  }

  markFallback(): void {
    this.rolloverIfNeeded();
    this.analytics = { ...this.analytics, fallbackCount: this.analytics.fallbackCount + 1 };
    this.commitAnalytics();
  }

  private rolloverIfNeeded(): void {
    const today = new Date().toISOString().slice(0, 10);
    if (this.analytics.date !== today) {
      this.analytics = {
        date: today,
        requestsToday: 0,
        fallbackCount: 0,
        currentProvider: this.analytics.currentProvider,
        lastError: null,
      };
    }
  }

  /* ---------------- connection test ---------------- */

  async testConnection(id: ProviderId): Promise<{ ok: boolean; error?: string }> {
    const provider = providerRegistry.require(id);
    const config = this.config(id);
    if (provider.meta.requiresKey && !config.apiKey.trim()) {
      this.setStatus(id, "unconfigured");
      return { ok: false, error: "API key required" };
    }
    try {
      await provider.testConnection(config);
      this.setStatus(id, "ready");
      return { ok: true };
    } catch (err) {
      const error = err instanceof LLMError ? err : new LLMError("unknown", err instanceof Error ? err.message : String(err));
      this.markFailure(id, error);
      return { ok: false, error: error.message };
    }
  }
}

/** App-wide singleton. */
export const llmManager = new ProviderManager();
export type { ProviderManager };
