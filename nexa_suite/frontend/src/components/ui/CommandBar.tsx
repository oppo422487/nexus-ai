import { useState, type KeyboardEvent, type ReactNode } from "react";
import { Command, Search } from "lucide-react";
import { cx } from "./cx";

export type CommandBarProps = {
  placeholder?: string;
  /** Called with the trimmed text when the user presses Enter. */
  onSubmit: (text: string) => void;
  /** Controlled value (optional). If omitted, CommandBar manages its own. */
  value?: string;
  onChange?: (value: string) => void;
  shortcut?: ReactNode;
  className?: string;
};

/**
 * CommandBar — the primary "drive the OS" control. A search-styled field with a
 * keyboard-shortcut affordance. Submits the trimmed query on Enter and clears
 * (only when uncontrolled). Behaviour matches the previous inline top-bar input.
 */
export function CommandBar({
  placeholder = "Type a command or ask Nexa…",
  onSubmit,
  value,
  onChange,
  shortcut,
  className,
}: CommandBarProps) {
  const [internal, setInternal] = useState("");
  const isControlled = value !== undefined;
  const current = isControlled ? value : internal;

  const setValue = (next: string) => {
    if (!isControlled) setInternal(next);
    onChange?.(next);
  };

  const handleKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Enter" && current.trim()) {
      onSubmit(current.trim());
      if (!isControlled) setInternal("");
    }
  };

  return (
    <div className={cx("nx-search", "nxos-command-bar", className)}>
      <Search />
      <input
        value={current}
        onChange={(event) => setValue(event.target.value)}
        placeholder={placeholder}
        onKeyDown={handleKeyDown}
      />
      <kbd className="nxos-kbd">{shortcut ?? (<><Command size={11} /> K</>)}</kbd>
    </div>
  );
}
