import {
  NOT_AVAILABLE,
  formatMissingValue,
  getDispositionTheme,
} from '../services/formatters';

export default function RuleEvaluationsCard({ evaluations }) {
  if (!evaluations || evaluations.length === 0) {
    return (
      <div className="card rules-card">
        <div className="card-header">
          <h3 className="card-title">Deterministic Rule Evaluations</h3>
        </div>
        <p className="empty-message">No rule evaluations recorded.</p>
      </div>
    );
  }

  return (
    <div className="card rules-card" id="rules-evaluation-card">
      <div className="card-header">
        <div className="card-header-title-group">
          <span className="card-icon">⚖️</span>
          <div>
            <h3 className="card-title">Deterministic Statutory Rule Evaluations</h3>
            <span className="card-subtitle">
              Evaluated strictly against Legal Metrology (Packaged Commodities) Rules, 2011
            </span>
          </div>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table" id="rule-evaluations-table">
          <thead>
            <tr>
              <th>Rule ID / Version</th>
              <th>Statutory Reference</th>
              <th>Verdict</th>
              <th>Observed Value</th>
              <th>Legal Requirement &amp; Explanation</th>
              <th>Stage</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((r, i) => {
              const theme = getDispositionTheme(r.status);
              const obsVal = formatMissingValue(r.observed_value);
              const expReq = formatMissingValue(r.expected_requirement);
              const explanation = formatMissingValue(r.explanation);
              const statRef = formatMissingValue(r.statutory_reference);

              return (
                <tr key={r.evaluation_id || r.rule_id || i}>
                  <td className="rule-id-cell">
                    <div className="rule-id font-mono font-medium">{r.rule_id}</div>
                    {r.rule_version && <div className="rule-version text-muted">{r.rule_version}</div>}
                  </td>
                  <td className="stat-ref-cell">{statRef}</td>
                  <td className="status-cell">
                    <span className={`status-badge ${theme.badgeClass}`}>
                      {theme.icon} {theme.label}
                    </span>
                  </td>
                  <td className="observed-cell">
                    <span className={obsVal === NOT_AVAILABLE ? 'text-missing' : 'font-medium'}>
                      {obsVal}
                    </span>
                  </td>
                  <td className="explanation-cell">
                    <div className="req-line">
                      <span className="req-label">Requirement:</span>{' '}
                      <span className={expReq === NOT_AVAILABLE ? 'text-missing' : ''}>{expReq}</span>
                    </div>
                    <div className="exp-line text-muted">
                      <span className="exp-label">Explanation:</span>{' '}
                      <span className={explanation === NOT_AVAILABLE ? 'text-missing' : ''}>{explanation}</span>
                    </div>
                  </td>
                  <td className="stage-cell">
                    <span className="stage-tag font-mono">{r.evaluation_stage || 'initial'}</span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
