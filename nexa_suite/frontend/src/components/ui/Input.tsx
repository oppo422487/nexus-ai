import type { InputHTMLAttributes, ReactNode } from "react";
import { cx } from "./cx";

export type InputProps = InputHTMLAttributes<HTMLInputElement> & {
  /** Optional leading adornment (e.g. an icon); wraps input in a field shell. */
  leftIcon?: ReactNode;
};

/**
 * Input — token-driven text field over the `.nx-input` system. When `leftIcon`
 * is provided the input is wrapped in a `.nx-search`-style field shell.
 */
export function Input({ leftIcon, className, ...rest }: InputProps) {
  if (leftIcon) {
    return (
      <div className={cx("nx-search", className)}>
        {leftIcon}
        <input {...rest} />
      </div>
    );
  }
  return <input className={cx("nx-input", className)} {...rest} />;
}
