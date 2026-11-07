/* ActivityDriver — the single cinematic controller. Each frame it eases every
   activity channel toward its target (asymmetric: quicker to rise, gentler to
   settle, so modes "smoothly settle"), decays the command burst, derives the
   coarse mode, and publishes everything to <html> so the CSS layer enters the
   same cinematic mode as the 3D scene:
     • data-ai-mode   — "idle" | "thinking" | "command" | "voice"
     • data-ai-state  — legacy Phase-F coarse state (kept for existing rules)
     • --nx-core-energy / --nx-core-pulse       — OMEGA-1 heartbeat + intensity
     • --nx-ai-thinking / --nx-ai-command / --nx-ai-voice — per-channel weights
   One clock for the whole OS. Lives inside the Canvas → shares/pauses with the
   render loop. */
import { useFrame } from "@react-three/fiber";
import { ENV_CONFIG } from "../config";
import { aiActivity, type AiMode } from "../activity";

let lastWrite = 0;

function ease(cur: number, target: number, d: number): number {
  const rate = target > cur ? 3.0 : 1.8; // rise faster, settle gently
  return cur + (target - cur) * Math.min(1, d * rate);
}

export function ActivityDriver() {
  useFrame((state, delta) => {
    const d = Math.min(delta, 0.05);
    const c = aiActivity.channel;
    const t = aiActivity.target;

    c.thinking = ease(c.thinking, t.thinking, d);
    c.command = ease(c.command, t.command, d);
    c.voice = ease(c.voice, t.voice, d);
    aiActivity.commandBurst = Math.max(0, aiActivity.commandBurst - d * 1.4);

    aiActivity.value = Math.min(1.6, Math.max(c.thinking, c.command, c.voice) + aiActivity.commandBurst * 0.5);

    const mode: AiMode =
      aiActivity.commandBurst > 0.35 || c.command > 0.3
        ? "command"
        : c.thinking > 0.3
          ? "thinking"
          : c.voice > 0.3
            ? "voice"
            : "idle";
    aiActivity.mode = mode;

    const root = document.documentElement;
    if (root.dataset.aiMode !== mode) root.dataset.aiMode = mode;
    const legacy = aiActivity.value > 0.55 ? "thinking" : aiActivity.value > 0.14 ? "active" : "idle";
    if (root.dataset.aiState !== legacy) root.dataset.aiState = legacy;

    // Throttle CSS-var writes to ~20/s.
    const now = state.clock.elapsedTime;
    if (now - lastWrite >= 0.05) {
      lastWrite = now;
      const pulse = 0.5 + 0.5 * Math.sin(now * ENV_CONFIG.core.pulseSpeed);
      root.style.setProperty("--nx-core-energy", aiActivity.value.toFixed(3));
      root.style.setProperty("--nx-core-pulse", pulse.toFixed(3));
      root.style.setProperty("--nx-ai-thinking", c.thinking.toFixed(3));
      root.style.setProperty("--nx-ai-command", aiActivity.commandBurst.toFixed(3));
      root.style.setProperty("--nx-ai-voice", c.voice.toFixed(3));
    }
  });
  return null;
}
