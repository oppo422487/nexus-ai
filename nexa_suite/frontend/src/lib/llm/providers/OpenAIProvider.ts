/* OpenAI (GPT) — /chat/completions transport inherited from the shared base. */
import { OpenAICompatibleProvider } from "./openaiCompatible";
import type { ProviderMeta } from "../types";

export class OpenAIProvider extends OpenAICompatibleProvider {
  readonly meta: ProviderMeta = {
    id: "openai",
    label: "OpenAI",
    description: "GPT-4o / GPT-4o mini via the OpenAI API.",
    futureReady: false,
    requiresKey: true,
    configurableBaseUrl: true,
    defaultBaseUrl: "https://api.openai.com/v1",
    models: [
      { id: "gpt-4o-mini", label: "GPT-4o mini" },
      { id: "gpt-4o", label: "GPT-4o" },
      { id: "gpt-4.1-mini", label: "GPT-4.1 mini" },
    ],
    defaultModel: "gpt-4o-mini",
    docsUrl: "https://platform.openai.com/api-keys",
  };
}
