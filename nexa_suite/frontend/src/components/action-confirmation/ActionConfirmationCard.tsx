import type { FC } from "react";

export type ActionConfirmationCardProps = {
  title?: string;
  description?: string;
  intent: string;
  targetLabel?: string | null;
  targetValue?: string | null;
  riskLevel?: string;
  disabled?: boolean;
  loading?: boolean;
  resultMessage?: string | null;
  errorMessage?: string | null;
  onConfirm: () => void;
  onCancel?: () => void;
};

export const ActionConfirmationCard: FC<ActionConfirmationCardProps> = ({
  title = "Confirm Action",
  description = "Review this action before execution.",
  intent,
  targetLabel,
  targetValue,
  riskLevel,
  disabled = false,
  loading = false,
  resultMessage,
  errorMessage,
  onConfirm,
  onCancel,
}) => {
  return (
    <div className="action-confirmation-card">
      <div className="action-confirmation-header">
        <p className="eyebrow">{title}</p>
        <p className="action-confirmation-description">{description}</p>
      </div>

      <div className="action-confirmation-grid">
        <div className="action-confirmation-row">
          <span>Intent</span>
          <strong>{intent}</strong>
        </div>
        {targetLabel && (
          <div className="action-confirmation-row">
            <span>Target</span>
            <strong>{targetLabel}</strong>
          </div>
        )}
        {targetValue && (
          <div className="action-confirmation-row">
            <span>Value</span>
            <strong>{targetValue}</strong>
          </div>
        )}
        {riskLevel && (
          <div className="action-confirmation-row">
            <span>Risk level</span>
            <strong>{riskLevel}</strong>
          </div>
        )}
      </div>

      <div className="action-confirmation-note">
        Only whitelisted safe actions can run. Dangerous actions remain blocked.
      </div>

      <div className="action-confirmation-actions">
        <button
          type="button"
          className="action-confirmation-confirm"
          disabled={disabled || loading}
          onClick={onConfirm}
        >
          {loading ? "Running..." : "Confirm Action"}
        </button>
        {onCancel && (
          <button
            type="button"
            className="action-confirmation-cancel"
            disabled={loading}
            onClick={onCancel}
          >
            Cancel
          </button>
        )}
      </div>

      {resultMessage && (
        <div className="action-confirmation-result">{resultMessage}</div>
      )}
      {errorMessage && (
        <div className="action-confirmation-error">{errorMessage}</div>
      )}
    </div>
  );
};
