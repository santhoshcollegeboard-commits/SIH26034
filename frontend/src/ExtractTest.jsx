import { useState, useRef } from 'react';

const API_BASE = 'http://127.0.0.1:8000';

const FIELD_LABELS = {
  product_name: 'Product Name',
  manufacturer_name: 'Manufacturer Name',
  manufacturer_address: 'Manufacturer Address',
  packer_name: 'Packer Name',
  importer_name: 'Importer Name',
  net_quantity: 'Net Quantity',
  mrp: 'MRP',
  month_year_of_manufacture: 'Mfg Date (Month/Year)',
  consumer_care_details: 'Consumer Care Details',
};

function PackageIcon({ size = 32, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="m7.5 4.27 9 5.15" />
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <line x1="12" y1="22" x2="12" y2="12" />
    </svg>
  );
}

function AlertIcon({ size = 16, className = '' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className} aria-hidden="true">
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function statusBadge(status) {
  const map = {
    extracted: { className: 'badge-extracted', label: 'Extracted' },
    unreadable: { className: 'badge-unreadable', label: 'Unreadable' },
    not_found: { className: 'badge-not-found', label: 'Not Found' },
  };
  const s = map[status] || map.not_found;
  return <span className={`status-badge ${s.className}`}>{s.label}</span>;
}

function confidenceBar(confidence) {
  if (confidence === null || confidence === undefined) return <span className="no-data">—</span>;
  const pct = Math.round(confidence * 100);
  const color =
    pct >= 90 ? 'var(--accent-emerald)' : pct >= 70 ? 'var(--accent-amber)' : '#ef4444';
  return (
    <div className="confidence-cell">
      <div className="confidence-bar-track">
        <div
          className="confidence-bar-fill"
          style={{ width: `${pct}%`, backgroundColor: color }}
        />
      </div>
      <span className="confidence-value">{pct}%</span>
    </div>
  );
}

export default function ExtractTest() {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [meta, setMeta] = useState(null);
  const fileInputRef = useRef(null);
  const dropRef = useRef(null);

  function handleFileSelect(selectedFile) {
    if (!selectedFile) return;
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(selectedFile.type)) {
      setError('Please select a JPEG, PNG, or WEBP image.');
      return;
    }
    setFile(selectedFile);
    setPreview(URL.createObjectURL(selectedFile));
    setResult(null);
    setError(null);
    setMeta(null);
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropRef.current?.classList.remove('drag-over');
    const droppedFile = e.dataTransfer.files?.[0];
    handleFileSelect(droppedFile);
  }

  function handleDragOver(e) {
    e.preventDefault();
    dropRef.current?.classList.add('drag-over');
  }

  function handleDragLeave(e) {
    e.preventDefault();
    dropRef.current?.classList.remove('drag-over');
  }

  async function handleExtract() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setMeta(null);

    try {
      const formData = new FormData();
      formData.append('image', file);

      const response = await fetch(`${API_BASE}/api/extract`, {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        setError(data.detail || 'Extraction request failed.');
        return;
      }

      if (!data.success) {
        setError(data.error || 'Extraction failed.');
        return;
      }

      setResult(data.result);
      setMeta({
        model: data.model_used,
        time: data.processing_time_ms,
      });
    } catch (err) {
      setError(`Network error: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleReset() {
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setMeta(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  return (
    <div className="extract-container">
      {/* Upload Section */}
      <div className="upload-section">
        <div
          ref={dropRef}
          className={`drop-zone ${preview ? 'has-preview' : ''}`}
          onClick={() => !preview && fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          id="drop-zone"
        >
          {preview ? (
            <img src={preview} alt="Package preview" className="image-preview" id="image-preview" />
          ) : (
            <div className="drop-placeholder">
              <div className="drop-icon">
                <PackageIcon size={32} />
              </div>
              <div className="drop-text">Drop a package image here</div>
              <div className="drop-sub">or click to browse · JPEG, PNG, WEBP</div>
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => handleFileSelect(e.target.files?.[0])}
          style={{ display: 'none' }}
          id="file-input"
        />

        <div className="action-buttons">
          {preview && (
            <button className="btn btn-secondary" onClick={handleReset} id="btn-reset">
              Clear
            </button>
          )}
          {!preview && (
            <button className="btn btn-secondary" onClick={() => fileInputRef.current?.click()} id="btn-upload">
              Upload Image
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleExtract}
            disabled={!file || loading}
            id="btn-extract"
          >
            {loading ? (
              <span className="btn-loading">
                <span className="spinner" /> Extracting...
              </span>
            ) : (
              'Extract Fields'
            )}
          </button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner" id="error-display">
          <span className="error-icon">
            <AlertIcon size={16} />
          </span>
          <span>{error}</span>
        </div>
      )}

      {/* Results Section */}
      {result && (
        <div className="results-section" id="results-section">
          <div className="results-header">
            <h3 className="results-title">Extraction Results</h3>
            {meta && (
              <div className="results-meta">
                <span className="meta-tag">{meta.model}</span>
                <span className="meta-tag">{meta.time} ms</span>
              </div>
            )}
          </div>

          <div className="results-table-wrapper">
            <table className="results-table" id="results-table">
              <thead>
                <tr>
                  <th>Field</th>
                  <th>Value</th>
                  <th>Confidence</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {Object.entries(FIELD_LABELS).map(([key, label]) => {
                  const field = result[key] || {};
                  return (
                    <tr key={key} className={field.status === 'extracted' ? '' : 'row-missing'}>
                      <td className="field-name">{label}</td>
                      <td className="field-value">
                        {field.value || <span className="no-data">—</span>}
                      </td>
                      <td>{confidenceBar(field.confidence)}</td>
                      <td>{statusBadge(field.status)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          <div className="results-notice">
            <span className="notice-icon">ℹ</span>
            Extraction only — no compliance judgment has been made. Fields will be evaluated by the Rule Engine in a future milestone.
          </div>
        </div>
      )}
    </div>
  );
}
