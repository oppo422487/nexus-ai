/* ============================================================================
   MULTI-LLM · public surface
   ----------------------------------------------------------------------------
   The chat UI imports `chat` and the settings UI imports `useLLM`. Everything
   else (providers, registry, router internals) stays private to the module.
   ========================================================================== */
import { routeChat } from "./router";
import type { ChatContext, ChatResult } from "./types";

/** Unified chat entry — the ONLY call the chat UI makes. The router decides
 *  which provider executes it and fails over automatically. */
export function chat(message: string, context: ChatContext): Promise<ChatResult> {
  return routeChat(message, context);
}

export { llmManager } from "./manager";
export { useLLM } from "./useLLM";
export type { UseLLM } from "./useLLM";
export { providerRegistry } from "./registry";
export { LLMError } from "./errors";
export type {
  ProviderId,
  ModelSelection,
  ProviderStatus,
  ProviderMeta,
  ProviderConfig,
  LLMSettings,
  LLMAnalytics,
  ChatContext,
  ChatResult,
  ChatTurn,
  ChatExtras,
  LLMNotice,
} from "./types";
