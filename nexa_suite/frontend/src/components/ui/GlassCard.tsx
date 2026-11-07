import type { ReactNode } from "react";

type GlassCardProps = {
  children: ReactNode;
  className?: string;
  glow?: "cyan" | "purple" | "none";
};

const glowClasses = {
  cyan: "shadow-neon-cyan",
  purple: "shadow-neon-purple",
  none: "",
};

export function GlassCard({
  children,
  className = "",
  glow = "none",
}: GlassCardProps) {
  return (
    <div
      className={`nexa-glass nexa-border rounded-3xl p-5 transition-transform duration-200 hover:-translate-y-0.5 ${glowClasses[glow]} ${className}`}
    >
      {children}
    </div>
  );
}
