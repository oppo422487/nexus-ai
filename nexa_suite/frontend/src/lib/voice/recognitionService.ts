/* ============================================================================
   VOICE · SpeechRecognitionService
   ----------------------------------------------------------------------------
   Robust wrapper around the Web Speech API. Fixes the classic continuous-mode
   bug where recognition dies after the first pause: `onend` auto-restarts the
   engine unless the caller explicitly stopped it. Emits interim + final
   transcripts and classifies errors into friendly kinds.

   Recognition is provided by the browser/platform online speech service. Nexa
   does not load or download a local STT model.
   ========================================================================== */
import type {
  SpeechRecognitionLike,
  SpeechRecognitionResultEventLike,
  VoiceErrorKind,
} from "./types";

type Ctor = new () => SpeechRecognitionLike;

function getCtor(): Ctor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: Ctor;
    webkitSpeechRecognition?: Ctor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null;
}

export interface RecognitionHandlers {
  onInterim?: (text: string) => void;
  onFinal?: (text: string) => void;
  onError?: (kind: VoiceErrorKind, raw: string) => void;
  onStart?: () => void;
  onEnd?: () => void;
  onSpeechStart?: () => void;
}

export class SpeechRecognitionService {
  private recognition: SpeechRecognitionLike | null = null;
  private handlers: RecognitionHandlers = {};
  private stopped = true;
  private continuous = false;
  private lang = "en-US";
  private restartTimer: number | null = null;

  static isSupported(): boolean {
    return getCtor() !== null;
  }

  isRunning(): boolean {
    return !this.stopped;
  }

  start(options: { lang: string; continuous: boolean; handlers: RecognitionHandlers }): boolean {
    const Ctor = getCtor();
    if (!Ctor) {
      options.handlers.onError?.("unsupported", "no SpeechRecognition");
      return false;
    }
    this.handlers = options.handlers;
    this.lang = options.lang;
    this.continuous = options.continuous;
    this.stopped = false;
    this.spawn();
    return true;
  }

  private spawn(): void {
    const Ctor = getCtor();
    if (!Ctor || this.stopped) return;

    const rec = new Ctor();
    rec.lang = this.lang;
    rec.continuous = this.continuous;
    rec.interimResults = true;
    rec.maxAlternatives = 1;

    rec.onstart = () => this.handlers.onStart?.();
    rec.onspeechstart = () => this.handlers.onSpeechStart?.();

    rec.onresult = (event: SpeechRecognitionResultEventLike) => {
      let interim = "";
      let final = "";
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        const transcript = result[0].transcript;
        if (result.isFinal) final += transcript;
        else interim += transcript;
      }
      if (interim.trim()) this.handlers.onInterim?.(interim);
      if (final.trim()) this.handlers.onFinal?.(final.trim());
    };

    rec.onerror = (event: { error?: string }) => {
      const raw = event.error ?? "unknown";
      // "no-speech"/"aborted" are benign in continuous mode — let onend restart.
      if (raw === "no-speech" || raw === "aborted") return;
      this.handlers.onError?.(this.classify(raw), raw);
      if (raw === "not-allowed" || raw === "service-not-allowed") {
        this.stopped = true; // fatal — don't auto-restart into a permission wall
      }
    };

    rec.onend = () => {
      this.handlers.onEnd?.();
      // Auto-restart keeps continuous listening truly continuous across the
      // engine's internal timeouts/pauses.
      if (!this.stopped && this.continuous) {
        this.restartTimer = window.setTimeout(() => this.spawn(), 250);
      }
    };

    this.recognition = rec;
    try {
      rec.start();
    } catch {
      // start() throws if called while already starting — safe to ignore.
    }
  }

  stop(): void {
    this.stopped = true;
    if (this.restartTimer !== null) {
      window.clearTimeout(this.restartTimer);
      this.restartTimer = null;
    }
    if (this.recognition) {
      try {
        this.recognition.stop();
      } catch {
        /* ignore */
      }
      this.recognition = null;
    }
  }

  abort(): void {
    this.stopped = true;
    if (this.restartTimer !== null) {
      window.clearTimeout(this.restartTimer);
      this.restartTimer = null;
    }
    if (this.recognition) {
      try {
        this.recognition.abort();
      } catch {
        /* ignore */
      }
      this.recognition = null;
    }
  }

  private classify(raw: string): VoiceErrorKind {
    switch (raw) {
      case "not-allowed":
      case "service-not-allowed":
        return "mic-denied";
      case "audio-capture":
        return "no-mic";
      case "network":
        return "network";
      case "no-speech":
        return "no-speech";
      default:
        return "unknown";
    }
  }
}
