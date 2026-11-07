/* ============================================================================
   MULTI-LLM · ProviderRegistry
   ----------------------------------------------------------------------------
   The single place that knows which concrete providers exist. Everything else
   resolves providers by id through here, so provider logic is never hardcoded
   into the router, manager, or UI. Adding a provider = one import + one entry.
   ========================================================================== */
import type { BaseProvider } from "./providers/BaseProvider";
import type { ProviderId, ProviderMeta } from "./types";
import { NexaBackendProvider } from "./providers/NexaBackendProvider";
import { OpenAIProvider } from "./providers/OpenAIProvider";
import { GeminiProvider } from "./providers/GeminiProvider";
import { ClaudeProvider } from "./providers/ClaudeProvider";
import { DeepSeekProvider } from "./providers/DeepSeekProvider";
import { OllamaProvider } from "./providers/OllamaProvider";

class ProviderRegistry {
  private readonly providers: Map<ProviderId, BaseProvider>;
  /** Declaration order = default failover priority for external providers. */
  readonly order: ProviderId[];

  constructor(instances: BaseProvider[]) {
    this.providers = new Map(instances.map((p) => [p.meta.id, p]));
    this.order = instances.map((p) => p.meta.id);
  }

  get(id: ProviderId): BaseProvider | undefined {
    return this.providers.get(id);
  }

  require(id: ProviderId): BaseProvider {
    const provider = this.providers.get(id);
    if (!provider) throw new Error(`Unknown LLM provider: ${id}`);
    return provider;
  }

  all(): BaseProvider[] {
    return [...this.providers.values()];
  }

  meta(id: ProviderId): ProviderMeta {
    return this.require(id).meta;
  }

  allMeta(): ProviderMeta[] {
    return this.all().map((p) => p.meta);
  }

  has(id: ProviderId): boolean {
    return this.providers.has(id);
  }
}

/** The app-wide registry. `nexa-backend` is registered first so it is the
 *  default final safety net; external providers follow in priority order. */
export const providerRegistry = new ProviderRegistry([
  new NexaBackendProvider(),
  new OpenAIProvider(),
  new GeminiProvider(),
  new ClaudeProvider(),
  new DeepSeekProvider(),
  new OllamaProvider(),
]);

export type { ProviderRegistry };
