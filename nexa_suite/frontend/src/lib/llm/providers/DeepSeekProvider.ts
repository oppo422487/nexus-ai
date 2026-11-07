/* DeepSeek — OpenAI-compatible API; transport inherited from the shared base. */
import { OpenAICompatibleProvider } from "./openaiCompatible";
import type { ProviderMeta } from "../types";

export class DeepSeekProvider extends OpenAICompatibleProvider {
  readonly meta: ProviderMeta = {
    id: "deepseek",
    label: "DeepSeek",
    description: "DeepSeek chat / reasoning models (OpenAI-compatible).",
    futureReady: true,
    requiresKey: true,
    configurableBaseUrl: true,
    defaultBaseUrl: "https://api.deepseek.com/v1",
    models: [
      { id: "deepseek-chat", label: "DeepSeek Chat" },
      { id: "deepseek-reasoner", label: "DeepSeek Reasoner" },
    ],
    defaultModel: "deepseek-chat",
    docsUrl: "https://platform.deepseek.com/api_keys",
  };
}
