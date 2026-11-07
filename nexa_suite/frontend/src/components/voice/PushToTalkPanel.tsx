import { useCallback, useEffect, useRef, useState } from "react";
import {
  getBackendPermissions, getBackendSttEngines, requestYouTubeCommand, SttEnginesResponseDto,
  TranscriptionResponseDto, transcribeAudioBlob,
} from "@/lib/backendAssistantClient";
import { ContinuousVoiceCapture, startContinuousVoiceCapture } from "@/lib/audioRecorder";
import { loadProfile } from "@/lib";
import { LoaderCircle, Mic, MicOff } from "lucide-react";

type ListenStatus = "idle" | "starting" | "listening" | "hearing" | "transcribing" | "processing" | "error";

/** Always-listening online Bangla STT with local silence/utterance detection. */
export function PushToTalkPanel({ onTranscript, compact = false }: {
  onTranscript: (text: string) => void | Promise<void>;
  compact?: boolean;
}) {
  const [status, setStatus] = useState<ListenStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [result, setResult] = useState<TranscriptionResponseDto | null>(null);
  const [engines, setEngines] = useState<SttEnginesResponseDto | null>(null);
  const [micLevel, setMicLevel] = useState(0);
  const captureRef = useRef<ContinuousVoiceCapture | null>(null);
  const startingRef = useRef(false);
  const generationRef = useRef(0);
  const mountedRef = useRef(true);
  const transcriptHandlerRef = useRef(onTranscript);
  const wakeActiveUntilRef = useRef(0);
  const wakeWordEnabledRef = useRef(true);
  transcriptHandlerRef.current = onTranscript;

  try {
    const savedVoiceSettings = localStorage.getItem("nexa.mark-plus.voice.settings");
    const parsedVoiceSettings = savedVoiceSettings ? JSON.parse(savedVoiceSettings) as { wakeWordEnabled?: boolean } : {};
    wakeWordEnabledRef.current = parsedVoiceSettings.wakeWordEnabled ?? true;
  } catch {
    wakeWordEnabledRef.current = true;
  }

  const restoreYouTubeAudio = useCallback(() => {
    void requestYouTubeCommand({ action: "restore", user_confirmed: true, source: "continuous_voice_restore" }).catch(() => undefined);
  }, []);

  const stopListening = useCallback(() => {
    generationRef.current += 1;
    startingRef.current = false;
    captureRef.current?.stop();
    captureRef.current = null;
    setMicLevel(0);
    restoreYouTubeAudio();
    if (mountedRef.current) setStatus("idle");
  }, [restoreYouTubeAudio]);

  const startListening = useCallback(async () => {
    if (captureRef.current || startingRef.current) return;
    startingRef.current = true;
    const generation = generationRef.current + 1;
    generationRef.current = generation;
    setErrorMessage(null);
    setStatus("starting");
    try {
      const permissions = await getBackendPermissions();
      const alwaysOn = permissions.permissions.find((item) => item.key === "always_on_microphone");
      const stt = permissions.permissions.find((item) => item.key === "voice_stt");
      if (!alwaysOn?.enabled || !stt?.enabled) {
        throw new Error("Always-listening microphone or Voice STT is disabled in Settings > Security.");
      }
      const capture = await startContinuousVoiceCapture({
        onAudioLevel: (level) => { if (mountedRef.current) setMicLevel(level); },
        onVoiceState: (hearing) => {
          if (mountedRef.current) setStatus(hearing ? "hearing" : "listening");
        },
        onError: (error) => {
          if (!mountedRef.current) return;
          setStatus("error");
          setErrorMessage(error.message);
        },
        onUtterance: async (blob) => {
          if (!mountedRef.current) return;
          setStatus("transcribing");
          void requestYouTubeCommand({ action: "duck", value: 8, user_confirmed: true, source: "continuous_voice_ducking" }).catch(() => undefined);
          try {
            const language = loadProfile().languageMode === "English" ? "en-US" : "bn-BD";
            const response = await transcribeAudioBlob(blob, "continuous-voice.wav", undefined, language);
            if (!mountedRef.current) return;
            setResult(response);
            if (!response.transcribed || !response.text.trim()) {
              setStatus("listening");
              if (response.error && !/not clear|unknown/i.test(response.error)) setErrorMessage(response.error);
              return;
            }
            const transcript = response.text.trim();
            try {
              const currentSettings = JSON.parse(localStorage.getItem("nexa.mark-plus.voice.settings") || "{}") as { wakeWordEnabled?: boolean };
              wakeWordEnabledRef.current = currentSettings.wakeWordEnabled ?? true;
            } catch { wakeWordEnabledRef.current = true; }
            const wakeMatch = /(?:^|\s)(?:nexa|নেক্সা\s*এআই|নেক্সা)(?=\s|$|[,।.!?])/iu.test(transcript);
            if (wakeWordEnabledRef.current && !wakeMatch && Date.now() > wakeActiveUntilRef.current) {
              setStatus("listening");
              return;
            }
            if (wakeMatch) wakeActiveUntilRef.current = Date.now() + 30_000;
            const command = transcript
              .replace(/(?:^|\s)(?:hey\s+)?(?:nexa|নেক্সা\s*এআই|নেক্সা)(?=\s|$|[,।.!?])/iu, " ")
              .trim().replace(/^[,।.!?\s]+/u, "");
            if (!command) {
              setStatus("listening");
              return;
            }
            setStatus("processing");
            await transcriptHandlerRef.current(command);
            wakeActiveUntilRef.current = Date.now() + 20_000;
            if (mountedRef.current) setStatus("listening");
          } catch (error) {
            if (!mountedRef.current) return;
            setStatus("error");
            setErrorMessage(error instanceof Error ? error.message : "Online voice transcription failed.");
          } finally {
            restoreYouTubeAudio();
          }
        },
      });
      if (!mountedRef.current || generation !== generationRef.current) {
        capture.stop();
        return;
      }
      captureRef.current = capture;
      setStatus("listening");
    } catch (error) {
      if (!mountedRef.current || generation !== generationRef.current) return;
      setStatus("error");
      const message = error instanceof Error ? error.message : "Microphone could not be started.";
      setErrorMessage(/denied|permission|notallowed/i.test(message)
        ? "Microphone permission denied. Windows Settings > Privacy & security > Microphone থেকে desktop app access চালু করুন।"
        : message);
    } finally {
      if (generation === generationRef.current) startingRef.current = false;
    }
  }, [restoreYouTubeAudio]);

  useEffect(() => {
    mountedRef.current = true;
    void getBackendSttEngines().then(setEngines).catch(() => undefined);
    const onOutputState = (event: Event) => {
      const active = Boolean((event as CustomEvent<{ active?: boolean }>).detail?.active);
      captureRef.current?.setPaused(active);
      if (active) setMicLevel(0);
      if (!active && captureRef.current && mountedRef.current) setStatus("listening");
    };
    window.addEventListener("nexa:voice-output-state", onOutputState);
    if (compact) void startListening();
    return () => {
      mountedRef.current = false;
      generationRef.current += 1;
      startingRef.current = false;
      window.removeEventListener("nexa:voice-output-state", onOutputState);
    captureRef.current?.stop();
    captureRef.current = null;
    setMicLevel(0);
      restoreYouTubeAudio();
    };
  }, [compact, restoreYouTubeAudio, startListening]);

  const listening = ["listening", "hearing", "transcribing", "processing"].includes(status);
  const busy = ["starting", "transcribing", "processing"].includes(status);
  const label = status === "starting" ? "Mic starting…" : status === "listening" ? "Say ‘Nexa’"
    : status === "hearing" ? "কথা শুনছি…" : status === "transcribing" ? "বোঝার চেষ্টা…"
    : status === "processing" ? "উত্তর দিচ্ছি…" : status === "error" ? "Voice error" : "Voice off";

  if (compact) return (
    <div className="nx-global-ptt">
      <button type="button" className={`nx-icon-btn nx-global-ptt-button ${listening ? "recording" : ""}`}
        onClick={listening || status === "starting" ? stopListening : () => void startListening()}
        title={listening ? "Stop always-listening microphone" : "Enable always-listening microphone"}
        aria-label={listening ? "Stop always-listening microphone" : "Enable always-listening microphone"}>
        {busy ? <LoaderCircle className="nx-spin" /> : listening ? <Mic /> : <MicOff />}
      </button>
      <span className={`nx-global-ptt-label ${status}`} title={errorMessage ?? undefined}>{label}</span>
    </div>
  );

  const preferredEngine = engines?.engines.find((engine) => engine.name === engines.preferred_engine);
  return (
    <div className="voice-panel push-to-talk-panel">
      <div className="voice-panel-header"><div><p className="eyebrow">Always-listening Voice</p><h4>Nexa আপনার কথা শুনবে</h4>
        <p>“Nexa” বা “নেক্সা” বলে command দিন। Follow-up window-তে পরের কথা wake word ছাড়াও নেওয়া হবে। উত্তর দেওয়ার সময় mic pause থাকে।</p></div></div>
      <div className="ptt-controls"><button type="button" className={`real-listening-button ${listening ? "recording" : ""}`}
        onClick={listening ? stopListening : () => void startListening()} disabled={status === "starting"}>
        {status === "starting" ? "Starting microphone…" : listening ? "Stop Always Listening" : "Start Always Listening"}
      </button></div>
      <div className="ptt-recording-note">Status: <strong>{label}</strong></div>
      <div className="nxv-range" role="meter" aria-label="Microphone input level" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(micLevel * 100)}>
        <div style={{ width: `${Math.round(micLevel * 100)}%`, height: 6, borderRadius: 6, background: micLevel > 0.35 ? "#22c55e" : "#38bdf8", transition: "width 100ms linear" }} />
      </div>
      {errorMessage && <div className="real-listening-error">{errorMessage}</div>}
      {result?.transcribed && <div className="real-listening-transcript"><span>আপনি বলেছেন</span><p>{result.text}</p></div>}
      <div className="ptt-engine-status"><span>Engine: <strong>{preferredEngine?.label ?? "Online Bangla STT"}</strong> · continuous VAD · no local model</span></div>
    </div>
  );
}
