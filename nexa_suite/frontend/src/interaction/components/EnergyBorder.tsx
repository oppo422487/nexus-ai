/* EnergyBorder — wraps content with a subtle animated conic-gradient border
   that reads as flowing energy. The rotation is a cheap, GPU-composited CSS
   custom-property animation, paused under reduced motion. Reusable + opt-in. */
import type { ReactNode } from "react";
import { INTERACTION_CONFIG } from "../config";
import { useInteraction } from "../context";

export interface EnergyBorderProps {
  children: ReactNode;
  /** Continuously animate (true) or only glow on hover via CSS (false). */
  active?: boolean;
  radius?: number;
  className?: string;
}

export function EnergyBorder({ children, active = false, radius, className }: EnergyBorderProps) {
  const { reducedMotion, quality } = useInteraction();
  const animate = active && !reducedMotion && quality !== "off";

  return (
    <div
      className={`nxi-energy-border ${animate ? "is-active" : ""} ${className ?? ""}`}
      style={{
        borderRadius: radius,
        // duration is data, not hardcoded in CSS
        ["--nxi-energy-dur" as string]: `${INTERACTION_CONFIG.energy.borderDurationS}s`,
      }}
    >
      <div className="nxi-energy-border-inner" style={{ borderRadius: radius }}>
        {children}
      </div>
    </div>
  );
}
