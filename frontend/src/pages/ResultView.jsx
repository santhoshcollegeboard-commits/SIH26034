import { useState, useEffect } from 'react';
import { api } from '../services/api';
import QualityGateCard from '../components/QualityGateCard';
import DeclarationsTable from '../components/DeclarationsTable';
import RuleEvaluationsCard from '../components/RuleEvaluationsCard';
import AuditTrailCard from '../components/AuditTrailCard';
import {
  EMPTY_REVIEWS,
  formatMissingValue,
  getDispositionTheme,
} from '../services/formatters';

export default function ResultView({ inspectionId, onBack, onNewInspection }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!inspectionId) return;
    let isMounted = true;
    api.getResultReport(inspectionId)
      .then((data) => {
        if (isMounted) {
          setReport(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message || 'Failed to retrieve inspection result.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [inspectionId]);

  function handleOpenPdf() {
    if (!inspectionId) return;
    const url = api.getPdfUrl(inspectionId);
    window.open(url, '_blank');
  }

  function handleDownloadPdf() {
    if (!inspectionId) return;
    const url = api.getPdfUrl(inspectionId);
    const a = document.createElement('a');
    a.href = url;
    a.download = `PackCheck_${inspectionId}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }

  if (loading) {
    return (
      <div className="card text-center py-8">
        <span className="spinner" /> Loading official statutory result...
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="card result-error-card">
        <div className="error-banner mb-3">
          <span className="error-icon">⚠️</span>
          <span>{error || 'Inspection report not available.'}</span>
        </div>
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back
        </button>
      </div>
    );
  }

  const theme = getDispositionTheme(report.overall_disposition);
  const pkgId = formatMissingValue(report.package_id);
  const summary = formatMissingValue(report.summary);
  const reviews = report.review_actions || [];

  return (
    <div className="result-view-container" id="result-view-page">
      {/* Top Action Bar */}
      <div className="result-action-bar mb-4 flex-between">
        <div className="action-left">
          {onBack && (
            <button className="btn btn-secondary btn-sm" onClick={onBack}>
              ← Back
            </button>
          )}
          {onNewInspection && (
            <button className="btn btn-outline btn-sm ml-2" onClick={onNewInspection}>
              📸 New Inspection
            </button>
          )}
        </div>

        <div className="action-right">
          <button className="btn btn-secondary btn-sm mr-2" onClick={handleOpenPdf} id="btn-view-pdf">
            👁 View PDF Report
          </button>
          <button className="btn btn-primary btn-sm" onClick={handleDownloadPdf} id="btn-download-pdf">
            ⬇ Download Official PDF
          </button>
        </div>
      </div>

      {/* Prominent Statutory Verdict Banner */}
      <div className={`disposition-banner ${theme.bannerClass} mb-4`} id="final-verdict-banner">
        <div className="banner-left">
          <span className="banner-icon">{theme.icon}</span>
          <div>
            <div className="banner-label">FINAL STATUTORY DISPOSITION</div>
            <h2 className="banner-disposition">{theme.label}</h2>
            <p className="banner-summary-text mt-1">{summary}</p>
          </div>
        </div>
        <div className="banner-right">
          <div className="meta-block">
            <span className="meta-k">Inspection ID:</span>
            <span className="meta-v font-mono">{report.inspection_id}</span>
          </div>
          <div className="meta-block">
            <span className="meta-k">Package Ref:</span>
            <span className="meta-v font-mono">{pkgId}</span>
          </div>
          <div className="meta-block">
            <span className="meta-k">Created:</span>
            <span className="meta-v text-xs">{report.created_at}</span>
          </div>
        </div>
      </div>

      {/* Section 1: Image Evidence & Capture Quality */}
      <div className="mb-4">
        <div className="card mb-3">
          <div className="card-header">
            <h3 className="card-title">1. Image Evidence Metadata</h3>
          </div>
          {report.evidence ? (
            <div className="evidence-grid">
              <div className="metric-box">
                <span className="metric-label">Filename</span>
                <span className="metric-value font-mono">{formatMissingValue(report.evidence.filename)}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">MIME Type</span>
                <span className="metric-value">{formatMissingValue(report.evidence.media_type)}</span>
              </div>
              <div className="metric-box">
                <span className="metric-label">Dimensions</span>
                <span className="metric-value font-mono">
                  {report.evidence.image_width && report.evidence.image_height
                    ? `${report.evidence.image_width} × ${report.evidence.image_height} px`
                    : 'Not available in recorded evidence'}
                </span>
              </div>
              <div className="metric-box">
                <span className="metric-label">File Size</span>
                <span className="metric-value font-mono">
                  {report.evidence.file_size_bytes
                    ? `${(report.evidence.file_size_bytes / 1024).toFixed(1)} KB`
                    : 'Not available in recorded evidence'}
                </span>
              </div>
            </div>
          ) : (
            <p className="empty-message">No evidence records available.</p>
          )}
        </div>

        <QualityGateCard quality={report.quality || report.evidence?.quality_assessment} />
      </div>

      {/* Section 2: Mandatory Declarations */}
      <div className="mb-4">
        <DeclarationsTable declarations={report.observations} />
      </div>

      {/* Section 3: Statutory Rule Evaluations */}
      <div className="mb-4">
        <RuleEvaluationsCard evaluations={report.rule_evaluations} />
      </div>

      {/* Section 4: Human Review Audit Log */}
      <div className="card mb-4" id="human-review-log-card">
        <div className="card-header">
          <div className="card-header-title-group">
            <span className="card-icon">👤</span>
            <div>
              <h3 className="card-title">4. Human Review Audit Log</h3>
              <span className="card-subtitle">Permanent audit log of human reviewer resolutions</span>
            </div>
          </div>
        </div>

        {reviews.length === 0 ? (
          <div className="empty-state py-4 px-4 text-muted">
            <p className="empty-message">{EMPTY_REVIEWS}</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table" id="review-log-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Review Action</th>
                  <th>Original AI Value</th>
                  <th>Reviewed Value</th>
                  <th>Reviewer Notes</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {reviews.map((ra) => {
                  const actionStr = typeof ra.action === 'object' ? ra.action?.value : ra.action;
                  return (
                    <tr key={ra.review_id}>
                      <td className="font-medium">{formatMissingValue(ra.field_name)}</td>
                      <td>
                        <span className="status-badge badge-reviewed">
                          {String(actionStr || '').toUpperCase()}
                        </span>
                      </td>
                      <td className="text-muted font-mono">{formatMissingValue(ra.original_value)}</td>
                      <td className="font-mono font-medium">{formatMissingValue(ra.reviewed_value)}</td>
                      <td className="text-sm">{formatMissingValue(ra.reviewer_notes, true, 'No notes recorded.')}</td>
                      <td className="text-xs text-muted">{formatMissingValue(ra.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Section 5: Audit Traceability & Decision Trail */}
      <div className="mb-4">
        <AuditTrailCard
          traceability={report.traceability}
          decisionTrailSummary={report.decision_trail_summary}
        />
      </div>
    </div>
  );
}
