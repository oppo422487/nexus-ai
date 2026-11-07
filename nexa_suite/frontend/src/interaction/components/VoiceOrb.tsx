/* VoiceOrb — a reusable voice visualiser. It reacts to a `level` (0..1) and a
   `state`, breathing gently when idle and expanding with amplitude when
   listening. It never accesses the microphone itself — feed it a level from the
   opt-in useMicLevel hook or from voice events. Transform/opacity only. */
import { motion } from "framer-motion";
import { INTERACTION_CONFIG } from "../config";
import { useInteraction } from "../context";
import type { VoiceState } from "../events";

export interface VoiceOrbProps {
  level?: number;
  state?: VoiceState;
  size?: number;
  className?: string;
}

export function VoiceOrb({ level = 0, state = "idle", size = 96, className }: VoiceOrbProps) {
  const { reducedMotion } = useInteraction();
  const cfg = INTERACTION_CONFIG.voice;
  const amp = Math.max(0, Math.min(1, level));
  const listening = state === "listening";
  const processing = state === "processing";

  const coreScale = reducedMotion ? 1 : 1 + amp * 0.28;

  return (
    <div
      className={`nxi-orb ${className ?? ""}`}
      data-state={state}
      style={{ width: size, height: size }}
    >
      {/* Amplitude / idle rings */}
      {Array.from({ length: cfg.ringCount }).map((_, i) => (
        <motion.span
          key={i}
          className="nxi-orb-ring"
          animate={
            reducedMotion
              ? { opacity: 0.25, scale: 1 }
              : listening
                ? { opacity: [0.35, 0.05], scale: [1, 1.5 + amp * 0.6] }
                : { opacity: [0.28, 0.1, 0.28], scale: [1, 1.14, 1] }
          }
          transition={{
            duration: listening ? 1.1 : cfg.idlePulseS,
            repeat: Infinity,
            ease: "easeOut",
            delay: (i * (listening ? 0.28 : cfg.idlePulseS / cfg.ringCount)),
          }}
        />
      ))}

      {/* Core */}
      <motion.span
        className="nxi-orb-core"
        data-processing={processing || undefined}
        animate={{ scale: coreScale }}
        transition={{ type: "spring", stiffness: 240, damping: 18 }}
      />
    </div>
  );
}
