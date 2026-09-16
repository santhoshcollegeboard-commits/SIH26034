import { useState, useEffect } from 'react';
import { api } from '../services/api';
import {
  EMPTY_HISTORY,
  formatMissingValue,
  getDispositionTheme,
} from '../services/formatters';

export default function InspectionHistory({ onSelectInspection }) {
  const [inspections, setInspections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('ALL');
  const [error, setError] = useState(null);

  useEffect(() => {
    loadHistory();
  }, []);

  async function loadHistory() {
    setLoading(true);
    setError(null);
    try {
      const list = await api.listInspections(100, 0);
      setInspections(list || []);
    } catch (err) {
      setError(err.message || 'Failed to load inspection history.');
    } finally {
      setLoading(false);
    }
  }

  const filtered = inspections.filter((item) => {
    if (filter === 'ALL') return true;
    return item.overall_disposition === filter;
  });

  return (
    <div className="history-container" id="inspection-history-page">
      <div className="section-header flex-between">
        <div>
          <h2 className="section-title">Inspection History</h2>
          <p className="section-sub">
            Auditable statutory inspection records stored permanently in the Evidence Ledger.
          </p>
        </div>
        <button className="btn btn-secondary btn-sm" onClick={loadHistory} disabled={loading}>
          🔄 Refresh
        </button>
      </div>

      {error && (
        <div className="error-banner mb-4">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="filter-bar mb-4">
        {['ALL', 'PASS', 'FAIL', 'REVIEW_REQUIRED', 'NOT_ASSESSABLE'].map((f) => (
          <button
            key={f}
            className={`filter-btn ${filter === f ? 'active' : ''}`}
            onClick={() => setFilter(f)}
          >
            {f === 'ALL' ? 'All Records' : f.replace(/_/g, ' ')}
          </button>
        ))}
      </div>

      {/* History Table Card */}
      <div className="card history-card">
        {loading ? (
          <div className="py-6 text-center">
            <span className="spinner" /> Loading inspection records...
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state py-6 text-center" id="empty-history-notice">
            <p className="empty-message">{EMPTY_HISTORY}</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="data-table" id="history-table">
              <thead>
                <tr>
                  <th>Inspection ID</th>
                  <th>Package ID</th>
                  <th>Date &amp; Time (UTC)</th>
                  <th>Final Statutory Disposition</th>
                  <th>Summary</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => {
                  const theme = getDispositionTheme(item.overall_disposition);
                  const pkgId = formatMissingValue(item.package_id);
                  const summary = formatMissingValue(item.summary);
                  const dateStr = item.created_at ? new Date(item.created_at).toLocaleString() : '';

                  return (
                    <tr key={item.inspection_id}>
                      <td className="font-mono font-medium">{item.inspection_id}</td>
                      <td className="font-mono">{pkgId}</td>
                      <td className="text-muted text-sm">{dateStr}</td>
                      <td>
                        <span className={`status-badge ${theme.badgeClass}`}>
                          {theme.icon} {theme.label}
                        </span>
                      </td>
                      <td className="summary-cell text-sm text-muted">
                        {summary}
                      </td>
                      <td>
                        <button
                          className="btn btn-xs btn-outline"
                          onClick={() => onSelectInspection && onSelectInspection(item.inspection_id)}
                        >
                          View Details →
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
