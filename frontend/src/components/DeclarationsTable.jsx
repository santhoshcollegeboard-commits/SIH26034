import { useState } from 'react';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import {
  MANDATORY_DECLARATIONS,
  NOT_AVAILABLE,
  NOT_RECORDED,
  NOT_APPLICABLE,
  formatMissingValue,
  formatConfidence,
  formatSourceRegion,
} from '../services/formatters';

export default function DeclarationsTable({ declarations, imageSrc }) {
  const [selectedBbox, setSelectedBbox] = useState(null);

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
          <span className="card-icon">📋</span>
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
              <th>Source Bounding Box</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => {
              const isMissing = item.value === NOT_AVAILABLE || item.value === NOT_RECORDED;
              const hasCoords =
                item.sourceRegion &&
                typeof item.sourceRegion === 'object' &&
                item.sourceRegion.x !== undefined;

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
                  <td className="region-cell">
                    {hasCoords ? (
                      <button
                        className="btn-inspect-region"
                        onClick={() =>
                          setSelectedBbox({
                            fieldName: item.key,
                            label: item.label,
                            sourceRegion: item.sourceRegion,
                            confidence: item.confidence,
                          })
                        }
                        title="Inspect bounding box on image"
                      >
                        🔍 View Evidence
                      </button>
                    ) : (
                      <span className="text-muted font-mono">{formatSourceRegion(item.sourceRegion)}</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {selectedBbox && (
        <BoundingBoxOverlay
          imageSrc={imageSrc}
          fieldName={selectedBbox.fieldName}
          label={selectedBbox.label}
          sourceRegion={selectedBbox.sourceRegion}
          confidence={selectedBbox.confidence}
          onClose={() => setSelectedBbox(null)}
        />
      )}
    </div>
  );
}
