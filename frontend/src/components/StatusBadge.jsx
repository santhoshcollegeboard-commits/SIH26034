import React from 'react';

/**
 * Standard status badge for statutory compliance states.
 * Supports: PASS, FAIL, NOT_VERIFIABLE, NOT_APPLICABLE
 */
export default function StatusBadge({ status, size = 'md' }) {
  const configs = {
    PASS: {
      label: 'PASS',
      icon: '✓',
      className: 'badge-pass',
      description: 'Statutory requirement verified',
    },
    FAIL: {
      label: 'FAIL',
      icon: '✕',
      className: 'badge-fail',
      description: 'Defect or non-compliance detected',
    },
    NOT_VERIFIABLE: {
      label: 'REVIEW',
      icon: '?',
      className: 'badge-review',
      description: 'Uncertain or not legible on this view',
    },
    NOT_APPLICABLE: {
      label: 'N/A',
      icon: '—',
      className: 'badge-na',
      description: 'Exempt or not applicable',
    },
  };

  const config = configs[status] || configs.NOT_VERIFIABLE;

  return (
    <span className={`status-pill ${config.className} size-${size}`} title={config.description}>
      <span className="pill-icon">{config.icon}</span>
      <span className="pill-text">{config.label}</span>
    </span>
  );
}
