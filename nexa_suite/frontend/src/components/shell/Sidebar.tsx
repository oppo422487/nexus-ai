import {
  Home,
  Terminal,
  Mic,
  Zap,
  FolderOpen,
  LayoutGrid,
  Globe,
  Clock,
  Shield,
  Settings,
  BrainCircuit,
} from "lucide-react";
import { SidebarGroup, StatusCard } from "@/components/ui";

export type NavId =
  | "dashboard"
  | "commands"
  | "voice"
  | "automations"
  | "files"
  | "launcher"
  | "web"
  | "history"
  | "security"
  | "settings"
  | "skills";

type NavItem = { id: NavId; label: string; icon: typeof Home; hint: string };

/**
 * Navigation grouped by intent so the shell reads like an operating system:
 * where you work, what the assistant can reach, and how you govern it. The ids,
 * order within groups, and selection behaviour are unchanged — this is purely a
 * presentational hierarchy over the existing routes.
 */
const NAV_GROUPS: Array<{ label: string; items: NavItem[] }> = [
  {
    label: "কর্মক্ষেত্র",
    items: [
      { id: "dashboard", label: "ড্যাশবোর্ড", icon: Home, hint: "Command center" },
      { id: "commands", label: "কমান্ড", icon: Terminal, hint: "Intent lab" },
      { id: "voice", label: "ভয়েস", icon: Mic, hint: "Always listening" },
      { id: "automations", label: "অটোমেশন", icon: Zap, hint: "Workflows" },
      { id: "skills", label: "দক্ষতা", icon: BrainCircuit, hint: "20 capabilities" },
    ],
  },
  {
    label: "তথ্য ও সহায়তা",
    items: [
      { id: "files", label: "File Organizer", icon: FolderOpen, hint: "Safe search" },
      { id: "launcher", label: "App Launcher", icon: LayoutGrid, hint: "Apps & sites" },
      { id: "web", label: "Web Search", icon: Globe, hint: "Safe answers" },
    ],
  },
  {
    label: "সিস্টেম",
    items: [
      { id: "history", label: "ইতিহাস", icon: Clock, hint: "Audit trail" },
      { id: "security", label: "নিরাপত্তা", icon: Shield, hint: "Permissions" },
      { id: "settings", label: "সেটিংস", icon: Settings, hint: "Preferences" },
    ],
  },
];

export function Sidebar({
  active,
  backendConnected,
  onSelect,
}: {
  active: NavId;
  backendConnected: boolean;
  onSelect: (id: NavId) => void;
}) {
  return (
    <aside className="nx-sidebar nxos-rail">
      <div className="nx-brand nxos-brand">
        <div className="nx-brand-orb">N</div>
        <div className="nxos-brand-text">
          <h1>
            Nexa <span>AI</span>
          </h1>
          <p className="nxos-brand-tag">Operating System</p>
        </div>
      </div>

      <nav className="nx-nav nxos-nav">
        {NAV_GROUPS.map((group) => (
          <SidebarGroup key={group.label} label={group.label}>
            {group.items.map((item) => {
              const Icon = item.icon;
              const isActive = active === item.id;
              return (
                <button
                  key={item.id}
                  type="button"
                  className={isActive ? "nx-nav-item nxos-nav-item active" : "nx-nav-item nxos-nav-item"}
                  onClick={() => onSelect(item.id)}
                  aria-current={isActive ? "page" : undefined}
                >
                  <span className="nxos-nav-icon">
                    <Icon />
                  </span>
                  <span className="nxos-nav-text">
                    <span className="nxos-nav-name">{item.label}</span>
                    <span className="nxos-nav-hint">{item.hint}</span>
                  </span>
                </button>
              );
            })}
          </SidebarGroup>
        ))}
      </nav>

      <div className="nxos-rail-status">
        <StatusCard tone={backendConnected ? "ok" : "warn"} title={backendConnected ? "Core online" : "Core offline"}>
          {backendConnected
            ? "FastAPI reachable · 127.0.0.1:8766"
            : "Run python run_backend.py to enable actions"}
        </StatusCard>

        <StatusCard tone="ok" title="Local-first">
          No cloud sync · whitelist + confirmation
        </StatusCard>
      </div>
    </aside>
  );
}
