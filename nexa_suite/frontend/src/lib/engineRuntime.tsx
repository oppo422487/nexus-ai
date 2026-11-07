import { createContext, useContext, useEffect, useRef, useState, type ReactNode } from "react";
import { interactionBus } from "@/interaction/events";

export const NATIVE_ENGINE = new URLSearchParams(window.location.search).get("engine") === "native";
const BASE = "http://127.0.0.1:8766/api/engine";
export type EngineConfirmation = { id: string; title: string; detail: string; expires_at: number };
export type EngineEvent = { id: number; kind: string; text: string; at: number; label?: string; confirmation?: EngineConfirmation };
type Snapshot = {
  generation: string; cursor: number; events: EngineEvent[]; connected: boolean;
  configured: boolean; state: string; speaking: boolean; level: number; muted: boolean;
  awake: boolean; confirmation: EngineConfirmation | null;
  camera?: boolean;
  quiz?: { topic: string; index: number; total: number; question: string; options: string[]; answered: boolean; feedback: string } | null;
};
const initial: Snapshot = { generation: "", cursor: 0, events: [], connected: false,
  configured: false, state: "INITIALISING", speaking: false, level: 0, muted: false,
  awake: false, confirmation: null };
const EngineContext = createContext({ ...initial, enabled: NATIVE_ENGINE, error: "" });

export async function engineCommand(action: string, values: Record<string, unknown> = {}) {
  const response = await fetch(`${BASE}/command`, { method: "POST",
    headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...values, action }) });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "ইঞ্জিনের সঙ্গে যোগাযোগ হয়নি।");
  return result as { accepted: boolean; message?: string };
}

export function EngineProvider({ children }: { children: ReactNode }) {
  const [snapshot, setSnapshot] = useState<Snapshot>(initial);
  const [error, setError] = useState("");
  useEffect(() => {
    if (!NATIVE_ENGINE) return;
    let active = true;
    let timer = 0;
    let cursor = 0;
    let generation = "";
    const abort = new AbortController();
    const poll = async () => {
      try {
        const response = await fetch(`${BASE}/events?after=${cursor}`, { signal: abort.signal, cache: "no-store" });
        if (!response.ok) throw new Error("ইঞ্জিনের সঙ্গে সংযোগ হচ্ছে…");
        const next = await response.json() as Snapshot;
        if (!active) return;
        // Sequence numbers restart with the worker; request its new history once.
        if (generation && generation !== next.generation) {
          cursor = 0;
          generation = next.generation;
        } else {
          generation = next.generation;
          cursor = next.cursor;
          setSnapshot(previous => ({ ...next, events:
            (previous.generation === next.generation ? [...previous.events, ...next.events] : next.events).slice(-800) }));
        }
        setError("");
        interactionBus.emit({ type: "voice", payload: { state: next.speaking ? "processing" : next.connected ? "listening" : "idle", level: next.level } });
        interactionBus.emit({ type: "ai:thinking", payload: { active: next.state === "THINKING" || next.state === "PROCESSING" } });
      } catch (failure) {
        if (active) {
          setError(failure instanceof Error ? failure.message : "ইঞ্জিন সংযোগ বিচ্ছিন্ন।");
          setSnapshot(previous => ({ ...previous, connected: false, speaking: false, level: 0 }));
        }
      } finally {
        if (active) timer = window.setTimeout(() => void poll(), 250);
      }
    };
    void poll();
    return () => { active = false; abort.abort(); window.clearTimeout(timer); };
  }, []);
  return <EngineContext.Provider value={{ ...snapshot, enabled: NATIVE_ENGINE, error }}>{children}</EngineContext.Provider>;
}

export const useEngine = () => useContext(EngineContext);

export function EngineInlineTools() {
  const engine = useEngine();
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState("");
  const [frame, setFrame] = useState(0);
  useEffect(() => {
    if (!engine.camera) return;
    const interval = window.setInterval(() => setFrame(previous => previous + 1), 500);
    return () => window.clearInterval(interval);
  }, [engine.camera]);
  const submit = async (action: string, text = "") => {
    try { await engineCommand(action, { text }); setAnswer(""); setError(""); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "কাজটি হয়নি।"); }
  };
  if (!engine.enabled) return null;
  return <>
    {engine.camera && <article className="dashboard-chat-bubble assistant"><div className="dashboard-chat-body">
      <p>ক্যামেরা</p><img src={`${BASE}/frame?t=${frame}`} alt="নেক্সা engine-এর সক্রিয় ক্যামেরা" style={{ width: "100%", maxWidth: 480, borderRadius: 12 }} />
    </div></article>}
    {engine.quiz && <article className="dashboard-chat-bubble assistant"><div className="dashboard-chat-body">
      <strong>{engine.quiz.topic} — {engine.quiz.index + 1}/{engine.quiz.total}</strong>
      <p>{engine.quiz.question}</p>
      {engine.quiz.options.map(option => <button key={option} type="button" className="nx-btn ghost" disabled={engine.quiz?.answered}
        onClick={() => void submit("quiz_answer", option)}>{option}</button>)}
      {!engine.quiz.options.length && !engine.quiz.answered && <form onSubmit={event => { event.preventDefault(); void submit("quiz_answer", answer); }}>
        <label htmlFor="native-quiz-answer">আপনার উত্তর</label>
        <input id="native-quiz-answer" value={answer} onChange={event => setAnswer(event.target.value)} />
        <button className="nx-btn" type="submit" disabled={!answer.trim()}>উত্তর দিন</button>
      </form>}
      {engine.quiz.answered && <><p>{engine.quiz.feedback}</p><button type="button" className="nx-btn" onClick={() => void submit("quiz_next")}>
        {engine.quiz.index + 1 === engine.quiz.total ? "শেষ করুন" : "পরের প্রশ্ন"}</button></>}
      <button type="button" className="nx-btn ghost" onClick={() => void submit("quiz_close")}>কুইজ বন্ধ</button>
      {error && <p role="alert">{error}</p>}
    </div></article>}
  </>;
}

export function EngineControls({ compact = false }: { compact?: boolean }) {
  const engine = useEngine();
  const [error, setError] = useState("");
  const holding = useRef(false);
  const action = async (name: string) => {
    try { await engineCommand(name); setError(""); }
    catch (failure) { setError(failure instanceof Error ? failure.message : "কাজটি হয়নি।"); }
  };
  const release = () => {
    if (holding.current) { holding.current = false; void action("ptt_up"); }
  };
  useEffect(() => {
    const stop = () => { if (holding.current) { holding.current = false; void engineCommand("ptt_up").catch(() => undefined); } };
    window.addEventListener("blur", stop);
    document.addEventListener("visibilitychange", stop);
    return () => { stop(); window.removeEventListener("blur", stop); document.removeEventListener("visibilitychange", stop); };
  }, []);
  if (!engine.enabled) return null;
  return <div className={compact ? "nx-native-controls compact" : "nx-native-controls"}>
    <span className={`nx-chip ${engine.connected ? "" : "warn"}`} role="status">
      {engine.error || (!engine.configured ? "Settings-এ engine key দিন" : engine.speaking ? "কথা বলছি" : (engine.state === "THINKING" || engine.state === "PROCESSING") ? "ভাবছি…" : engine.connected ? "সংযুক্ত" : "সংযোগ হচ্ছে…")}
    </span>
    <button type="button" className="nx-btn ghost" onClick={() => void action("mute")} aria-pressed={engine.muted}>
      {engine.muted ? "মাইক চালু" : "মাইক বন্ধ"}
    </button>
    <button type="button" className="nx-btn ghost" onClick={() => void action("interrupt")} disabled={!engine.connected}>থামাও</button>
    {!compact && <>
      <button type="button" className="nx-btn ghost" onClick={() => void action(engine.awake ? "sleep" : "wake")} disabled={!engine.connected}>
        {engine.awake ? "বিরতি" : "জাগাও"}
      </button>
      <button type="button" className="nx-btn ghost" disabled={!engine.connected}
        onPointerDown={event => { event.currentTarget.setPointerCapture(event.pointerId); holding.current = true; void action("ptt_down"); }}
        onPointerUp={release} onPointerCancel={release} onLostPointerCapture={release}
        onKeyDown={event => { if ((event.key === " " || event.key === "Enter") && !event.repeat) { event.preventDefault(); holding.current = true; void action("ptt_down"); } }}
        onKeyUp={event => { if (event.key === " " || event.key === "Enter") release(); }}>
        ধরে কথা বলুন
      </button>
    </>}
    {error && <span role="alert" className="nx-status-err">{error}</span>}
  </div>;
}

export function EngineSettings() {
  const engine = useEngine();
  const [key, setKey] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  if (!engine.enabled) return null;
  return <section className="nx-card">
    <div className="nx-card-head"><div className="nx-card-title">নেক্সা Live Engine</div></div>
    <p>এই UI থেকেই বর্তমান voice engine, memory ও tools ব্যবহার হবে।</p>
    <form onSubmit={event => { event.preventDefault(); setBusy(true);
      void engineCommand("configure", { key }).then(result => { setMessage(result.message || "সংরক্ষিত"); setKey(""); })
        .catch(failure => setMessage(String(failure.message)))
        .finally(() => setBusy(false)); }}>
      <label htmlFor="native-gemini-key">Gemini API key</label>
      <input id="native-gemini-key" type="password" autoComplete="off" value={key} onChange={event => setKey(event.target.value)} placeholder={engine.configured ? "Key আগে থেকেই দেওয়া আছে" : "আপনার Gemini API key"} />
      <button className="nx-btn" type="submit" disabled={busy || key.trim().length < 16}>সংরক্ষণ করুন</button>
    </form>
    <button type="button" className="nx-btn ghost" onClick={() => void engineCommand("advanced_settings").catch(failure => setMessage(failure.message))}>আরও engine ও device settings</button>
    {message && <p role="status">{message}</p>}
    <EngineControls />
  </section>;
}

export function EngineParticles() {
  const engine = useEngine();
  const canvas = useRef<HTMLCanvasElement>(null);
  const amplitude = useRef(0);
  amplitude.current = engine.speaking ? engine.level : 0;
  useEffect(() => {
    if (!NATIVE_ENGINE || !canvas.current) return;
    const element = canvas.current;
    const ctx = element.getContext("2d");
    if (!ctx) return;
    let width = 0, height = 0, frame = 0, phase = 0, last = 0;
    const dots = Array.from({ length: 550 }, (_, i) => ({
      a: i * 2.39996323, y: 1 - 2 * (i + .5) / 550, radius: .72 + ((i * 37) % 100) / 360,
    }));
    const resize = () => { width = element.width = innerWidth; height = element.height = innerHeight; };
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
    resize();
    const draw = (now: number) => {
      frame = requestAnimationFrame(draw);
      if (document.hidden || now - last < 33) return;
      const dt = Math.min(.1, (now - (last || now)) / 1000); last = now;
      phase += reduced.matches ? 0 : dt * (.12 + amplitude.current * 1.4);
      ctx.clearRect(0, 0, width, height);
      const radius = Math.min(width * .26, height * .38);
      const cx = width * .65, cy = height * .48;
      for (const dot of dots) {
        const ring = Math.sqrt(1 - dot.y * dot.y);
        const a = dot.a + phase + .18 * Math.sin(dot.y * 4 + phase);
        const z = Math.sin(a) * ring;
        const fold = 1 + .09 * Math.sin(a * 3 + dot.y * 5 + phase) + amplitude.current * .12;
        const x = cx + Math.cos(a) * ring * radius * dot.radius * fold;
        const y = cy + dot.y * radius * dot.radius * fold;
        ctx.fillStyle = `rgba(93,102,127,${.12 + (z + 1) * .14})`;
        ctx.beginPath();ctx.arc(x, y, .6 + (z + 1) * .35, 0, Math.PI * 2);ctx.fill();
      }
    };
    frame = requestAnimationFrame(draw);
    window.addEventListener("resize", resize);
    return () => { cancelAnimationFrame(frame); window.removeEventListener("resize", resize); };
  }, []);
  return engine.enabled ? <canvas ref={canvas} aria-hidden="true" className="nx-native-particles" /> : null;
}
