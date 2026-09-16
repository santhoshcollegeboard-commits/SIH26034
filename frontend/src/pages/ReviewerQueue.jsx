import { useState, useEffect, useCallback } from 'react';
import { api } from '../services/api';
import ReviewSection from '../components/ReviewSection';
import DeclarationsTable from '../components/DeclarationsTable';
import RuleEvaluationsCard from '../components/RuleEvaluationsCard';
import { getDispositionTheme } from '../services/formatters';

export default function ReviewerQueue({ initialInspectionId, onReviewCompleted }) {
  const [queue, setQueue] = useState([]);
  const [loadingQueue, setLoadingQueue] = useState(true);
  const [selectedInspectionId, setSelectedInspectionId] = useState(initialInspectionId || null);

  // Active review inspection state
  const [trail, setTrail] = useState(null);
  const [reviewItems, setReviewItems] = useState([]);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [successMsg, setSuccessMsg] = useState(null);

  const refreshQueue = useCallback(async () => {
    setLoadingQueue(true);
    setError(null);
    try {
      const list = await api.listInspections(100, 0);
      const pending = (list || []).filter((item) => item.overall_disposition === 'REVIEW_REQUIRED');
      setQueue(pending);
      if (initialInspectionId) {
        setSelectedInspectionId(initialInspectionId);
      } else if (pending.length > 0) {
        setSelectedInspectionId((prev) => prev || pending[0].inspection_id);
      }
    } catch (err) {
      setError(err.message || 'Failed to load reviewer queue.');
    } finally {
      setLoadingQueue(false);
    }
  }, [initialInspectionId]);

  // Load queue on mount
  useEffect(() => {
    let isMounted = true;
    api.listInspections(100, 0)
      .then((list) => {
        if (!isMounted) return;
        const pending = (list || []).filter((item) => item.overall_disposition === 'REVIEW_REQUIRED');
        setQueue(pending);
        if (initialInspectionId) {
          setSelectedInspectionId(initialInspectionId);
        } else if (pending.length > 0) {
          setSelectedInspectionId((prev) => prev || pending[0].inspection_id);
        }
        setLoadingQueue(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err.message || 'Failed to load reviewer queue.');
        setLoadingQueue(false);
      });

    return () => {
      isMounted = false;
    };
  }, [initialInspectionId]);

  // When selectedInspectionId changes, load details
  useEffect(() => {
    if (!selectedInspectionId) return;
    let isMounted = true;

    api.getInspectionTrail(selectedInspectionId)
      .then(async (trailData) => {
        if (!isMounted) return;
        setTrail(trailData);

        // Reconstruct extraction format to identify review items
        const extractionObj = {};
        (trailData.observations || []).forEach((obs) => {
          extractionObj[obs.field_name] = {
            value: obs.value,
            confidence: obs.confidence,
            status: obs.status,
            source_region: obs.source_region,
            source_type: obs.source_type,
          };
        });

        const inspectionObj = {
          overall_disposition: trailData.inspection.overall_disposition,
          rule_evaluations: trailData.rule_evaluations,
          summary: trailData.inspection.summary,
        };

        const itemsResponse = await api.getReviewItems({
          extraction: extractionObj,
          inspection: inspectionObj,
        });

        if (isMounted) {
          setReviewItems(itemsResponse.review_items || []);
          setLoadingDetails(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to load inspection details.');
          setLoadingDetails(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedInspectionId]);

  function handleSelectInspection(id) {
    if (!id) {
      setSelectedInspectionId(null);
      setTrail(null);
      setReviewItems([]);
    } else {
      setSelectedInspectionId(id);
      setLoadingDetails(true);
      setError(null);
      setSuccessMsg(null);
    }
  }

  async function handleSubmitReview(corrections) {
    if (!selectedInspectionId || !trail) return;

    setIsSubmitting(true);
    setError(null);
    try {
      // Reconstruct original extraction object
      const originalExtraction = {};
      (trail.observations || []).forEach((obs) => {
        originalExtraction[obs.field_name] = {
          value: obs.value,
          confidence: obs.confidence,
          status: obs.status,
          source_region: obs.source_region,
          source_type: obs.source_type,
        };
      });

      // 1. Submit review to review engine for deterministic re-evaluation
      const reviewResult = await api.submitReview({
        originalExtraction,
        corrections,
      });

      // 2. Append review resolution to the Evidence Ledger
      const updatedTrail = await api.appendReviewToLedger(selectedInspectionId, {
        corrections,
        updatedExtraction: reviewResult.updated_extraction,
        newCompliance: reviewResult.new_compliance,
        provenance: reviewResult.provenance,
      });

      setSuccessMsg(`Review successfully applied. New statutory disposition: ${reviewResult.new_compliance.overall_disposition}`);
      setTrail(updatedTrail);
      setReviewItems([]);

      // Refresh queue
      await refreshQueue();

      // If review completed callback provided, notify parent
      if (onReviewCompleted) {
        setTimeout(() => {
          onReviewCompleted(selectedInspectionId);
        }, 1200);
      }
    } catch (err) {
      setError(err.message || 'Failed to submit review resolutions.');
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <div className="reviewer-queue-container" id="reviewer-queue-page">
      <div className="section-header">
        <h2 className="section-title">Reviewer Queue</h2>
        <p className="section-sub">
          Inspections flagged with REVIEW_REQUIRED due to borderline OCR confidence or observation uncertainty. Resolve observations deterministically.
        </p>
      </div>

      {error && (
        <div className="error-banner mb-4" id="reviewer-error-banner">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {successMsg && (
        <div className="success-banner mb-4" id="reviewer-success-banner">
          <span className="success-icon">✓</span>
          <span>{successMsg}</span>
        </div>
      )}

      <div className="reviewer-layout-grid">
        {/* Left Sidebar: Queue List */}
        <div className="queue-sidebar card">
          <div className="card-header flex-between">
            <h3 className="card-title">Pending Reviews</h3>
            <span className="badge-count font-mono">{queue.length}</span>
          </div>

          {loadingQueue ? (
            <div className="loading-state py-4">
              <span className="spinner" /> Loading queue...
            </div>
          ) : queue.length === 0 ? (
            <div className="empty-queue-notice" id="empty-queue-notice">
              <span className="empty-icon">✓</span>
              <p className="empty-text">No inspections currently require human review.</p>
              <span className="empty-sub">All statutory inspections have definitive automated dispositions.</span>
            </div>
          ) : (
            <div className="queue-items-list">
              {queue.map((item) => {
                const isSelected = item.inspection_id === selectedInspectionId;
                const theme = getDispositionTheme(item.overall_disposition);
                const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : '';

                return (
                  <div
                    key={item.inspection_id}
                    className={`queue-item-row ${isSelected ? 'selected' : ''}`}
                    onClick={() => handleSelectInspection(item.inspection_id)}
                  >
                    <div className="queue-item-top">
                      <span className="item-id font-mono font-medium">{item.inspection_id}</span>
                      <span className={`status-badge ${theme.badgeClass}`}>
                        {theme.label}
                      </span>
                    </div>
                    {item.package_id && (
                      <div className="item-pkg-id text-muted font-mono">Ref: {item.package_id}</div>
                    )}
                    <div className="item-date text-xs text-muted mt-1">{dateStr}</div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Area: Review Inspection Interface */}
        <div className="queue-detail-content">
          {loadingDetails ? (
            <div className="card text-center py-6">
              <span className="spinner" /> Loading inspection evidence...
            </div>
          ) : !trail ? (
            <div className="card text-center py-6 text-muted">
              Select an inspection from the queue to start review.
            </div>
          ) : (
            <div className="inspection-review-view">
              {/* Header Info Banner */}
              <div className="card mb-4">
                <div className="card-header flex-between">
                  <div>
                    <h3 className="card-title">Inspection {trail.inspection.inspection_id}</h3>
                    <span className="card-subtitle">
                      Package: {trail.inspection.package_id || 'Not specified'} · Created: {trail.inspection.created_at}
                    </span>
                  </div>
                  <span className="status-badge badge-review font-mono">
                    {trail.inspection.overall_disposition}
                  </span>
                </div>
              </div>

              {/* Review Section if pending items */}
              {reviewItems.length > 0 && (
                <div className="mb-4">
                  <ReviewSection
                    reviewItems={reviewItems}
                    onSubmitReview={handleSubmitReview}
                    isSubmitting={isSubmitting}
                  />
                </div>
              )}

              {/* Declarations Table */}
              <div className="mb-4">
                <DeclarationsTable declarations={trail.observations} />
              </div>

              {/* Rule Evaluations Table */}
              <div className="mb-4">
                <RuleEvaluationsCard evaluations={trail.rule_evaluations} />
              </div>

              {/* Actions */}
              <div className="flex-end mt-4">
                <button
                  className="btn btn-secondary"
                  onClick={() => onReviewCompleted && onReviewCompleted(selectedInspectionId)}
                >
                  View Full Official Report →
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
