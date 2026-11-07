import type { ReactNode } from "react";
import { cx } from "./cx";

export interface PageHeroProps {
  /** Small glowing icon badge (e.g. a lucide icon). */
  icon?: ReactNode;
  /** Uppercase kicker above the title. */
  eyebrow?: string;
  title: ReactNode;
  description?: ReactNode;
  /** Right-aligned actions (buttons, toggles). */
  actions?: ReactNode;
  /** Status chips / meta shown under the description. */
  meta?: ReactNode;
  className?: string;
}

/**
 * PageHero — the unified premium page header for the AI OS. Every page opens
 * with the same hierarchy (icon · eyebrow · title · description · meta/actions)
 * so the whole product reads as one system. Presentational only.
 */
export function PageHero({ icon, eyebrow, title, description, actions, meta, className }: PageHeroProps) {
  return (
    <header className={cx("nxos-hero", className)}>
      <span className="nxos-hero-glow" aria-hidden="true" />
      <div className="nxos-hero-lead">
        {icon && <span className="nxos-hero-icon">{icon}</span>}
        <div className="nxos-hero-text">
          {eyebrow && <p className="nxos-hero-eyebrow">{eyebrow}</p>}
          <h1 className="nxos-hero-title">{title}</h1>
          {description && <p className="nxos-hero-desc">{description}</p>}
          {meta && <div className="nxos-hero-meta">{meta}</div>}
        </div>
      </div>
      {actions && <div className="nxos-hero-actions">{actions}</div>}
    </header>
  );
}
