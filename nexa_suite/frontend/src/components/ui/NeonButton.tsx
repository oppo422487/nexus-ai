import type { ReactNode } from "react";

type NeonButtonProps = {
  children: ReactNode;
  variant?: "primary" | "secondary" | "danger" | "ghost";
  size?: "sm" | "md" | "lg";
  className?: string;
  disabled?: boolean;
  onClick?: () => void;
};

const variantClasses = {
  primary:
    "bg-gradient-to-r from-nexa-cyan to-nexa-purple text-slate-950 shadow-neon-cyan hover:brightness-110",
  secondary:
    "nexa-glass nexa-border text-nexa-text hover:border-nexa-cyan/60",
  danger:
    "border border-nexa-red/70 bg-nexa-red/10 text-nexa-text shadow-[0_0_20px_rgba(239,68,68,0.22)] hover:bg-nexa-red/20",
  ghost: "bg-transparent text-nexa-muted hover:bg-white/5 hover:text-nexa-text",
};

const sizeClasses = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-5 py-3 text-base",
};

export function NeonButton({
  children,
  variant = "primary",
  size = "md",
  className = "",
  disabled = false,
  onClick,
}: NeonButtonProps) {
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={`rounded-2xl font-semibold transition duration-200 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-nexa-cyan focus-visible:ring-offset-2 focus-visible:ring-offset-nexa-bg disabled:cursor-not-allowed disabled:opacity-50 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {children}
    </button>
  );
}
