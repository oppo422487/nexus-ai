/* EnergyLines — draws faint animated links between related cards in a hub-and-
   spoke pattern. Opt-in and non-invasive: it connects any elements tagged
   `data-energy-node="<group>"`, and renders nothing if none exist. Positions
   recompute on resize/scroll (rAF-throttled). Purely decorative overlay. */
import { useEffect, useRef, useState } from "react";
import { INTERACTION_CONFIG } from "../config";
import { useInteraction } from "../context";

interface Line {
  x1: number;
  y1: number;
  x2: number;
  y2: number;
  key: string;
}

export interface EnergyLinesProps {
  group: string;
  className?: string;
}

export function EnergyLines({ group, className }: EnergyLinesProps) {
  const { reducedMotion, quality } = useInteraction();
  const [lines, setLines] = useState<Line[]>([]);
  const raf = useRef(0);

  useEffect(() => {
    if (quality === "off") {
      setLines([]);
      return;
    }
    const measure = () => {
      raf.current = 0;
      const nodes = Array.from(
        document.querySelectorAll<HTMLElement>(`[data-energy-node="${group}"]`),
      );
      if (nodes.length < 2) {
        setLines([]);
        return;
      }
      const centers = nodes.map((n) => {
        const r = n.getBoundingClientRect();
        return { x: r.left + r.width / 2, y: r.top + r.height / 2 };
      });
      const hub = centers.reduce(
        (acc, c) => ({ x: acc.x + c.x / centers.length, y: acc.y + c.y / centers.length }),
        { x: 0, y: 0 },
      );
      setLines(
        centers.map((c, i) => ({ x1: hub.x, y1: hub.y, x2: c.x, y2: c.y, key: `${group}-${i}` })),
      );
    };
    const schedule = () => {
      if (!raf.current) raf.current = requestAnimationFrame(measure);
    };
    schedule();
    window.addEventListener("resize", schedule);
    window.addEventListener("scroll", schedule, true);
    const ro = new ResizeObserver(schedule);
    ro.observe(document.body);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      window.removeEventListener("resize", schedule);
      window.removeEventListener("scroll", schedule, true);
      ro.disconnect();
    };
  }, [group, quality]);

  if (lines.length === 0) return null;

  return (
    <svg className={`nxi-energy-lines ${className ?? ""}`} aria-hidden="true">
      <defs>
        <linearGradient id={`nxi-energy-grad-${group}`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor="var(--nx-cyan)" />
          <stop offset="100%" stopColor="var(--nx-violet)" />
        </linearGradient>
      </defs>
      {lines.map((l) => (
        <line
          key={l.key}
          x1={l.x1}
          y1={l.y1}
          x2={l.x2}
          y2={l.y2}
          stroke={`url(#nxi-energy-grad-${group})`}
          strokeWidth={1}
          strokeOpacity={INTERACTION_CONFIG.energy.lineOpacity}
          strokeDasharray={reducedMotion ? undefined : "4 8"}
          className={reducedMotion ? undefined : "nxi-energy-line-flow"}
        />
      ))}
    </svg>
  );
}
