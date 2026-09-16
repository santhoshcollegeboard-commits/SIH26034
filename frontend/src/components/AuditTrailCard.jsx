import { formatMissingValue } from '../services/formatters';

export default function AuditTrailCard({ traceability, decisionTrailSummary }) {
  if (!traceability && !decisionTrailSummary) {
    return null;
  }

  const engine = traceability?.rule_engine_version || 'DeterministicRuleEngine-v1.0';
  const regime = traceability?.statutory_source || 'The Legal Metrology (Packaged Commodities) Rules, 2011';
  const totalCount = traceability?.evaluated_rule_count ?? 0;
  const initialCount = traceability?.initial_rule_count ?? 0;
  const postReviewCount = traceability?.post_review_rule_count ?? 0;
  const chain = traceability?.provenance_chain || 'Evidence -> Observation -> Rule Evaluation -> Review Action -> Final Disposition';

  return (
    <div className="card audit-card" id="audit-trail-card">
      <div className="card-header">
        <div className="card-header-title-group">
          <span className="card-icon">📜</span>
          <div>
            <h3 className="card-title">Audit Traceability &amp; Decision Trail</h3>
            <span className="card-subtitle">
              Immutable provenance reconstructing the evidence and decision path
            </span>
          </div>
        </div>
      </div>

      <div className="traceability-info-grid">
        <div className="trace-item">
          <span className="trace-label">Rule Engine Version:</span>
          <span className="trace-val font-mono">{engine}</span>
        </div>
        <div className="trace-item">
          <span className="trace-label">Statutory Source:</span>
          <span className="trace-val">{regime}</span>
        </div>
        <div className="trace-item">
          <span className="trace-label">Rule Evaluations:</span>
          <span className="trace-val font-mono">
            {totalCount} total ({initialCount} initial, {postReviewCount} post-review)
          </span>
        </div>
        <div className="trace-item">
          <span className="trace-label">Decision Chain:</span>
          <span className="trace-val font-mono text-xs">{chain}</span>
        </div>
      </div>

      {decisionTrailSummary && (
        <div className="decision-trail-box mt-3">
          <span className="trail-title">Narrative Audit Trail Summary</span>
          <pre className="trail-text font-mono">{formatMissingValue(decisionTrailSummary)}</pre>
        </div>
      )}
    </div>
  );
}
