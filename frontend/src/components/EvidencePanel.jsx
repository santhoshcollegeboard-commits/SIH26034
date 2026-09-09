import React from 'react';

/**
 * Detailed audit view for an individual statutory rule evaluation.
 * Renders verified extracted text, legal requirement, and bounding box coordinates.
 */
export default function EvidencePanel({ evaluation, extractedField }) {
  if (!evaluation) return null;

  const hasRegion = evaluation.source_region && (
    evaluation.source_region.width > 0 || evaluation.source_region.height > 0
  );

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
                      ? 'var(--color-emerald-600)'
                      : confidence >= 0.65
                      ? 'var(--color-amber-600)'
                      : 'var(--color-red-600)',
                }}
              />
            </div>
            <span className="confidence-pct">{Math.round(confidence * 100)}%</span>
          </div>
        </div>
      )}

      {/* Bounding Box Source Region */}
      {hasRegion && (
        <div className="evidence-row">
          <span className="evidence-label">Image Region (PDP)</span>
          <span className="coords-chip">
            x: {evaluation.source_region.x}, y: {evaluation.source_region.y} &bull;{' '}
            {evaluation.source_region.width}&times;{evaluation.source_region.height}px
          </span>
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
