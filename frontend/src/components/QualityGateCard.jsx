import { NOT_AVAILABLE, formatMissingValue } from '../services/formatters';

/**
 * Renders the Image Quality Gate assessment card.
 * If rejected, displays prominent recapture alert with statutory quality reasons.
 */
export default function QualityGateCard({ quality, onRecapture }) {
  if (!quality) {
    return (
      <div className="card quality-gate-card">
        <div className="card-header">
          <h3 className="card-title">Image Quality Gate</h3>
        </div>
        <p className="empty-message">Quality assessment: {NOT_AVAILABLE}</p>
      </div>
    );
  }

  const isAcceptable = quality.is_acceptable;
  const score = quality.overall_score !== undefined ? Number(quality.overall_score).toFixed(2) : null;
  const reasons = quality.reasons || [];
  const details = quality.details || {};

  return (
    <div className={`card quality-gate-card ${isAcceptable ? 'quality-pass' : 'quality-fail'}`} id="quality-gate-card">
      <div className="card-header">
        <div className="card-header-title-group">
          <span className="card-icon">{isAcceptable ? '🛡️' : '⚠️'}</span>
          <div>
            <h3 className="card-title">Image Quality Gate</h3>
            <span className="card-subtitle">
              Pre-OCR capture verification pursuant to Legal Metrology digital evidence standards
            </span>
          </div>
        </div>
        <div className="card-header-badge">
          <span className={`status-badge ${isAcceptable ? 'badge-pass' : 'badge-fail'}`} id="quality-status-badge">
            {isAcceptable ? '✓ Acceptable' : '✗ Insufficient Quality'}
          </span>
        </div>
      </div>

      {!isAcceptable && (
        <div className="quality-alert-banner" id="quality-failure-banner">
          <div className="alert-title">Image quality is insufficient for reliable inspection.</div>
          <p className="alert-sub">
            The package capture failed automated quality verification. Statutory rules cannot be reliably assessed.
          </p>
          {reasons.length > 0 && (
            <ul className="rejection-reasons-list">
              {reasons.map((r, i) => (
                <li key={i}>{formatMissingValue(r)}</li>
              ))}
            </ul>
          )}
          {onRecapture && (
            <button className="btn btn-primary btn-sm mt-3" onClick={onRecapture} id="btn-recapture">
              🔄 Recapture Image
            </button>
          )}
        </div>
      )}

      <div className="quality-metrics-grid">
        <div className="metric-box">
          <span className="metric-label">Quality Score</span>
          <span className="metric-value font-mono">{score !== null ? `${score} / 1.00` : NOT_AVAILABLE}</span>
          {score !== null && (
            <div className="metric-bar-track">
              <div
                className={`metric-bar-fill ${isAcceptable ? 'fill-emerald' : 'fill-red'}`}
                style={{ width: `${Math.min(Number(score) * 100, 100)}%` }}
              />
            </div>
          )}
        </div>

        <div className="metric-box">
          <span className="metric-label">Sharpness</span>
          <span className="metric-value">{formatMissingValue(details.sharpness)}</span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Lighting / Brightness</span>
          <span className="metric-value">{formatMissingValue(details.lighting || details.brightness)}</span>
        </div>

        <div className="metric-box">
          <span className="metric-label">Framing / Framing Score</span>
          <span className="metric-value">{formatMissingValue(details.framing || details.aspect_ratio)}</span>
        </div>
      </div>
    </div>
  );
}
