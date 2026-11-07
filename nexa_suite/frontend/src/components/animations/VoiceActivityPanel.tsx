import { GlassCard } from "@/components/ui";

import { AnimatedOrb } from "./AnimatedOrb";
import { Waveform } from "./Waveform";

type VoiceActivityPanelProps = {
  status?: "idle" | "listening" | "thinking" | "speaking";
  transcript?: string;
  duration?: string;
  className?: string;
};

const statusLabels = {
  idle: "Idle",
  listening: "Listening",
  thinking: "Thinking",
  speaking: "Speaking",
};

export function VoiceActivityPanel({
  status = "idle",
  transcript = "Waiting for voice input...",
  duration = "00:00",
  className = "",
}: VoiceActivityPanelProps) {
  const isActive = status !== "idle";

  return (
    <GlassCard className={className} glow={isActive ? "cyan" : "none"}>
      <div className="flex items-center gap-4">
        <AnimatedOrb size="sm" status={status} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm font-semibold text-nexa-text">{statusLabels[status]}</p>
            <span className="text-sm text-nexa-muted">{duration}</span>
          </div>
          <Waveform active={isActive} bars={7} className="mt-2 justify-start" />
          <p className="mt-2 truncate text-sm text-nexa-muted">{transcript}</p>
        </div>
      </div>
    </GlassCard>
  );
}
