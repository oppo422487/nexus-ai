/* ============================================================================
   VOICE · TYPES
   ----------------------------------------------------------------------------
   Provider-agnostic contracts for the voice assistant. The recognition and
   synthesis services, the pipeline, the manager, and the UI all speak these.
   ========================================================================== */

/** High-level conversation state (drives orb colour + animations). */
export type VoiceState = "idle" | "listening" | "thinking" | "speaking" | "error";

/** Recognition/synthesis language. "auto" resolves to the browser locale. */
export type VoiceLanguage = "auto" | "en-US" | "bn-BD";
export type VoiceSttEngine = "auto" | "assemblyai" | "browser";

/** User-owned, persisted voice preferences. */
export interface VoiceSettings {
  /** Preferred live transcription engine; auto uses AssemblyAI when configured. */
  sttEngine: VoiceSttEngine;
  /** Master switch: speak AI replies at all. */
  enableVoiceReply: boolean;
  /** Auto-speak every response (vs. speak-on-demand). */
  autoSpeak: boolean;
  /** Keep listening after each turn (hands-free). */
  continuousListening: boolean;
  /** Require Nexa/নেক্সা before a new hands-free conversation. */
  wakeWordEnabled: boolean;
  /** Temporarily mute AI voice without changing enableVoiceReply. */
  muted: boolean;
  rate: number; // 0.5 – 2.0
  pitch: number; // 0 – 2
  volume: number; // 0 – 1
  language: VoiceLanguage;
  /** Selected Edge neural voice id, or null to match the selected language. */
  voiceURI: string | null;
}

export interface VoiceMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  at: string;
  provider?: string;
}

export type VoiceErrorKind =
  | "mic-denied"
  | "no-mic"
  | "unsupported"
  | "network"
  | "no-speech"
  | "tts"
  | "unknown";

export interface VoiceErrorInfo {
  kind: VoiceErrorKind;
  message: string;
}

/** Friendly, user-facing copy for each error kind. */
export const VOICE_ERROR_COPY: Record<VoiceErrorKind, string> = {
  "mic-denied": "Microphone access is blocked. Allow it in your system/browser settings, then try again.",
  "no-mic": "No microphone was found. Connect one and try again.",
  unsupported: "Live speech recognition isn't available in this environment. Try the latest Chrome or the desktop app.",
  network: "The speech service is unreachable. Check your internet connection.",
  "no-speech": "I didn't catch that — try speaking a little closer to the mic.",
  tts: "Couldn't play the voice reply, but the text is shown above.",
  unknown: "Something went wrong with the voice engine. Please try again.",
};

/** Minimal structural type for the Web Speech API (not in TS lib DOM types). */
export interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start: () => void;
  stop: () => void;
  abort: () => void;
  onresult: ((event: SpeechRecognitionResultEventLike) => void) | null;
  onerror: ((event: { error?: string }) => void) | null;
  onend: (() => void) | null;
  onstart: (() => void) | null;
  onspeechstart: (() => void) | null;
}

export interface SpeechRecognitionResultEventLike {
  resultIndex: number;
  results: ArrayLike<{
    isFinal: boolean;
    0: { transcript: string; confidence: number };
  }>;
}
