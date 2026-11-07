import { Zap, Lock, BookOpen, Moon, Users, Briefcase } from "lucide-react";
import { RemindersPage } from "./RemindersPage";
import { PageHero } from "@/components/ui";

const TEMPLATE_PREVIEWS = [
  { icon: BookOpen, name: "Study Mode", text: "Focus workflow for study and deep work.", tag: "Preview" },
  { icon: Briefcase, name: "Work Pack", text: "Boost productivity with essential tools.", tag: "Preview" },
  { icon: Users, name: "Meeting Mode", text: "Prepare system for online meetings.", tag: "Preview" },
  { icon: Moon, name: "Night Mode", text: "Relax and reduce eye strain.", tag: "Preview" },
];

/**
 * Automations hub. Today the working automation primitive is the local
 * reminder/scheduler (confirmation-based). Multi-step workflow execution is
 * shown as preview templates only — it stays disabled until a future
 * permission-gated phase, and will never include hidden or auto-run actions.
 */
export function AutomationsPage() {
  return (
    <>
      <div className="nx-page">
        <PageHero
          icon={<Zap />}
          eyebrow="Automation"
          title={<>Automation <span>Builder</span></>}
          description="Reminders work today. Multi-step workflows are preview-only and confirmation-based by design."
          meta={
            <>
              <span className="nx-chip">Reminders: live</span>
              <span className="nx-chip warn">Workflows: preview only</span>
              <span className="nx-chip muted">No hidden automation, ever</span>
            </>
          }
        />

        <section className="nx-card">
          <div className="nx-card-head">
            <div className="nx-card-title"><Zap /> Automation Library</div>
          </div>
          <div className="nx-grid-4">
            {TEMPLATE_PREVIEWS.map((template) => {
              const Icon = template.icon;
              return (
                <div className="nx-tile" key={template.name} style={{ cursor: "default" }}>
                  <span className="nx-tile-icon" style={{ background: "rgba(99,102,241,0.14)", color: "#818cf8" }}>
                    <Icon />
                  </span>
                  <strong>{template.name}</strong>
                  <small>{template.text}</small>
                  <span className="nx-list-badge mid">{template.tag}</span>
                </div>
              );
            })}
          </div>
          <div className="nx-locked-note" style={{ marginTop: 14 }}>
            <Lock />
            <span>
              Workflow execution is <strong>not enabled yet</strong>. When it ships, every
              step will be whitelist-based, visible, and individually confirmed — no
              auto-run, no background execution, no shell commands.
            </span>
          </div>
        </section>

        <RemindersPage embedded />
      </div>
    </>
  );
}
