/* ============================================================================
   MULTI-LLM · Nexa Backend
   ----------------------------------------------------------------------------
   Wraps the EXISTING FastAPI chat endpoint (requestChatMessage) as a first-class
   provider. It is the guaranteed always-available safety net: with no external
   API keys configured the router resolves to this provider, so default chat
   behaviour is byte-for-byte identical to before the Multi-LLM system existed.
   No backend code is changed — this only calls the same endpoint the ChatPage
   used to call directly.
   ========================================================================== */
import { BaseProvider } from "./BaseProvider";
import { LLMError, classifyHttp, toLLMError } from "../errors";
import type { ChatResult, ProviderCallInput, ProviderConfig, ProviderMeta } from "../types";
import {
  requestChatMessage,
  type ChatHistoryItemDto,
} from "../../backendAssistantClient";
import { DEFAULT_BACKEND_URL } from "../../backendCommandClient";

export class NexaBackendProvider extends BaseProvider {
  readonly meta: ProviderMeta = {
    id: "nexa-backend",
    label: "Nexa Backend",
    description: "The built-in Nexa assistant (local FastAPI). Always available.",
    futureReady: false,
    requiresKey: false,
    configurableBaseUrl: false,
    defaultBaseUrl: DEFAULT_BACKEND_URL,
    models: [{ id: "nexa-default", label: "Nexa Router" }],
    defaultModel: "nexa-default",
    docsUrl: undefined,
  };

  async chat(input: ProviderCallInput, _config: ProviderConfig): Promise<ChatResult> {
    void _config;
    const history: ChatHistoryItemDto[] = input.history
      .filter((turn) => turn.role !== "system")
      .map((turn) => ({ role: turn.role, content: turn.content }));

    try {
      const response = await requestChatMessage(input.message, history, input.addressStyle, "auto", "chat_page", undefined, input.preferredLanguage);
      return {
        text: response.answer,
        providerId: this.meta.id,
        providerLabel: this.meta.label,
        model: this.meta.defaultModel,
        fellOver: false,
        extras: {
          intent: response.intent,
          status: response.status,
          source: response.source,
          sourceUrl: response.source_url,
          chips: response.chips,
          backendProvider: response.provider ?? response.llm_provider ?? null,
        },
      };
    } catch (err) {
      const message = err instanceof Error ? err.message : String(err);
      const match = message.match(/status (\d+)/);
      if (match) {
        const status = Number(match[1]);
        throw new LLMError(classifyHttp(status, message), `Nexa backend: ${message}`, status);
      }
      // Network failure → the backend is not running.
      throw toLLMError(err);
    }
  }

  async testConnection(_config: ProviderConfig): Promise<void> {
    void _config;
    try {
      // Any response (even a 404 at root) means the server is reachable.
      await fetch(DEFAULT_BACKEND_URL, { method: "GET" });
    } catch (err) {
      throw toLLMError(err);
    }
  }
}
