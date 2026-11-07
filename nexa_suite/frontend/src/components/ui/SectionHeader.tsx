import type { ReactNode } from "react";

type SectionHeaderProps = {
  eyebrow?: string;
  title: string;
  subtitle?: string;
  action?: ReactNode;
};

export function SectionHeader({
  eyebrow,
  title,
  subtitle,
  action,
}: SectionHeaderProps) {
  return (
    <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
      <div>
        {eyebrow ? (
          <p className="mb-2 text-xs font-semibold uppercase tracking-[0.24em] text-nexa-cyan">
            {eyebrow}
          </p>
        ) : null}
        <h1 className="nexa-gradient-text text-3xl font-bold md:text-4xl">{title}</h1>
        {subtitle ? <p className="mt-2 text-nexa-muted">{subtitle}</p> : null}
      </div>
      {action}
    </div>
  );
}
