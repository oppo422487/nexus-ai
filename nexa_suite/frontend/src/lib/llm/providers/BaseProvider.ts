/* ============================================================================
   MULTI-LLM · BaseProvider
   ----------------------------------------------------------------------------
   The interface every provider implements. The router and manager depend only
   on this abstraction — adding a provider is a new subclass + one registry line.
   ========================================================================== */
import type {
  ProviderCallInput,
  ProviderConfig,
  ProviderMeta,
  ChatResult,
} from "../types";

export abstract class BaseProvider {
  /** Static description (id, label, models, key requirements). */
  abstract readonly meta: ProviderMeta;

  /** Execute one chat turn. Must throw an LLMError on any failure so the router
   *  can classify it for failover. */
  abstract chat(input: ProviderCallInput, config: ProviderConfig): Promise<ChatResult>;

  /** Lightweight reachability/auth check. Resolves on success, throws LLMError
   *  otherwise. Used by the "Test connection" button in Settings. */
  abstract testConnection(config: ProviderConfig): Promise<void>;

  /** Whether the provider has everything it needs to be attempted. */
  isConfigured(config: ProviderConfig): boolean {
    return this.meta.requiresKey ? config.apiKey.trim().length > 0 : true;
  }
}
