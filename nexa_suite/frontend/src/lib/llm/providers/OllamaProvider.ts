/* ============================================================================
   MULTI-LLM · Ollama  (future-ready, local)
   Local models via http://localhost:11434/api/chat. No API key required.
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

interface OllamaResponse {
  message?: { content?: string };
  error?: string;
}

const TIMEOUT_MS = 60_000; // local models can be slow to first token

export class OllamaProvider extends BaseProvider {
  readonly meta: ProviderMeta = {
    id: "ollama",
    label: "Ollama",
    description: "Local models (Llama, Mistral, Qwen…) via Ollama. Future-ready.",
    futureReady: true,
    requiresKey: false,
    configurableBaseUrl: true,
    defaultBaseUrl: "http://localhost:11434",
    models: [
      { id: "llama3.1", label: "Llama 3.1" },
      { id: "qwen2.5", label: "Qwen 2.5" },
      { id: "mistral", label: "Mistral" },
    ],
    defaultModel: "llama3.1",
    docsUrl: "https://ollama.com/library",
  };

  private endpoint(config: ProviderConfig): string {
    return (config.baseUrl?.trim() || this.meta.defaultBaseUrl || "").replace(/\/+$/, "");
  }

  async chat(input: ProviderCallInput, config: ProviderConfig): Promise<ChatResult> {
    const url = `${this.endpoint(config)}/api/chat`;
    const messages = [
      ...(input.addressStyle
        ? [{ role: "system", content: `You are Nexa, a desktop AI assistant. Address the user as "${input.addressStyle}".` }]
        : []),
      ...input.history,
      { role: "user", content: input.message },
    ];

    let response: Response;
    try {
      response = await fetchWithTimeout(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
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
      throw new LLMError(classifyHttp(response.status, body), `Ollama: ${body || response.statusText}`, response.status);
    }

    const data = (await response.json()) as OllamaResponse;
    const text = data.message?.content?.trim();
    if (!text) {
      throw new LLMError("unavailable", "Ollama returned an empty response (is the model pulled?)");
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
    // A tags call is the cheapest reachability probe for a local daemon.
    let response: Response;
    try {
      response = await fetchWithTimeout(`${this.endpoint(config)}/api/tags`, { method: "GET" }, 8_000);
    } catch (err) {
      throw toLLMError(err);
    }
    if (!response.ok) {
      const body = await safeBodyText(response);
      throw new LLMError(classifyHttp(response.status, body), `Ollama: ${body || response.statusText}`, response.status);
    }
  }
}
