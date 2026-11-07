import type { ReactNode } from "react";
import { cx } from "./cx";
import { Surface, type SurfaceProps } from "./Surface";

export type CardProps = Omit<SurfaceProps, "title"> & {
  title?: ReactNode;
  icon?: ReactNode;
  action?: ReactNode;
  footer?: ReactNode;
};

/**
 * Card — a padded Surface with an optional header (icon + title + action) and
 * footer. Composes Surface, so all depth/colour comes from tokens.
 */
export function Card({
  title,
  icon,
  action,
  footer,
  padding = "md",
  children,
  className,
  ...rest
}: CardProps) {
  const hasHeader = title != null || action != null || icon != null;
  return (
    <Surface padding={padding} className={cx("nxui-card", className)} {...rest}>
      {hasHeader && (
        <div className="nxui-card-head">
          <div className="nxui-card-title">
            {icon}
            {title}
          </div>
          {action}
        </div>
      )}
      {children}
      {footer != null && <div className="nxui-card-foot">{footer}</div>}
    </Surface>
  );
}
