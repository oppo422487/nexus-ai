type AnimatedOrbProps = {
  size?: "sm" | "md" | "lg" | "xl";
  status?: "idle" | "listening" | "thinking" | "speaking";
  className?: string;
};

const sizeClasses = {
  sm: "h-16 w-16",
  md: "h-24 w-24",
  lg: "h-36 w-36",
  xl: "h-52 w-52",
};

const statusClasses = {
  idle: "nexa-orb-idle",
  listening: "nexa-orb-listening",
  thinking: "nexa-orb-thinking",
  speaking: "nexa-orb-speaking",
};

export function AnimatedOrb({
  size = "md",
  status = "idle",
  className = "",
}: AnimatedOrbProps) {
  return (
    <div className={`relative grid place-items-center ${sizeClasses[size]} ${className}`}>
      <span className={`nexa-orb-ring ${statusClasses[status]}`} />
      <span className="nexa-orb" />
      <span className={`nexa-orb-core ${statusClasses[status]}`} />
    </div>
  );
}
