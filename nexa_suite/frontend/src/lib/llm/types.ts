/* ============================================================================
   MULTI-LLM · TYPES
   ----------------------------------------------------------------------------
   Shared, provider-agnostic contracts for the Multi-LLM system. Nothing here
   imports a concrete provider — the router, manager, registry and UI all speak
   in these types so provider logic is never hardcoded anywhere.
   ========================================================================== */

/** Every provider Nexa knows about. `nexa-backend` wraps the existing FastAPI
 *  chat endpoint and is the guaranteed always-available safety net. */
export type ProviderId =
  | "nexa-backend"
  | "openai"
  | "gemini"
  | "claude"
  | "deepseek"
  | "ollama";

/** The user-facing model choices in Settings → AI Models. */
export type ModelSelection =
  | "auto"
  | "gpt"
  | "gemini-pro"
  | "gemini-flash"
  | "claude"
  | "deepseek"
  | "ollama";

/** Live connection state for a provider, shown as 🟢 / 🟡 / 🔴 / ⚪. */
export type ProviderStatus = "ready" | "rate-limited" | "disconnected" | "unconfigured";

/** A single conversation turn — identical shape across every provider. */
export interface ChatTurn {
  role: "user" | "assistant" | "system";
  content: string;
}

/** One selectable model within a provider. */
export interface ModelOption {
  id: string;
  label: string;
}

/** Static description of a provider (no user state). */
export interface ProviderMeta {
  id: ProviderId;
  label: string;
  description: string;
  /** Future-ready providers are shown but flagged as not fully verified. */
  futureReady: boolean;
  /** Whether an API key is required to use the provider. */
  requiresKey: boolean;
  /** Whether an endpoint/base URL is user-configurable. */
  configurableBaseUrl: boolean;
  defaultBaseUrl?: string;
  models: ModelOption[];
  defaultModel: string;
  docsUrl?: string;
}

/** Per-provider, user-owned configuration (persisted locally). */
export interface ProviderConfig {
  id: ProviderId;
  enabled: boolean;
  apiKey: string;
  defaultModel: string;
  baseUrl?: string;
}

/** The full persisted Multi-LLM settings blob. */
export interface LLMSettings {
  version: number;
  selection: ModelSelection;
  /** Failover order (highest priority first). */
  priority: ProviderId[];
  providers: Record<ProviderId, ProviderConfig>;
}

/** Rolling analytics surfaced in the UI. */
export interface LLMAnalytics {
  /** ISO date (YYYY-MM-DD) the counters belong to — used for daily rollover. */
  date: string;
  requestsToday: number;
  fallbackCount: number;
  currentProvider: ProviderId | null;
  lastError: string | null;
}

/** A notice the router asks the UI to surface (e.g. a failover toast). */
export interface LLMNotice {
  title: string;
  message?: string;
  tone: "info" | "success" | "warning" | "error";
}

/** Everything the chat UI passes alongside the message. Conversation identity,
 *  history, and the notice sink all live here so provider switching never
 *  loses context. */
export interface ChatContext {
  history: ChatTurn[];
  conversationId: string;
  addressStyle?: string;
  preferredLanguage?: "Bangla" | "English" | "Mixed";
  /** Optional model override; defaults to the user's saved selection. */
  selection?: ModelSelection;
  signal?: AbortSignal;
  /** The router calls this on failover so the UI can show a toast. */
  onNotice?: (notice: LLMNotice) => void;
}

/** Passthrough metadata from a provider (backend chat carries rich extras). */
export interface ChatExtras {
  intent?: string;
  status?: string;
  source?: string | null;
  sourceUrl?: string | null;
  chips?: string[];
  backendProvider?: string | null;
}

/** The unified result every provider returns. */
export interface ChatResult {
  text: string;
  providerId: ProviderId;
  providerLabel: string;
  model: string;
  /** True when the answering provider was NOT the first one attempted. */
  fellOver: boolean;
  extras?: ChatExtras;
}

/** What a provider adapter needs at call time. */
export interface ProviderCallInput {
  message: string;
  history: ChatTurn[];
  addressStyle?: string;
  preferredLanguage?: "Bangla" | "English" | "Mixed";
  /** Model to use for this call (overrides the config default). */
  model: string;
  signal?: AbortSignal;
}
