/* ============================================================================
   MULTI-LLM · LLMRouter
   ----------------------------------------------------------------------------
   Owns the unified `chat()` entry. Resolves an ordered attempt list from the
   user's model selection + failover priority, tries each provider, classifies
   failures, and hands off automatically — recording analytics and emitting a
   "switched to …" notice on failover. The Nexa backend is always the final
   safety net, so chat never dead-ends even with zero API keys.

   The chat UI never names a provider: it calls chat(message, ctx) and the
   router decides everything.
   ========================================================================== */
import { providerRegistry } from "./registry";
import { llmManager } from "./manager";
import { LLMError, reasonLabel, toLLMError } from "./errors";
import type {
  ChatContext,
  ChatResult,
  ModelSelection,
  ProviderCallInput,
  ProviderId,
} from "./types";

/** The provider a specific (non-auto) selection starts from. */
const SELECTION_PROVIDER: Record<Exclude<ModelSelection, "auto">, ProviderId> = {
  gpt: "openai",
  "gemini-pro": "gemini",
  "gemini-flash": "gemini",
  claude: "claude",
  deepseek: "deepseek",
  ollama: "ollama",
};

/** Model override baked into a selection (used when a provider hosts several). */
const SELECTION_MODEL: Partial<Record<ModelSelection, string>> = {
  "gemini-pro": "gemini-1.5-pro",
  "gemini-flash": "gemini-1.5-flash",
};

function isConfigured(id: ProviderId): boolean {
  return providerRegistry.require(id).isConfigured(llmManager.config(id));
}

function isUsable(id: ProviderId): boolean {
  return llmManager.config(id).enabled && isConfigured(id);
}

/** Build the ordered list of provider ids to attempt for this request. */
function resolveAttemptOrder(selection: ModelSelection): ProviderId[] {
  const settings = llmManager.getSettings();
  const order: ProviderId[] = [];

  if (selection !== "auto") {
    order.push(SELECTION_PROVIDER[selection]);
  }
  for (const id of settings.priority) {
    if (!order.includes(id)) order.push(id);
  }
  // Backend is the guaranteed final safety net.
  if (!order.includes("nexa-backend")) order.push("nexa-backend");

  // Only keep providers that are enabled + configured; backend always stays.
  const usable = order.filter((id) => id === "nexa-backend" ? settings.providers[id].enabled : isUsable(id));
  return usable.length > 0 ? usable : ["nexa-backend"];
}

/** Pick the model for a given provider on this request. */
function modelFor(providerId: ProviderId, selection: ModelSelection, isSelectionStart: boolean): string {
  if (isSelectionStart) {
    const forced = SELECTION_MODEL[selection];
    if (forced) return forced;
  }
  return llmManager.config(providerId).defaultModel || providerRegistry.meta(providerId).defaultModel;
}

/** The unified chat entry. The chat UI calls only this. */
export async function routeChat(message: string, context: ChatContext): Promise<ChatResult> {
  const selection = context.selection ?? llmManager.getSettings().selection;
  const order = resolveAttemptOrder(selection);
  const selectionStart = selection !== "auto" ? SELECTION_PROVIDER[selection] : null;

  let firstFailure: { label: string; reason: string } | null = null;
  let lastError: LLMError | null = null;

  for (let i = 0; i < order.length; i += 1) {
    const providerId = order[i];
    const provider = providerRegistry.require(providerId);
    const config = llmManager.config(providerId);
    const input: ProviderCallInput = {
      message: providerId !== "nexa-backend" && context.preferredLanguage !== "Mixed" && context.preferredLanguage
        ? `${message}\n\nReply entirely in ${context.preferredLanguage === "Bangla" ? "Bengali script" : "English"}, unless I explicitly request another reply language in this message.`
        : message,
      history: context.history,
      addressStyle: context.addressStyle,
      preferredLanguage: context.preferredLanguage,
      model: modelFor(providerId, selection, providerId === selectionStart),
      signal: context.signal,
    };

    try {
      const result = await provider.chat(input, config);
      const fellOver = i > 0 && firstFailure !== null;
      if (fellOver) {
        llmManager.markFallback();
        context.onNotice?.({
          title: `${firstFailure!.label} ${firstFailure!.reason}`,
          message: `Switched to ${result.providerLabel}. Conversation continues.`,
          tone: "warning",
        });
      }
      llmManager.markSuccess(providerId);
      return { ...result, fellOver };
    } catch (err) {
      const error = toLLMError(err);
      lastError = error;
      llmManager.markFailure(providerId, error);
      if (!firstFailure) {
        firstFailure = { label: provider.meta.label, reason: reasonLabel(error.kind) };
      }
      // Try the next provider in the chain (unless this was the last one).
    }
  }

  // Everything failed — surface the last error to the caller (ChatPage keeps its
  // existing "start the backend" handling).
  throw lastError ?? new LLMError("unknown", "No LLM provider was able to answer.");
}
