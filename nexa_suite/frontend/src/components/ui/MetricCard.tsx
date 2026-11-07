import type { ReactNode } from "react";

import { GlassCard } from "./GlassCard";

type MetricCardProps = {
  title: string;
  value: string;
  subtitle?: string;
  status?: "success" | "warning" | "danger" | "neutral";
  icon?: ReactNode;
  className?: string;
};

const statusClasses = {
  success: "text-nexa-green",
  warning: "text-amber-300",
  danger: "text-nexa-red",
  neutral: "text-nexa-cyan",
};

export function MetricCard({
  title,
  value,
  subtitle,
  status = "neutral",
  icon,
  className = "",
}: MetricCardProps) {
  return (
    <GlassCard className={className}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm text-nexa-muted">{title}</p>
          <p className={`mt-2 text-2xl font-semibold ${statusClasses[status]}`}>
            {value}
          </p>
          {subtitle ? <p className="mt-1 text-sm text-nexa-muted">{subtitle}</p> : null}
        </div>
        {icon ? <div className="text-nexa-cyan">{icon}</div> : null}
      </div>
    </GlassCard>
  );
}
