/* ============================================================================
   VOICE · useVoice — React binding for the VoiceManager singleton.
   ========================================================================== */
import { useSyncExternalStore } from "react";
import { voiceManager, VoiceManager } from "./manager";
import type { VoiceErrorInfo, VoiceMessage, VoiceSettings, VoiceState } from "./types";
import type { OnlineVoiceInfo } from "./synthesisService";

export interface UseVoice {
  state: VoiceState;
  messages: VoiceMessage[];
  interim: string;
  error: VoiceErrorInfo | null;
  settings: VoiceSettings;
  recognitionSupported: boolean;
  synthesisSupported: boolean;
  voices: OnlineVoiceInfo[];
  manager: typeof voiceManager;
}

export function useVoice(): UseVoice {
  useSyncExternalStore(
    (cb) => voiceManager.subscribe(cb),
    () => voiceManager.version,
    () => voiceManager.version,
  );

  return {
    state: voiceManager.state,
    messages: voiceManager.messages,
    interim: voiceManager.interim,
    error: voiceManager.error,
    settings: voiceManager.getSettings(),
    recognitionSupported: VoiceManager.recognitionSupported(),
    synthesisSupported: VoiceManager.synthesisSupported(),
    voices: voiceManager.getVoices(),
    manager: voiceManager,
  };
}
