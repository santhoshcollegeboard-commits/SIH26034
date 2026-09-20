import React from 'react';

/**
 * Standard status badge for statutory compliance states.
 * Supports: PASS, FAIL, NOT_VERIFIABLE, NOT_APPLICABLE
 */
export default function StatusBadge({ status, size = 'md' }) {
  const iconSize = size === 'sm' ? 11 : 13;

  const renderIcon = (type) => {
    switch (type) {
      case 'PASS':
        return (
          <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        );
      case 'FAIL':
        return (
          <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        );
      case 'NOT_APPLICABLE':
        return (
          <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
        );
      case 'NOT_VERIFIABLE':
      default:
        return (
          <svg width={iconSize} height={iconSize} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
        );
    }
  };

  const configs = {
    PASS: {
      label: 'PASS',
      type: 'PASS',
      className: 'badge-pass',
      description: 'Statutory requirement verified',
    },
    FAIL: {
      label: 'FAIL',
      type: 'FAIL',
      className: 'badge-fail',
      description: 'Defect or non-compliance detected',
    },
    NOT_VERIFIABLE: {
      label: 'REVIEW',
      type: 'NOT_VERIFIABLE',
      className: 'badge-review',
      description: 'Uncertain or not legible on this view',
    },
    NOT_APPLICABLE: {
      label: 'N/A',
      type: 'NOT_APPLICABLE',
      className: 'badge-na',
      description: 'Exempt or not applicable',
    },
  };

  const config = configs[status] || configs.NOT_VERIFIABLE;

  return (
    <span className={`status-pill ${config.className} size-${size}`} title={config.description}>
      <span className="pill-icon">{renderIcon(config.type)}</span>
      <span className="pill-text">{config.label}</span>
    </span>
  );
}
