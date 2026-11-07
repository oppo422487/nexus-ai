/* ============================================================================
   MULTI-LLM · OpenAI-compatible base
   ----------------------------------------------------------------------------
   OpenAI and DeepSeek (and most local gateways) share the /chat/completions
   contract, so the transport lives here once. Concrete providers only supply
   their `meta` + default base URL — zero duplicated request logic.
   ========================================================================== */
import { BaseProvider } from "./BaseProvider";
import {
  LLMError,
  classifyHttp,
  fetchWithTimeout,
  safeBodyText,
  toLLMError,
} from "../errors";
import type { ChatResult, ProviderCallInput, ProviderConfig, ChatTurn } from "../types";

interface OpenAIChatResponse {
  choices?: Array<{ message?: { content?: string } }>;
  error?: { message?: string; type?: string; code?: string };
}

const TIMEOUT_MS = 45_000;

function systemPreamble(addressStyle?: string): ChatTurn[] {
  if (!addressStyle) return [];
  return [
    {
      role: "system",
      content: `You are Nexa, a helpful desktop AI assistant. Address the user as "${addressStyle}" when natural. Answer in the user's language (Bangla, Banglish, or English).`,
    },
  ];
}

export abstract class OpenAICompatibleProvider extends BaseProvider {
  protected baseUrl(config: ProviderConfig): string {
    return (config.baseUrl?.trim() || this.meta.defaultBaseUrl || "").replace(/\/+$/, "");
  }

  async chat(input: ProviderCallInput, config: ProviderConfig): Promise<ChatResult> {
    const url = `${this.baseUrl(config)}/chat/completions`;
    const messages: ChatTurn[] = [
      ...systemPreamble(input.addressStyle),
      ...input.history,
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
            Authorization: `Bearer ${config.apiKey}`,
          },
          body: JSON.stringify({ model: input.model, messages, stream: false }),
        },
        TIMEOUT_MS,
        input.signal,
      );
    } catch (err) {
      throw toLLMError(err);
    }

    if (!response.ok) {
      const body = await safeBodyText(response);
      throw new LLMError(classifyHttp(response.status, body), `${this.meta.label}: ${body || response.statusText}`, response.status);
    }

    const data = (await response.json()) as OpenAIChatResponse;
    const text = data.choices?.[0]?.message?.content?.trim();
    if (!text) {
      throw new LLMError("unavailable", `${this.meta.label} returned an empty response`);
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
