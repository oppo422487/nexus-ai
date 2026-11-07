import type { ReactNode } from "react";
import { cx } from "./cx";

export type SidebarGroupProps = {
  label: ReactNode;
  children: ReactNode;
  className?: string;
};

/**
 * SidebarGroup — a labelled cluster of navigation items. Presentational grouping
 * only; the items and their behaviour are provided by the caller.
 */
export function SidebarGroup({ label, children, className }: SidebarGroupProps) {
  return (
    <div className={cx("nxos-nav-group", className)}>
      <p className="nxos-nav-label">{label}</p>
      {children}
    </div>
  );
}
