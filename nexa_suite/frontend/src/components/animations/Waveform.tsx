type WaveformProps = {
  bars?: number;
  active?: boolean;
  variant?: "cyan" | "purple" | "mixed";
  className?: string;
};

const variantClasses = {
  cyan: "from-nexa-cyan to-nexa-cyan",
  purple: "from-nexa-purple to-nexa-purple",
  mixed: "from-nexa-cyan to-nexa-purple",
};

export function Waveform({
  bars = 9,
  active = false,
  variant = "mixed",
  className = "",
}: WaveformProps) {
  return (
    <div className={`flex h-12 items-end justify-center gap-1.5 ${className}`}>
      {Array.from({ length: bars }, (_, index) => (
        <span
          key={index}
          className={`block w-1.5 rounded-full bg-gradient-to-t ${variantClasses[variant]} ${
            active ? "nexa-wave-active" : "h-3 opacity-45"
          }`}
          style={active ? { animationDelay: `${index * 0.08}s` } : undefined}
        />
      ))}
    </div>
  );
}
