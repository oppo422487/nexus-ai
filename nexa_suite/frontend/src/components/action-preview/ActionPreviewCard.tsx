import type { FC } from "react";
import type { ActionPreview } from "@/lib";
import { getActionPreviewStatusLabel } from "@/lib";

type ActionPreviewCardProps = {
  preview: ActionPreview;
  onEdit?: () => void;
  onCancel?: () => void;
};

export const ActionPreviewCard: FC<ActionPreviewCardProps> = ({
  preview,
  onEdit,
  onCancel,
}) => {
  const statusLabel = getActionPreviewStatusLabel(preview.status);
  const isBlocked = preview.status === "blocked";
  const isConfirmationRequired =
    preview.status === "requires_confirmation" ||
    preview.status === "sensitive_warning";
  const secondaryAction = onEdit ?? onCancel;

  return (
    <article className="action-preview-card">
      <header className="action-preview-header">
        <span className={`action-preview-badge ${preview.status}`}>{statusLabel}</span>
        <div>
          <h3 className="action-preview-title">{preview.title}</h3>
          <p className="action-preview-description">{preview.description}</p>
        </div>
      </header>

      <div className="action-preview-meta-grid">
        <div className="action-preview-meta-row">
          <span>Intent</span>
          <strong>{preview.intent}</strong>
        </div>
        <div className="action-preview-meta-row">
          <span>Risk level</span>
          <strong>{preview.riskLevel}</strong>
        </div>
        <div className="action-preview-meta-row">
          <span>Execution</span>
          <strong>Execution disabled in this phase</strong>
        </div>
      </div>

      <div className="action-preview-steps">
        <p className="eyebrow">Preview steps</p>
        {preview.previewSteps.map((step, index) => (
          <div className="action-preview-step" key={step + index}>
            <strong>{index + 1}.</strong>
            <span>{step}</span>
          </div>
        ))}
      </div>

      {preview.warningMessage ? (
        <div className="action-preview-warning">{preview.warningMessage}</div>
      ) : null}

      {preview.blockedReason ? (
        <div className="action-preview-blocked">{preview.blockedReason}</div>
      ) : null}

      <div className="action-preview-actions">
        <button className="action-preview-primary" type="button" disabled>
          {preview.primaryActionLabel}
        </button>
        <button
          className="action-preview-secondary"
          type="button"
          onClick={secondaryAction}
          disabled={!secondaryAction}
        >
          {preview.secondaryActionLabel}
        </button>
      </div>

      <div className="action-preview-disabled-note">
        {isBlocked
          ? "This action is blocked and only available for review or rewrite."
          : isConfirmationRequired
          ? "This preview requires confirmation before execution in a later phase."
          : "This card is preview-only and will not execute any action."}
      </div>
    </article>
  );
};
