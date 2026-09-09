import React from 'react';

/**
 * Clean mobile error banner with user-friendly error messages and retry action.
 */
export default function ErrorBanner({ error, onDismiss, onRetry }) {
  if (!error) return null;

  return (
    <div className="error-toast" role="alert" id="error-banner">
      <div className="error-icon-col">⚠️</div>
      <div className="error-text-col">
        <strong className="error-heading">Inspection Error</strong>
        <p className="error-message">{error}</p>
      </div>
      <div className="error-actions-col">
        {onRetry && (
          <button type="button" className="btn-retry" onClick={onRetry}>
            Retry
          </button>
        )}
        {onDismiss && (
          <button
            type="button"
            className="btn-dismiss"
            onClick={onDismiss}
            aria-label="Dismiss error"
          >
            ✕
          </button>
        )}
      </div>
    </div>
  );
}
