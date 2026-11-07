/* LiquidGlass — wraps a surface so a soft specular highlight follows the
   pointer across it, giving glass a liquid, physical feel. The highlight is a
   single gradient positioned by CSS variables updated only while hovered
   (cheap; no per-frame work when idle). Reusable + opt-in. */
import { useCallback, useRef, type ReactNode } from "react";
import { useInteraction } from "../context";

export interface LiquidGlassProps {
  children: ReactNode;
  className?: string;
}

export function LiquidGlass({ children, className }: LiquidGlassProps) {
  const { reducedMotion, coarsePointer } = useInteraction();
  const ref = useRef<HTMLDivElement>(null);
  const enabled = !reducedMotion && !coarsePointer;

  const onPointerMove = useCallback(
    (event: React.PointerEvent<HTMLDivElement>) => {
      if (!enabled || !ref.current) return;
      const rect = ref.current.getBoundingClientRect();
      const px = ((event.clientX - rect.left) / rect.width) * 100;
      const py = ((event.clientY - rect.top) / rect.height) * 100;
      ref.current.style.setProperty("--nxi-lx", `${px}%`);
      ref.current.style.setProperty("--nxi-ly", `${py}%`);
    },
    [enabled],
  );

  return (
    <div
      ref={ref}
      className={`nxi-liquid ${className ?? ""}`}
      onPointerMove={onPointerMove}
    >
      <span className="nxi-liquid-sheen" aria-hidden="true" />
      {children}
    </div>
  );
}
