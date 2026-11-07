/* ============================================================================
   MULTI-LLM · Google Gemini
   generativelanguage.googleapis.com — :generateContent REST transport.
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

interface GeminiResponse {
  candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }>;
  error?: { message?: string; status?: string };
}

const TIMEOUT_MS = 45_000;

export class GeminiProvider extends BaseProvider {
  readonly meta: ProviderMeta = {
    id: "gemini",
    label: "Google Gemini",
    description: "Gemini 1.5 Pro / Flash via the Generative Language API.",
    futureReady: false,
    requiresKey: true,
    configurableBaseUrl: false,
    defaultBaseUrl: "https://generativelanguage.googleapis.com/v1beta",
    models: [
      { id: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
      { id: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
      { id: "gemini-2.0-flash", label: "Gemini 2.0 Flash" },
    ],
    defaultModel: "gemini-1.5-flash",
    docsUrl: "https://aistudio.google.com/app/apikey",
  };

  async chat(input: ProviderCallInput, config: ProviderConfig): Promise<ChatResult> {
    const base = (config.baseUrl?.trim() || this.meta.defaultBaseUrl || "").replace(/\/+$/, "");
    const url = `${base}/models/${input.model}:generateContent?key=${encodeURIComponent(config.apiKey)}`;

    // Gemini uses "user"/"model" roles and a contents[] array.
    const contents = [
      ...input.history.map((turn) => ({
        role: turn.role === "assistant" ? "model" : "user",
        parts: [{ text: turn.content }],
      })),
      { role: "user", parts: [{ text: input.message }] },
    ];
    const systemInstruction = input.addressStyle
      ? { parts: [{ text: `You are Nexa, a desktop AI assistant. Address the user as "${input.addressStyle}". Reply in the user's language.` }] }
      : undefined;

    let response: Response;
    try {
      response = await fetchWithTimeout(
        url,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(systemInstruction ? { contents, systemInstruction } : { contents }),
        },
        TIMEOUT_MS,
        input.signal,
      );
    } catch (err) {
      throw toLLMError(err);
    }

    if (!response.ok) {
      const body = await safeBodyText(response);
      throw new LLMError(classifyHttp(response.status, body), `Gemini: ${body || response.statusText}`, response.status);
    }

    const data = (await response.json()) as GeminiResponse;
    const text = data.candidates?.[0]?.content?.parts?.map((p) => p.text ?? "").join("").trim();
    if (!text) {
      throw new LLMError("unavailable", "Gemini returned an empty response");
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
