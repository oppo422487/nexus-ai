/* Cartesia-primary online TTS with Edge neural fallback. */
import { requestPreferredTtsAudio } from "@/lib/backendAssistantClient";
import type { VoiceSettings } from "./types";

export interface SpeakHandlers {
  onStart?: () => void;
  onSentence?: (index: number, total: number) => void;
  onEnd?: () => void;
  onError?: () => void;
}

export interface OnlineVoiceInfo {
  voiceURI: string;
  name: string;
  lang: "bn-BD" | "en-US";
}

const ONLINE_VOICES: OnlineVoiceInfo[] = [
  { voiceURI: "bn-BD-NabanitaNeural", name: "Bangla - Nabanita", lang: "bn-BD" },
  { voiceURI: "bn-BD-PradeepNeural", name: "Bangla - Pradeep", lang: "bn-BD" },
  { voiceURI: "en-US-AriaNeural", name: "English - Aria", lang: "en-US" },
  { voiceURI: "en-US-GuyNeural", name: "English - Guy", lang: "en-US" },
];

function splitForEdge(text: string, maxLength = 700): string[] {
  const sentences = text.split(/(?<=[।.!?])\s+/u).map((part) => part.trim()).filter(Boolean);
  const chunks: string[] = [];
  for (const sentence of sentences) {
    if (sentence.length > maxLength) {
      for (let offset = 0; offset < sentence.length; offset += maxLength) {
        chunks.push(sentence.slice(offset, offset + maxLength));
      }
      continue;
    }
    const last = chunks[chunks.length - 1];
    if (last && `${last} ${sentence}`.length <= maxLength) chunks[chunks.length - 1] = `${last} ${sentence}`;
    else chunks.push(sentence);
  }
  return chunks;
}

function edgeRate(rate: number): string {
  const percent = Math.max(-50, Math.min(100, Math.round((rate - 1) * 100)));
  return `${percent >= 0 ? "+" : ""}${percent}%`;
}

export class SpeechSynthesisService {
  private audio: HTMLAudioElement | null = null;
  private objectUrl: string | null = null;
  private speaking = false;
  private generation = 0;

  static isSupported(): boolean {
    return typeof window !== "undefined" && typeof Audio !== "undefined" && typeof fetch === "function";
  }

  getVoices(): OnlineVoiceInfo[] {
    return ONLINE_VOICES;
  }

  isSpeaking(): boolean {
    return this.speaking;
  }

  private pickVoice(settings: VoiceSettings, lang: string): string {
    const selected = ONLINE_VOICES.find((voice) => voice.voiceURI === settings.voiceURI);
    if (selected) return selected.voiceURI;
    return lang.startsWith("bn") ? "bn-BD-NabanitaNeural" : "en-US-AriaNeural";
  }

  speak(text: string, settings: VoiceSettings, lang: string, handlers: SpeakHandlers = {}): void {
    this.cancel();
    const generation = this.generation;
    const chunks = splitForEdge(text);
    if (chunks.length === 0) {
      handlers.onEnd?.();
      return;
    }

    this.speaking = true;
    handlers.onStart?.();
    const voice = this.pickVoice(settings, lang);
    const rate = edgeRate(settings.rate);

    void (async () => {
      try {
        for (let index = 0; index < chunks.length; index += 1) {
          if (generation !== this.generation) return;
          const { blob } = await requestPreferredTtsAudio(chunks[index], voice, undefined, rate);
          if (generation !== this.generation) return;
          this.objectUrl = URL.createObjectURL(blob);
          this.audio = new Audio(this.objectUrl);
          this.audio.volume = settings.volume;
          handlers.onSentence?.(index, chunks.length);
          await new Promise<void>((resolve, reject) => {
            const audio = this.audio!;
            audio.addEventListener("ended", () => resolve(), { once: true });
            audio.addEventListener("error", () => reject(new Error("Online TTS audio playback failed.")), { once: true });
            audio.play().catch(reject);
          });
          this.releaseAudio();
        }
        if (generation !== this.generation) return;
        this.speaking = false;
        handlers.onEnd?.();
      } catch {
        if (generation !== this.generation) return;
        this.releaseAudio();
        this.speaking = false;
        handlers.onError?.();
      }
    })();
  }

  private releaseAudio(): void {
    this.audio = null;
    if (this.objectUrl) URL.revokeObjectURL(this.objectUrl);
    this.objectUrl = null;
  }

  cancel(): void {
    this.generation += 1;
    this.speaking = false;
    if (this.audio) {
      this.audio.pause();
      this.audio.removeAttribute("src");
    }
    this.releaseAudio();
  }
}
