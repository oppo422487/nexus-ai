type StatusBadgeProps = {
  label: string;
  status?: "online" | "offline" | "pending" | "success" | "warning" | "danger";
  className?: string;
};

const statusStyles = {
  online: "bg-nexa-green",
  offline: "bg-nexa-muted",
  pending: "bg-nexa-blue",
  success: "bg-nexa-green",
  warning: "bg-amber-400",
  danger: "bg-nexa-red",
};

export function StatusBadge({
  label,
  status = "pending",
  className = "",
}: StatusBadgeProps) {
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-3 py-1 text-sm text-nexa-text ${className}`}
    >
      <span className={`h-2 w-2 rounded-full ${statusStyles[status]}`} />
      {label}
    </span>
  );
}
