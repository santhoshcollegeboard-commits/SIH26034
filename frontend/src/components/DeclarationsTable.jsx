import {
  MANDATORY_DECLARATIONS,
  NOT_AVAILABLE,
  NOT_RECORDED,
  NOT_APPLICABLE,
  formatMissingValue,
  formatConfidence,
} from '../services/formatters';

function FileTextIcon({ size = 18, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <line x1="10" y1="9" x2="8" y2="9" />
    </svg>
  );
}

export default function DeclarationsTable({ declarations }) {

  if (!declarations || (Array.isArray(declarations) && declarations.length === 0)) {
    return (
      <div className="card declarations-card">
        <div className="card-header">
          <h3 className="card-title">Mandatory Packaging Declarations</h3>
        </div>
        <p className="empty-message">No observations recorded.</p>
      </div>
    );
  }

  // Normalize declarations: could be an array of ObservationPresentation or an object from ExtractionResult
  let items = [];
  if (Array.isArray(declarations)) {
    items = declarations.map((obs) => {
      const fieldMeta = MANDATORY_DECLARATIONS.find((d) => d.key === obs.field_name) || {
        key: obs.field_name,
        label: obs.field_name ? obs.field_name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()) : 'Unknown Field',
      };
      return {
        key: obs.field_name,
        label: fieldMeta.label,
        value: formatMissingValue(obs.value),
        confidence: formatConfidence(obs.confidence),
        status: formatMissingValue(obs.status, true, NOT_RECORDED),
        sourceRegion: obs.source_region,
        sourceType: obs.source_type || 'ai_extraction',
      };
    });
  } else {
    items = MANDATORY_DECLARATIONS.map(({ key, label }) => {
      const field = declarations[key] || {};
      const isNa = field.status === 'not_applicable';
      return {
        key,
        label,
        value: isNa ? NOT_APPLICABLE : formatMissingValue(field.value),
        confidence: isNa ? NOT_APPLICABLE : formatConfidence(field.confidence),
        status: isNa
          ? NOT_APPLICABLE
          : field.status === 'not_found' || !field.status
          ? NOT_RECORDED
          : formatMissingValue(field.status),
        sourceRegion: field.source_region,
        sourceType: field.source_type || 'ai_extraction',
      };
    });
  }

  function getStatusBadge(status) {
    const s = String(status || '').toLowerCase();
    if (s.includes('extracted') || s === 'extracted') {
      return <span className="status-badge badge-extracted">Extracted</span>;
    }
    if (s.includes('confirm') || s.includes('correct')) {
      return <span className="status-badge badge-reviewed">Reviewed</span>;
    }
    if (s === 'not applicable' || s.includes('not_applicable')) {
      return <span className="status-badge badge-na">Not applicable</span>;
    }
    if (s.includes('unreadable')) {
      return <span className="status-badge badge-unreadable">Unreadable</span>;
    }
    return <span className="status-badge badge-not-recorded">{NOT_RECORDED}</span>;
  }

  function renderConfidence(confStr) {
    if (confStr === NOT_AVAILABLE || confStr === NOT_APPLICABLE) {
      return <span className="text-muted">{confStr}</span>;
    }
    const num = parseInt(confStr, 10);
    if (isNaN(num)) return <span>{confStr}</span>;

    const barColor = num >= 90 ? 'var(--accent-emerald)' : num >= 70 ? 'var(--accent-amber)' : 'var(--accent-red)';
    return (
      <div className="confidence-cell">
        <div className="confidence-bar-track">
          <div className="confidence-bar-fill" style={{ width: `${num}%`, backgroundColor: barColor }} />
        </div>
        <span className="confidence-value font-mono">{confStr}</span>
      </div>
    );
  }

  return (
    <div className="card declarations-card" id="declarations-table-card">
      <div className="card-header">
        <div className="card-header-title-group">
          <span className="card-icon">
            <FileTextIcon size={18} />
          </span>
          <div>
            <h3 className="card-title">Mandatory Packaging Declarations</h3>
            <span className="card-subtitle">
              Section 6 Legal Metrology (Packaged Commodities) Rules, 2011 declarations
            </span>
          </div>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table" id="declarations-table">
          <thead>
            <tr>
              <th>Declaration Field</th>
              <th>Observed Value</th>
              <th>Confidence</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isMissing = item.value === NOT_AVAILABLE || item.value === NOT_RECORDED;

              return (
                <tr key={item.key} className={isMissing ? 'row-muted' : ''}>
                  <td className="field-cell font-medium">{item.label}</td>
                  <td className="value-cell">
                    <span className={isMissing ? 'text-missing' : 'text-primary font-medium'}>
                      {item.value}
                    </span>
                  </td>
                  <td className="conf-cell">{renderConfidence(item.confidence)}</td>
                  <td className="status-cell">{getStatusBadge(item.status)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
