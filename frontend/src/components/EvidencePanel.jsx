import React from 'react';

function AlertTriangleIcon({ className = '', size = 14 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function PinIcon({ className = '', size = 12 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="12" y1="17" x2="12" y2="22" />
      <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.89A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.89A2 2 0 0 0 5 15.24Z" />
    </svg>
  );
}

/**
 * Detailed audit view for an individual statutory rule evaluation.
 * Renders verified extracted text, legal requirement, and candidate provenance.
 */
export default function EvidencePanel({ evaluation, extractedField }) {
  if (!evaluation) return null;

  const confidence = extractedField?.confidence ?? null;

  return (
    <div className="evidence-panel">
      {/* Statutory Section */}
      <div className="evidence-row">
        <span className="evidence-label">Legal Reference</span>
        <span className="evidence-value stat-ref">{evaluation.rule_reference}</span>
      </div>

      {/* Statutory Expected Condition */}
      <div className="evidence-row">
        <span className="evidence-label">Mandatory Condition</span>
        <span className="evidence-value text-slate">{evaluation.expected_condition}</span>
      </div>

      {/* Extracted Declaration Evidence */}
      <div className="evidence-row highlight-box">
        <span className="evidence-label">Extracted Evidence</span>
        {evaluation.extracted_value ? (
          <div className="extracted-quote">
            <span className="quote-mark">“</span>
            <span className="quote-content">{evaluation.extracted_value}</span>
            <span className="quote-mark">”</span>
          </div>
        ) : (
          <span className="no-evidence-text">
            No declaration legible or detected on this packaging angle
          </span>
        )}
      </div>

      {/* Conflict Alert Box if present */}
      {extractedField?.status === 'conflict' && (
        <div className="evidence-row conflict-alert-row">
          <span className="evidence-label text-amber">Cross-Panel Conflict</span>
          <div className="conflict-box">
            <AlertTriangleIcon size={16} className="conflict-icon-svg" />
            <div className="conflict-body">
              <strong>Contradictory values across panels</strong>
              <p>{extractedField.conflict_details || extractedField.value}</p>
            </div>
          </div>
        </div>
      )}

      {/* Source Panel Provenance */}
      {(evaluation.source_region?.panel_label || extractedField?.source_panel_label) && (
        <div className="evidence-row">
          <span className="evidence-label">Source Panel</span>
          <span className="panel-provenance-tag">
            <PinIcon size={12} className="provenance-pin-svg" />
            <span>{evaluation.source_region?.panel_label || extractedField?.source_panel_label}</span>
            {extractedField?.source_image_index !== undefined &&
              extractedField?.source_image_index !== null && (
                <span className="image-idx-text">
                  {' '}(Image #{extractedField.source_image_index + 1})
                </span>
              )}
          </span>
        </div>
      )}

      {/* Multi-Panel Competing Candidates */}
      {extractedField?.all_candidates && extractedField.all_candidates.length > 1 && (
        <div className="evidence-row candidate-list-box">
          <span className="evidence-label">Candidates Across Panels</span>
          <div className="candidates-list">
            {extractedField.all_candidates.map((cand, i) => (
              <div key={i} className="candidate-row">
                <span className="cand-panel-badge">
                  {cand.source_panel_label || `Panel ${cand.source_image_index + 1}`}
                </span>
                <span className="cand-val">“{cand.value}”</span>
                {cand.confidence !== null && cand.confidence !== undefined && (
                  <span className="cand-conf">{Math.round(cand.confidence * 100)}%</span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Confidence Score if available */}
      {confidence !== null && (
        <div className="evidence-row">
          <span className="evidence-label">OCR Confidence</span>
          <div className="confidence-indicator">
            <div className="confidence-track">
              <div
                className="confidence-fill"
                style={{
                  width: `${Math.round(confidence * 100)}%`,
                  backgroundColor:
                    confidence >= 0.85
                      ? 'var(--color-emerald-600, #059669)'
                      : confidence >= 0.65
                      ? 'var(--color-amber-600, #d97706)'
                      : 'var(--color-red-600, #dc2626)',
                }}
              />
            </div>
            <span className="confidence-pct">{Math.round(confidence * 100)}%</span>
          </div>
        </div>
      )}

      {/* Specific Evaluator Finding Message */}
      <div className="evidence-row finding-note">
        <span className="evidence-label">Inspector Finding</span>
        <p className="finding-text">{evaluation.message}</p>
      </div>
    </div>
  );
}
