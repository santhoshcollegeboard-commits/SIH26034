import { useState } from 'react';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import {
  FIELD_LABELS,
  formatConfidence,
  formatMissingValue,
  formatSourceRegion,
} from '../services/formatters';

export default function ReviewSection({
  reviewItems,
  imageSrc,
  onSubmitReview,
  isSubmitting,
}) {
  // State for corrections keyed by field_name: { action: 'confirm'|'correct'|'mark_unassessable', correctedValue: '', reviewerNotes: '' }
  const [resolutions, setResolutions] = useState(() => {
    const initial = {};
    (reviewItems || []).forEach((item) => {
      initial[item.field_name] = {
        action: 'confirm',
        correctedValue: item.current_value || '',
        reviewerNotes: '',
      };
    });
    return initial;
  });

  const [inspectingBbox, setInspectingBbox] = useState(null);

  if (!reviewItems || reviewItems.length === 0) {
    return null;
  }

  function handleActionChange(fieldName, action) {
    setResolutions((prev) => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        action,
      },
    }));
  }

  function handleValueChange(fieldName, val) {
    setResolutions((prev) => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        correctedValue: val,
      },
    }));
  }

  function handleNotesChange(fieldName, notes) {
    setResolutions((prev) => ({
      ...prev,
      [fieldName]: {
        ...prev[fieldName],
        reviewerNotes: notes,
      },
    }));
  }

  function handleSubmit() {
    const corrections = reviewItems.map((item) => {
      const res = resolutions[item.field_name] || {
        action: 'confirm',
        correctedValue: item.current_value || '',
        reviewerNotes: '',
      };
      return {
        field_name: item.field_name,
        action: res.action,
        corrected_value: res.action === 'correct' ? res.correctedValue : null,
        reviewer_notes: res.reviewerNotes ? res.reviewerNotes.trim() : null,
      };
    });

    onSubmitReview(corrections);
  }

  return (
    <div className="card review-card" id="review-required-section">
      <div className="card-header">
        <div className="card-header-title-group">
          <span className="card-icon">🔍</span>
          <div>
            <h3 className="card-title">Human Review Required</h3>
            <span className="card-subtitle">
              Resolve declaration uncertainties before statutory compliance can be finalized
            </span>
          </div>
        </div>
        <div className="card-header-badge">
          <span className="status-badge badge-review">
            {reviewItems.length} {reviewItems.length === 1 ? 'Item' : 'Items'} Pending
          </span>
        </div>
      </div>

      <div className="review-items-list">
        {reviewItems.map((item) => {
          const fieldName = item.field_name;
          const label = FIELD_LABELS[fieldName] || fieldName.replace(/_/g, ' ');
          const currentRes = resolutions[fieldName] || {
            action: 'confirm',
            correctedValue: item.current_value || '',
            reviewerNotes: '',
          };
          const hasCoords = item.source_region && item.source_region.x !== undefined;

          return (
            <div key={fieldName} className="review-item-card">
              <div className="review-item-header">
                <div className="review-item-title-group">
                  <h4 className="review-field-title">{label}</h4>
                  <span className="review-field-key font-mono">{fieldName}</span>
                </div>
                <div className="review-item-meta">
                  <span className="meta-tag">Confidence: {formatConfidence(item.confidence)}</span>
                  {item.rule_id && <span className="meta-tag font-mono">{item.rule_id}</span>}
                </div>
              </div>

              {item.uncertainty_reason && (
                <div className="review-reason-box">
                  <span className="reason-label">Reason for Uncertainty:</span>{' '}
                  <span className="reason-text">{item.uncertainty_reason}</span>
                </div>
              )}

              {item.reviewer_instruction && (
                <div className="review-instruction-box">
                  <span className="instruction-icon">ℹ</span>
                  <span>{item.reviewer_instruction}</span>
                </div>
              )}

              <div className="review-evidence-row">
                <div className="evidence-col">
                  <span className="col-label">Extracted AI Value:</span>
                  <div className="evidence-val-box font-medium font-mono">
                    {formatMissingValue(item.current_value)}
                  </div>
                </div>

                <div className="evidence-col">
                  <span className="col-label">Source Bounding Box:</span>
                  <div className="evidence-val-box font-mono flex-between">
                    <span>{formatSourceRegion(item.source_region)}</span>
                    {hasCoords && (
                      <button
                        className="btn btn-xs btn-outline"
                        onClick={() =>
                          setInspectingBbox({
                            fieldName,
                            label,
                            sourceRegion: item.source_region,
                            confidence: formatConfidence(item.confidence),
                          })
                        }
                      >
                        Inspect Image
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Reviewer Action Radio / Buttons */}
              <div className="review-actions-panel">
                <span className="action-panel-label">Reviewer Resolution:</span>
                <div className="action-btn-group">
                  <button
                    type="button"
                    className={`btn-toggle ${currentRes.action === 'confirm' ? 'active active-confirm' : ''}`}
                    onClick={() => handleActionChange(fieldName, 'confirm')}
                  >
                    ✓ Confirm Value
                  </button>
                  <button
                    type="button"
                    className={`btn-toggle ${currentRes.action === 'correct' ? 'active active-correct' : ''}`}
                    onClick={() => handleActionChange(fieldName, 'correct')}
                  >
                    ✎ Correct Value
                  </button>
                  <button
                    type="button"
                    className={`btn-toggle ${currentRes.action === 'mark_unassessable' ? 'active active-unassessable' : ''}`}
                    onClick={() => handleActionChange(fieldName, 'mark_unassessable')}
                  >
                    ○ Mark Unassessable
                  </button>
                </div>

                {/* Correction Input if Correct selected */}
                {currentRes.action === 'correct' && (
                  <div className="correction-input-group mt-3">
                    <label className="input-label">Verified Correct Value:</label>
                    <input
                      type="text"
                      className="form-control font-mono"
                      value={currentRes.correctedValue}
                      onChange={(e) => handleValueChange(fieldName, e.target.value)}
                      placeholder={`Enter verified ${label}`}
                      autoFocus
                    />
                  </div>
                )}

                {/* Optional Reviewer Notes */}
                <div className="reviewer-notes-group mt-2">
                  <label className="input-label">Reviewer Rationale / Notes (optional):</label>
                  <input
                    type="text"
                    className="form-control form-control-sm"
                    value={currentRes.reviewerNotes}
                    onChange={(e) => handleNotesChange(fieldName, e.target.value)}
                    placeholder="e.g. Confirmed text from physical commodity packaging"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="card-footer review-footer">
        <div className="footer-notice text-muted">
          <span>AI extracts → Rules decide → Humans resolve uncertainty → Rules decide again</span>
        </div>
        <button
          className="btn btn-primary"
          onClick={handleSubmit}
          disabled={isSubmitting}
          id="btn-submit-review"
        >
          {isSubmitting ? (
            <span className="btn-loading">
              <span className="spinner" /> Re-evaluating Deterministically...
            </span>
          ) : (
            'Submit Review & Re-evaluate'
          )}
        </button>
      </div>

      {inspectingBbox && (
        <BoundingBoxOverlay
          imageSrc={imageSrc}
          fieldName={inspectingBbox.fieldName}
          label={inspectingBbox.label}
          sourceRegion={inspectingBbox.sourceRegion}
          confidence={inspectingBbox.confidence}
          onClose={() => setInspectingBbox(null)}
        />
      )}
    </div>
  );
}
