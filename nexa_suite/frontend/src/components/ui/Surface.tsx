import type { HTMLAttributes, ReactNode } from "react";
import { cx } from "./cx";

export type SurfaceVariant = "glass" | "inset" | "plain";
export type SurfacePadding = "none" | "sm" | "md" | "lg";

export type SurfaceProps = HTMLAttributes<HTMLDivElement> & {
  variant?: SurfaceVariant;
  padding?: SurfacePadding;
  /** Adds a subtle hover lift for clickable surfaces. */
  interactive?: boolean;
  /** Stronger accent halo (hero surfaces). */
  raised?: boolean;
  children?: ReactNode;
};

const variantClass: Record<SurfaceVariant, string> = {
  glass: "",
  inset: "nxui-surface--inset",
  plain: "nxui-surface--plain",
};

const paddingClass: Record<SurfacePadding, string> = {
  none: "nxui-p-none",
  sm: "nxui-p-sm",
  md: "nxui-p-md",
  lg: "nxui-p-lg",
};

/**
 * Surface — the base token-driven panel. All elevated regions build on this so
 * radius, border, glass fill, and shadow come from tokens, never raw values.
 */
export function Surface({
  variant = "glass",
  padding = "none",
  interactive = false,
  raised = false,
  className,
  children,
  ...rest
}: SurfaceProps) {
  return (
    <div
      className={cx(
        "nxui-surface",
        variantClass[variant],
        paddingClass[padding],
        interactive && "nxui-surface--interactive",
        raised && "nxui-surface--raised",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}
