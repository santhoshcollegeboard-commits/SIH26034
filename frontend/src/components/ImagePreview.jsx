import React, { useRef } from 'react';

const PANEL_OPTIONS = [
  'Front Panel',
  'Back Panel',
  'Side Panel (Left)',
  'Side Panel (Right)',
  'Top Panel',
  'Bottom Panel',
  'Other / Detail View',
];

/**
 * Multi-panel preview screen shown once one or more images are captured/selected.
 * Allows tagging panel types, previewing, removing, adding more panels, and verifying.
 */
export default function ImagePreview({
  panels = [],
  file,
  previewUrl,
  onVerify,
  onReset,
  onRemovePanel,
  onUpdatePanelLabel,
  onAddMoreFiles,
  loading = false,
}) {
  const addFileInputRef = useRef(null);
  const addCameraInputRef = useRef(null);

  // Normalize to panels array (supports backward-compatibility if single file passed)
  const displayPanels =
    panels && panels.length > 0
      ? panels
      : file && previewUrl
      ? [{ id: 'single', file, previewUrl, panelLabel: 'Front Panel' }]
      : [];

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const handleMoreFiles = (fileList) => {
    if (!fileList || fileList.length === 0) return;
    if (onAddMoreFiles) {
      onAddMoreFiles(Array.from(fileList));
    }
  };

  return (
    <div className="preview-screen multi-panel-preview">
      {/* Hidden inputs to add more panels */}
      <input
        ref={addCameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => {
          handleMoreFiles(e.target.files);
          e.target.value = '';
        }}
        id="add-camera-input"
      />
      <input
        ref={addFileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => {
          handleMoreFiles(e.target.files);
          e.target.value = '';
        }}
        id="add-file-input"
      />

      {/* Screen Header */}
      <div className="preview-header">
        <div className="header-title-row">
          <h3 className="preview-heading">Product Panels</h3>
          <span className="panel-count-badge">
            {displayPanels.length} {displayPanels.length === 1 ? 'Panel' : 'Panels'} Selected
          </span>
        </div>
        <p className="preview-sub">
          Verify declarations distributed across multiple sides of the packaging.
        </p>
      </div>

      {/* Multi-Panel Grid / Cards */}
      <div className="panels-grid">
        {displayPanels.map((panel, idx) => (
          <div key={panel.id || idx} className="panel-card">
            <div className="panel-thumb-container">
              <img
                src={panel.previewUrl}
                alt={`${panel.panelLabel || 'Panel'} preview`}
                className="panel-img"
              />
              <span className="panel-number-chip">#{idx + 1}</span>

              {onRemovePanel && displayPanels.length > 1 && (
                <button
                  type="button"
                  className="btn-remove-panel"
                  onClick={() => onRemovePanel(panel.id)}
                  title="Remove this panel"
                  aria-label={`Remove panel ${idx + 1}`}
                >
                  ✕
                </button>
              )}
            </div>

            <div className="panel-controls">
              <div className="panel-select-row">
                <label htmlFor={`label-select-${idx}`} className="panel-select-label">
                  Panel:
                </label>
                <select
                  id={`label-select-${idx}`}
                  className="panel-label-select"
                  value={panel.panelLabel || PANEL_OPTIONS[0]}
                  onChange={(e) =>
                    onUpdatePanelLabel && onUpdatePanelLabel(panel.id, e.target.value)
                  }
                >
                  {PANEL_OPTIONS.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              </div>

              <div className="panel-meta-row">
                <span className="panel-filename" title={panel.file?.name}>
                  {panel.file?.name || `Panel ${idx + 1}`}
                </span>
                <span className="panel-size">{formatFileSize(panel.file?.size)}</span>
              </div>
            </div>
          </div>
        ))}

        {/* Add More Panel Card */}
        {displayPanels.length < 10 && (
          <div className="add-panel-card">
            <div className="add-panel-content">
              <span className="add-panel-icon">＋</span>
              <span className="add-panel-text">Add Another Panel</span>
              <span className="add-panel-hint">e.g. Back or Side</span>
              <div className="add-panel-actions">
                <button
                  type="button"
                  className="btn-add-camera"
                  onClick={() => addCameraInputRef.current?.click()}
                  title="Take photo of another panel"
                >
                  📷 Scan
                </button>
                <button
                  type="button"
                  className="btn-add-upload"
                  onClick={() => addFileInputRef.current?.click()}
                  title="Upload from device"
                >
                  📁 Browse
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Guidelines Pill */}
      <div className="guideline-callout">
        <span className="guideline-icon">ℹ</span>
        <p className="guideline-text">
          {displayPanels.length > 1
            ? 'Declarations from all panels will be aggregated into a single Legal Metrology verification. Any contradictory declarations will be flagged for review.'
            : 'You can add other package sides (back, side) or proceed with this panel.'}
        </p>
      </div>

      {/* Action Buttons */}
      <div className="preview-actions-footer">
        <button
          type="button"
          className="btn-primary btn-large"
          onClick={onVerify}
          disabled={loading || displayPanels.length === 0}
          id="btn-start-verification"
        >
          <span className="btn-icon">⚡</span>
          <span>
            Verify Product ({displayPanels.length} {displayPanels.length === 1 ? 'Panel' : 'Panels'})
          </span>
        </button>

        <button
          type="button"
          className="btn-ghost"
          onClick={onReset}
          disabled={loading}
          id="btn-choose-another"
        >
          <span>Start Over</span>
        </button>
      </div>
    </div>
  );
}
