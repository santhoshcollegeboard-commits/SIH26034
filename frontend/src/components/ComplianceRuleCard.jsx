import React, { useState } from 'react';
import StatusBadge from './StatusBadge';
import EvidencePanel from './EvidencePanel';

function ChevronUpIcon({ className = '', size = 12 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

function ChevronDownIcon({ className = '', size = 12 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

/**
 * Card rendering a single statutory rule evaluation.
 * Tap anywhere on the card header to expand full evidence details.
 */
export default function ComplianceRuleCard({ evaluation, extractedField }) {
  const [expanded, setExpanded] = useState(false);

  const statusClassMap = {
    PASS: 'card-pass',
    FAIL: 'card-fail',
    NOT_VERIFIABLE: 'card-review',
    NOT_APPLICABLE: 'card-na',
  };

  const statusBorder = statusClassMap[evaluation.status] || 'card-review';

  return (
    <article className={`rule-card ${statusBorder} ${expanded ? 'is-expanded' : ''}`}>
      <button
        type="button"
        className="rule-card-header"
        onClick={() => setExpanded((prev) => !prev)}
        aria-expanded={expanded}
        aria-label={`${evaluation.rule_name} status ${evaluation.status}. Click to ${expanded ? 'collapse' : 'expand'} evidence details.`}
      >
        <div className="rule-info-primary">
          <div className="rule-title-row">
            <h4 className="rule-title">{evaluation.rule_name}</h4>
          </div>
          <span className="rule-ref-sub">{evaluation.rule_reference.split(',')[0]}</span>
        </div>

        <div className="rule-action-col">
          <StatusBadge status={evaluation.status} size="sm" />
          <span className="chevron-icon" aria-hidden="true">
            {expanded ? <ChevronUpIcon size={12} /> : <ChevronDownIcon size={12} />}
          </span>
        </div>
      </button>

      {/* Finding snippet visible when collapsed */}
      {!expanded && evaluation.message && (
        <div className="rule-summary-snippet" onClick={() => setExpanded(true)}>
          <p className="snippet-text">{evaluation.message}</p>
        </div>
      )}

      {/* Detailed evidence view when expanded */}
      {expanded && (
        <div className="rule-card-body">
          <EvidencePanel evaluation={evaluation} extractedField={extractedField} />
        </div>
      )}
    </article>
  );
}
