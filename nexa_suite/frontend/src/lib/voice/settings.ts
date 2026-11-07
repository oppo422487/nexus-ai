/* ============================================================================
   VOICE · Settings persistence
   ========================================================================== */
import type { VoiceSettings } from "./types";

const KEY = "nexa.mark-plus.voice.settings";

export const DEFAULT_VOICE_SETTINGS: VoiceSettings = {
  sttEngine: "assemblyai",
  enableVoiceReply: true,
  autoSpeak: true,
  continuousListening: true,
  wakeWordEnabled: true,
  muted: false,
  rate: 1,
  pitch: 1,
  volume: 1,
  language: "bn-BD",
  voiceURI: null,
};

export function loadVoiceSettings(): VoiceSettings {
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return { ...DEFAULT_VOICE_SETTINGS };
    const parsed = JSON.parse(raw) as Record<string, unknown>;
    if (parsed.sttEngine === "google") parsed.sttEngine = "assemblyai";
    return { ...DEFAULT_VOICE_SETTINGS, ...parsed } as VoiceSettings;
  } catch {
    return { ...DEFAULT_VOICE_SETTINGS };
  }
}

export function saveVoiceSettings(settings: VoiceSettings): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(settings));
  } catch {
    // best-effort
  }
}

/** Resolve "auto" to a concrete BCP-47 tag for the speech engines. */
export function resolveLanguage(language: VoiceSettings["language"]): string {
  if (language !== "auto") return language;
  if (typeof navigator !== "undefined" && navigator.language) {
    return navigator.language.startsWith("bn") ? "bn-BD" : navigator.language;
  }
  return "en-US";
}
