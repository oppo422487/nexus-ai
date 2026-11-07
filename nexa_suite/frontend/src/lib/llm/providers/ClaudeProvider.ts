/* ============================================================================
   MULTI-LLM · Anthropic Claude  (future-ready)
   api.anthropic.com/v1/messages. Works when a key is set; flagged future-ready
   because direct browser calls may require the anthropic-dangerous-direct
   header and can be CORS-restricted depending on the runtime.
   ========================================================================== */
import { BaseProvider } from "./BaseProvider";
import {
  LLMError,
  classifyHttp,
  fetchWithTimeout,
  safeBodyText,
  toLLMError,
} from "../errors";
import type { ChatResult, ProviderCallInput, ProviderConfig, ProviderMeta } from "../types";

interface ClaudeResponse {
  content?: Array<{ text?: string }>;
  error?: { message?: string; type?: string };
}

const TIMEOUT_MS = 45_000;

export class ClaudeProvider extends BaseProvider {
  readonly meta: ProviderMeta = {
    id: "claude",
    label: "Claude",
    description: "Anthropic Claude (Messages API). Future-ready.",
    futureReady: true,
    requiresKey: true,
    configurableBaseUrl: true,
    defaultBaseUrl: "https://api.anthropic.com/v1",
    models: [
      { id: "claude-sonnet-4-20250514", label: "Claude Sonnet 4" },
      { id: "claude-3-5-haiku-20241022", label: "Claude 3.5 Haiku" },
    ],
    defaultModel: "claude-sonnet-4-20250514",
    docsUrl: "https://console.anthropic.com/settings/keys",
  };

  async chat(input: ProviderCallInput, config: ProviderConfig): Promise<ChatResult> {
    const base = (config.baseUrl?.trim() || this.meta.defaultBaseUrl || "").replace(/\/+$/, "");
    const url = `${base}/messages`;
    const messages = [
      ...input.history.map((turn) => ({
        role: turn.role === "assistant" ? "assistant" : "user",
        content: turn.content,
      })),
      { role: "user", content: input.message },
    ];

    let response: Response;
    try {
      response = await fetchWithTimeout(
        url,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "x-api-key": config.apiKey,
            "anthropic-version": "2023-06-01",
            "anthropic-dangerous-direct-browser-access": "true",
          },
          body: JSON.stringify({
            model: input.model,
            max_tokens: 1024,
            system: input.addressStyle
              ? `You are Nexa, a desktop AI assistant. Address the user as "${input.addressStyle}". Reply in the user's language.`
              : undefined,
            messages,
          }),
        },
        TIMEOUT_MS,
        input.signal,
      );
    } catch (err) {
      throw toLLMError(err);
    }

    if (!response.ok) {
      const body = await safeBodyText(response);
      throw new LLMError(classifyHttp(response.status, body), `Claude: ${body || response.statusText}`, response.status);
    }

    const data = (await response.json()) as ClaudeResponse;
    const text = data.content?.map((part) => part.text ?? "").join("").trim();
    if (!text) {
      throw new LLMError("unavailable", "Claude returned an empty response");
    }
    return {
      text,
      providerId: this.meta.id,
      providerLabel: this.meta.label,
      model: input.model,
      fellOver: false,
    };
  }

  async testConnection(config: ProviderConfig): Promise<void> {
    await this.chat(
      { message: "ping", history: [], model: config.defaultModel || this.meta.defaultModel },
      config,
    );
  }
}
