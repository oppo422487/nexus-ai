/* FloatingVoiceOrb — the permanent AI presence. A always-mounted VoiceOrb that
   reflects Nexa's live state from the event bus: it breathes when idle, pulses
   while the assistant is thinking/executing, and expands with voice amplitude.
   A global interaction layer (same pattern as the other overlays), driven
   entirely by events — no backend, state, or routing coupling. */
import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useInteraction } from "../../context";
import type { VoiceState } from "../../events";
import { VoiceOrb } from "../VoiceOrb";

const LABELS: Record<VoiceState, string> = {
  idle: "Nexa",
  listening: "Listening…",
  processing: "Thinking…",
};

export function FloatingVoiceOrb() {
  const { subscribe, reducedMotion } = useInteraction();
  const [state, setState] = useState<VoiceState>("idle");
  const [level, setLevel] = useState(0);
  const resetTimer = useRef(0);

  useEffect(() => {
    const unsub = subscribe((event) => {
      if (event.type === "ai:thinking") {
        window.clearTimeout(resetTimer.current);
        setState(event.payload.active ? "processing" : "idle");
      } else if (event.type === "voice") {
        if (event.payload.state) setState(event.payload.state);
        if (typeof event.payload.level === "number") setLevel(event.payload.level);
      } else if (event.type === "command:execute") {
        window.clearTimeout(resetTimer.current);
        if (event.payload.status === "start") {
          setState("processing");
        } else {
          resetTimer.current = window.setTimeout(() => setState("idle"), 1400);
        }
      }
    });
    return () => {
      unsub();
      window.clearTimeout(resetTimer.current);
    };
  }, [subscribe]);

  return (
    <motion.div
      className="nxi-assistant"
      data-state={state}
      initial={reducedMotion ? { opacity: 0 } : { opacity: 0, scale: 0.8, y: 12 }}
      animate={{ opacity: 1, scale: 1, y: 0 }}
      transition={{ type: "spring", stiffness: 220, damping: 20, delay: 0.4 }}
      title={`Nexa · ${LABELS[state]}`}
    >
      <VoiceOrb state={state} level={level} size={58} />
      <span className="nxi-assistant-label">{LABELS[state]}</span>
    </motion.div>
  );
}
