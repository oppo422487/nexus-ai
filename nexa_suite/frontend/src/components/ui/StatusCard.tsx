import type { ReactNode } from "react";
import { cx } from "./cx";

export type StatusTone = "ok" | "warn" | "info";

export type StatusCardProps = {
  tone?: StatusTone;
  title: ReactNode;
  children?: ReactNode;
  className?: string;
};

/**
 * StatusCard — a compact status row (LED dot + title + subtitle) used in the
 * rail. Token-driven via the `.nxos-status-*` system classes.
 */
export function StatusCard({ tone = "ok", title, children, className }: StatusCardProps) {
  const toneClass = tone === "warn" ? "warn" : "ok";
  return (
    <div className={cx("nx-side-card", "nxos-status-card", className)}>
      <span className={cx("nxos-status-dot", toneClass)} />
      <div className="nxos-status-text">
        <strong className={toneClass}>{title}</strong>
        {children != null && <span>{children}</span>}
      </div>
    </div>
  );
}
