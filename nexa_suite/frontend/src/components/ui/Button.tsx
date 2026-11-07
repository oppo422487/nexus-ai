import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cx } from "./cx";

export type ButtonVariant = "primary" | "ghost" | "danger" | "amber";

export type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  children?: ReactNode;
};

const variantClass: Record<ButtonVariant, string> = {
  primary: "",
  ghost: "ghost",
  danger: "danger",
  amber: "amber",
};

/**
 * Button — typed wrapper over the token-driven `.nx-btn` system so features use
 * a primitive instead of raw class strings. Default type is "button" to avoid
 * accidental form submits.
 */
export function Button({
  variant = "primary",
  leftIcon,
  rightIcon,
  type = "button",
  className,
  children,
  ...rest
}: ButtonProps) {
  return (
    <button type={type} className={cx("nx-btn", variantClass[variant], className)} {...rest}>
      {leftIcon}
      {children}
      {rightIcon}
    </button>
  );
}
