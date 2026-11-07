/* ============================================================================
   VOICE · public surface
   ========================================================================== */
export { voiceManager, VoiceManager } from "./manager";
export { useVoice } from "./useVoice";
export type { UseVoice } from "./useVoice";
export { SpeechRecognitionService } from "./recognitionService";
export { SpeechSynthesisService } from "./synthesisService";
export { VoicePipeline } from "./pipeline";
export { DEFAULT_VOICE_SETTINGS, loadVoiceSettings, saveVoiceSettings } from "./settings";
export { VOICE_ERROR_COPY } from "./types";
export type {
  VoiceState,
  VoiceLanguage,
  VoiceSttEngine,
  VoiceSettings,
  VoiceMessage,
  VoiceErrorKind,
  VoiceErrorInfo,
} from "./types";
