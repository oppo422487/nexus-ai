import { useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import { ArrowLeft, Mic, MicOff, Radio, Trash2, Volume2, VolumeX } from "lucide-react";
import { useVoice } from "@/lib/voice";

const STATE_COPY: Record<string, { label: string; detail: string }> = {
  idle: { label: "VOICE LINK STANDBY", detail: "Tap the core to begin" },
  listening: { label: "LISTENING", detail: "Speak naturally — Nexa stays with you" },
  thinking: { label: "PROCESSING", detail: "Reading intent and preparing a response" },
  speaking: { label: "NEXA SPEAKING", detail: "You can interrupt at any time" },
  error: { label: "VOICE LINK ERROR", detail: "Check microphone access and try again" },
};

const PARTICLES = Array.from({ length: 42 }, (_, index) => ({
  id: index,
  angle: (index * 137.508) % 360,
  radius: 23 + ((index * 17) % 47),
  size: 2 + ((index * 7) % 4),
  delay: -((index * 0.19) % 5),
  duration: 4.5 + ((index * 11) % 35) / 10,
}));

function lastWords(text: string, count = 3): string {
  return text.trim().split(/\s+/).filter(Boolean).slice(-count).join(" ");
}

export function VoiceConversation({ onBack, autoStart = false }: { onBack?: () => void; autoStart?: boolean }) {
  const { state, messages, interim, error, settings, recognitionSupported, synthesisSupported, manager } = useVoice();
  const stageRef = useRef<HTMLDivElement | null>(null);
  const [level, setLevel] = useState(0.08);
  const lastUserMessage = useMemo(() => [...messages].reverse().find((message) => message.role === "user")?.text ?? "", [messages]);
  const visibleWords = lastWords(interim || lastUserMessage);
  const assistantMessages = useMemo(() => messages.filter((message) => message.role === "assistant").slice(-3), [messages]);
  const stateCopy = STATE_COPY[state] ?? STATE_COPY.idle;

  useEffect(() => {
    if (!autoStart || !recognitionSupported) return;
    const timer = window.setTimeout(() => void manager.startListening(), 120);
    return () => window.clearTimeout(timer);
  }, [autoStart, manager, recognitionSupported]);

  useEffect(() => {
    let frame = 0;
    let stream: MediaStream | null = null;
    let context: AudioContext | null = null;
    let cancelled = false;
    if (state !== "listening" || !navigator.mediaDevices?.getUserMedia) {
      setLevel(state === "speaking" ? 0.62 : state === "thinking" ? 0.34 : 0.08);
      return;
    }
    void navigator.mediaDevices.getUserMedia({ audio: true }).then((micStream) => {
      if (cancelled) { micStream.getTracks().forEach((track) => track.stop()); return; }
      stream = micStream;
      context = new AudioContext();
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.72;
      context.createMediaStreamSource(micStream).connect(analyser);
      const samples = new Uint8Array(analyser.frequencyBinCount);
      let lastPaint = 0;
      const read = (time: number) => {
        analyser.getByteFrequencyData(samples);
        const average = samples.reduce((sum, value) => sum + value, 0) / samples.length / 255;
        const next = Math.min(1, 0.08 + average * 2.85);
        stageRef.current?.style.setProperty("--voice-level", next.toFixed(3));
        if (time - lastPaint > 90) { setLevel(next); lastPaint = time; }
        frame = requestAnimationFrame(read);
      };
      frame = requestAnimationFrame(read);
    }).catch(() => setLevel(0.16));
    return () => {
      cancelled = true;
      cancelAnimationFrame(frame);
      stream?.getTracks().forEach((track) => track.stop());
      void context?.close();
    };
  }, [state]);

  useEffect(() => () => manager.stopListening(), [manager]);
  const active = state === "listening" || state === "thinking" || state === "speaking";
  const toggleVoice = () => active ? manager.stopListening() : void manager.startListening();

  return (
    <section className={`nx-voice-room is-${state}`} ref={stageRef} style={{ "--voice-level": level } as CSSProperties}>
      <header className="nx-voice-room-head">
        <button type="button" className="nx-voice-icon-control" onClick={onBack} aria-label="Back to dashboard"><ArrowLeft size={18} /></button>
        <div className="nx-voice-brand"><span className="nx-voice-brand-mark"><Radio size={14} /></span><div><strong>NEXA // VOICE CORE</strong><span>CONTINUOUS CONVERSATION CHANNEL</span></div></div>
        <span className={`nx-voice-live-dot ${active ? "active" : ""}`}>{active ? "LIVE" : "STANDBY"}</span>
      </header>

      <div className="nx-voice-display" aria-live="polite">
        <div className="nx-voice-user-caption"><span>YOU // LIVE TRANSCRIPT</span><strong>{visibleWords || (state === "listening" ? "…" : "VOICE INPUT READY")}</strong></div>
        <button type="button" className="nx-voice-orbit" onClick={toggleVoice} disabled={!recognitionSupported} aria-label={active ? "Stop voice conversation" : "Start continuous voice conversation"}>
          <span className="nx-voice-orbit-boundary" /><span className="nx-voice-orbit-boundary inner" /><span className="nx-voice-core"><Mic size={26} /></span>
          {PARTICLES.map((particle) => <i key={particle.id} className="nx-voice-particle" style={{ "--angle": `${particle.angle}deg`, "--radius": `${particle.radius}%`, "--size": `${particle.size}px`, "--delay": `${particle.delay}s`, "--duration": `${particle.duration}s` } as CSSProperties} />)}
        </button>
        <div className="nx-voice-state-copy"><strong>{stateCopy.label}</strong><span>{stateCopy.detail}</span></div>
      </div>

      <div className="nx-voice-replies">
        <span className="nx-voice-reply-label">NEXA // RESPONSE STREAM</span>
        {assistantMessages.length === 0 ? <p className="nx-voice-reply-empty">Your complete response will appear here.</p> : assistantMessages.map((message) => <article key={message.id} className="nx-voice-reply"><p>{message.text}</p>{message.provider && <small>{message.provider}</small>}</article>)}
        {state === "thinking" && <div className="nx-voice-thinking"><i /><i /><i /></div>}
      </div>

      {error && <div className="nx-voice-error">{error.message}</div>}
      {!recognitionSupported && <div className="nx-voice-error">Live recognition needs Chrome or the Nexa desktop app.</div>}
      <footer className="nx-voice-controls">
        <button type="button" onClick={toggleVoice} disabled={!recognitionSupported} className={active ? "danger" : "primary"}>{active ? <><MicOff size={16} /> END SESSION</> : <><Mic size={16} /> START LISTENING</>}</button>
        <button type="button" onClick={() => manager.toggleMute()}>{settings.muted ? <><VolumeX size={16} /> VOICE MUTED</> : <><Volume2 size={16} /> VOICE ON</>}</button>
        <button type="button" onClick={() => manager.clearConversation()} disabled={messages.length === 0}><Trash2 size={16} /> CLEAR</button>
        {!synthesisSupported && <span className="nx-voice-text-only">TEXT-ONLY OUTPUT</span>}
      </footer>
    </section>
  );
}

export default VoiceConversation;
