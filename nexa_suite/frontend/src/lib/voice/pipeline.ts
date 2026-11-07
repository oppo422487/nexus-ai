/* ============================================================================
   VOICE · VoicePipeline
   ----------------------------------------------------------------------------
   Turns a final transcript into an assistant turn through the same Nexa
   backend endpoint used by typed Dashboard commands. This is important for
   action intents: an external chat model must never swallow an app/website
   command that the backend safety router needs to execute.
   ========================================================================== */
import { requestChatMessage } from "@/lib/backendAssistantClient";
import type { ChatTurn, LLMNotice } from "@/lib/llm";

export interface VoicePipelineResult {
  text: string;
  provider: string;
  fellOver: boolean;
}

export class VoicePipeline {
  async process(
    message: string,
    ctx: {
      history: ChatTurn[];
      conversationId: string;
      addressStyle?: string;
      preferredLanguage?: string;
      signal?: AbortSignal;
      onNotice?: (notice: LLMNotice) => void;
    },
  ): Promise<VoicePipelineResult> {
    void ctx.conversationId;
    void ctx.signal;
    void ctx.onNotice;
    const history = ctx.history
      .filter((turn) => turn.role !== "system")
      .map((turn) => ({ role: turn.role as "user" | "assistant", content: turn.content }));
    const result = await requestChatMessage(message, history, ctx.addressStyle, "auto", "voice_conversation", undefined, ctx.preferredLanguage);
    return {
      text: result.answer,
      provider: result.provider || result.llm_provider || "Nexa Backend",
      fellOver: Boolean(result.fallback_used),
    };
  }
}
