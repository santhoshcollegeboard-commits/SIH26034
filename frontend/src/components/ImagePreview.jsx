import React, { useRef, useState } from 'react';

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
 * Responsive Multi-panel preview screen.
 * - PC Mode: Workstation-grade layout with a large inspectable package image stage,
 *   keyboard/mouse panel navigation, and a dedicated panel management sidebar.
 * - Mobile Mode: Preserves the existing touch-first panel card grid.
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
  isPC = false,
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

  const [selectedPanelId, setSelectedPanelId] = useState(displayPanels[0]?.id || null);

  // Derive active panel directly during render without extra effects
  const isSelectedValid = displayPanels.some((p) => p.id === selectedPanelId);
  const activePanelId = isSelectedValid ? selectedPanelId : displayPanels[0]?.id;
  const activeIndex = Math.max(
    0,
    displayPanels.findIndex((p) => p.id === activePanelId)
  );
  const activePanel = displayPanels[activeIndex] || displayPanels[0];

  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const formatTruncatedFilename = (name, maxLen = 22) => {
    if (!name) return 'panel.jpg';
    if (name.length <= maxLen) return name;
    const dotIdx = name.lastIndexOf('.');
    if (dotIdx > 0 && dotIdx >= name.length - 6) {
      const ext = name.slice(dotIdx);
      const base = name.slice(0, dotIdx);
      const keep = maxLen - ext.length - 3;
      return `${base.slice(0, Math.max(keep, 3))}...${ext}`;
    }
    return `${name.slice(0, maxLen - 3)}...`;
  };

  const handleMoreFiles = (fileList) => {
    if (!fileList || fileList.length === 0) return;
    if (onAddMoreFiles) {
      onAddMoreFiles(Array.from(fileList));
    }
  };

  const handlePrevPanel = () => {
    if (activeIndex > 0) {
      setSelectedPanelId(displayPanels[activeIndex - 1].id);
    }
  };

  const handleNextPanel = () => {
    if (activeIndex < displayPanels.length - 1) {
      setSelectedPanelId(displayPanels[activeIndex + 1].id);
    }
  };

  return (
    <div className={`preview-screen multi-panel-preview ${isPC ? 'pc-preview-layout' : 'mobile-preview-layout'}`}>
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

      {/* ─── PC WORKSTATION PREVIEW LAYOUT ─── */}
      {isPC ? (
        <div className="pc-preview-container">
          <div className="pc-preview-header">
            <div className="header-title-col">
              <h2 className="pc-preview-heading">Product Panel Inspection</h2>
              <p className="pc-preview-sub">
                Inspect high-resolution packaging declarations and verify panel types before compliance analysis.
              </p>
            </div>
            <div className="pc-header-actions">
              <span className="panel-count-badge">
                {displayPanels.length} {displayPanels.length === 1 ? 'Panel' : 'Panels'} Selected
              </span>
            </div>
          </div>

          <div className="pc-preview-workstation-grid">
            {/* Left Column: Focused Image Stage */}
            <div className="pc-preview-stage-col">
              {activePanel ? (
                <div className="pc-large-image-card">
                  <div className="stage-top-meta">
                    <div className="stage-panel-headline">
                      <span className="stage-pin-icon">📌</span>
                      <h3 className="stage-panel-title">
                        {activePanel.panelLabel || 'Package Panel'}
                      </h3>
                      <span className="stage-pager-chip">
                        Panel {activeIndex + 1} of {displayPanels.length}
                      </span>
                    </div>

                    <div className="stage-file-sub">
                      <span className="stage-filename" title={activePanel.file?.name}>
                        {formatTruncatedFilename(activePanel.file?.name, 26)}
                      </span>
                      <span className="stage-meta-dot">&bull;</span>
                      <span className="stage-filesize">{formatFileSize(activePanel.file?.size)}</span>
                    </div>

                    {onRemovePanel && (
                      <button
                        type="button"
                        className="stage-remove-btn"
                        onClick={() => onRemovePanel(activePanel.id)}
                        title="Remove this image"
                        id="btn-remove-stage-image"
                      >
                        ✕ Remove Image
                      </button>
                    )}
                  </div>

                  <div className="stage-image-viewport">
                    <img
                      src={activePanel.previewUrl}
                      alt={`${activePanel.panelLabel || 'Panel'} full preview`}
                      className="stage-main-image"
                    />

                    {/* Small unobtrusive nav overlay */}
                    {displayPanels.length > 1 && (
                      <div className="stage-nav-controls">
                        <button
                          type="button"
                          className="stage-nav-btn stage-nav-prev"
                          onClick={handlePrevPanel}
                          disabled={activeIndex === 0}
                          title="Previous panel"
                          aria-label="Previous panel"
                        >
                          ‹
                        </button>
                        <span className="stage-nav-counter">
                          {activeIndex + 1} / {displayPanels.length}
                        </span>
                        <button
                          type="button"
                          className="stage-nav-btn stage-nav-next"
                          onClick={handleNextPanel}
                          disabled={activeIndex === displayPanels.length - 1}
                          title="Next panel"
                          aria-label="Next panel"
                        >
                          ›
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="pc-no-panel-selected">
                  <p>No panel currently selected.</p>
                </div>
              )}
            </div>

            {/* Right Column: Submitted Panels Sidebar (Fixed 340px) */}
            <aside className="pc-preview-sidebar-col" aria-label="Submitted Panels Sidebar">
              <div className="pc-panels-manager-card">
                <div className="manager-header">
                  <div className="manager-title-row">
                    <h3 className="manager-title">
                      {displayPanels.length > 1 ? 'Submitted Panels' : 'Panel Details'}
                    </h3>
                    <span className="manager-count-tag">{displayPanels.length}</span>
                  </div>

                  {displayPanels.length < 10 && (
                    <button
                      type="button"
                      className="pc-add-panel-btn-header"
                      onClick={() => addFileInputRef.current?.click()}
                      title="Add another package panel"
                    >
                      + Add
                    </button>
                  )}
                </div>

                {/* When only 1 panel is selected, show details and controls without a duplicate image card */}
                {displayPanels.length === 1 ? (
                  <div className="pc-single-panel-config">
                    <div className="compact-select-wrap">
                      <label htmlFor="pc-select-single" className="single-panel-select-label">
                        Panel Type:
                      </label>
                      <select
                        id="pc-select-single"
                        className="compact-panel-select"
                        value={activePanel?.panelLabel || PANEL_OPTIONS[0]}
                        onChange={(e) =>
                          onUpdatePanelLabel && onUpdatePanelLabel(activePanel.id, e.target.value)
                        }
                        aria-label="Panel type"
                      >
                        {PANEL_OPTIONS.map((opt) => (
                          <option key={opt} value={opt}>
                            {opt}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="compact-meta-row">
                      <span className="compact-filename" title={activePanel?.file?.name}>
                        {formatTruncatedFilename(activePanel?.file?.name, 22)}
                      </span>
                      <span className="compact-meta-sep">&bull;</span>
                      <span className="compact-filesize">{formatFileSize(activePanel?.file?.size)}</span>
                    </div>

                    {onRemovePanel && (
                      <button
                        type="button"
                        className="pc-sidebar-remove-btn"
                        onClick={() => onRemovePanel(activePanel.id)}
                        id="btn-sidebar-remove-image"
                      >
                        🗑️ Remove Image
                      </button>
                    )}
                  </div>
                ) : (
                  /* Compact List of Panels (only rendered when > 1 panel to avoid duplicate single preview) */
                  <div className="pc-panel-items-list">
                    {displayPanels.map((panel, idx) => {
                      const isCurrent = panel.id === (activePanel?.id || displayPanels[0]?.id);
                      return (
                        <div
                          key={panel.id || idx}
                          className={`pc-panel-card-compact ${isCurrent ? 'is-active-card' : ''}`}
                          onClick={() => setSelectedPanelId(panel.id)}
                        >
                          <div className="compact-thumb-wrap">
                            <img
                              src={panel.previewUrl}
                              alt={`${panel.panelLabel} thumbnail`}
                              className="compact-thumb-img"
                            />
                            <span className="compact-idx-chip">#{idx + 1}</span>
                          </div>

                          <div className="compact-details-col" onClick={(e) => e.stopPropagation()}>
                            <div className="compact-select-wrap">
                              <select
                                id={`pc-select-${idx}`}
                                className="compact-panel-select"
                                value={panel.panelLabel || PANEL_OPTIONS[0]}
                                onChange={(e) =>
                                  onUpdatePanelLabel && onUpdatePanelLabel(panel.id, e.target.value)
                                }
                                aria-label={`Panel ${idx + 1} type`}
                              >
                                {PANEL_OPTIONS.map((opt) => (
                                  <option key={opt} value={opt}>
                                    {opt}
                                  </option>
                                ))}
                              </select>
                            </div>

                            <div className="compact-meta-row">
                              <span className="compact-filename" title={panel.file?.name}>
                                {formatTruncatedFilename(panel.file?.name, 15)}
                              </span>
                              <span className="compact-meta-sep">&bull;</span>
                              <span className="compact-filesize">{formatFileSize(panel.file?.size)}</span>
                            </div>
                          </div>

                          {onRemovePanel && (
                            <button
                              type="button"
                              className="compact-remove-btn"
                              onClick={(e) => {
                                e.stopPropagation();
                                onRemovePanel(panel.id);
                              }}
                              title="Remove this panel"
                              aria-label={`Remove panel ${idx + 1}`}
                            >
                              ✕
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}

                {/* Quick Add Buttons */}
                {displayPanels.length < 10 && (
                  <div className="pc-compact-add-row">
                    <button
                      type="button"
                      className="btn-secondary btn-compact"
                      onClick={() => addFileInputRef.current?.click()}
                    >
                      📁 Browse Files
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-compact"
                      onClick={() => addCameraInputRef.current?.click()}
                    >
                      📷 Camera
                    </button>
                  </div>
                )}

                {/* Compact Guideline Callout */}
                <div className="pc-guideline-compact">
                  <span className="guideline-icon-compact">ℹ</span>
                  <p className="guideline-text-compact">
                    {displayPanels.length > 1
                      ? 'Declarations across all panels are aggregated. Conflicting values are flagged for inspector review.'
                      : 'Add other package sides to verify all mandatory Rule 6 declarations.'}
                  </p>
                </div>

                {/* Primary Action Button */}
                <div className="pc-sidebar-actions">
                  <button
                    type="button"
                    className="btn-primary pc-btn-verify-primary"
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
                    className="btn-ghost pc-btn-reset-secondary"
                    onClick={onReset}
                    disabled={loading}
                    id="btn-choose-another"
                  >
                    <span>Start Over</span>
                  </button>
                </div>
              </div>
            </aside>
          </div>
        </div>
      ) : (
        /* ─── MOBILE EXPERIENCE (PRESERVED) ─── */
        <>
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

                  {onRemovePanel && (
                    <button
                      type="button"
                      className="btn-remove-panel"
                      onClick={() => onRemovePanel(panel.id)}
                      title="Remove this panel"
                      aria-label={`Remove panel ${idx + 1}`}
                      id={`btn-remove-panel-${idx}`}
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

                  {onRemovePanel && (
                    <button
                      type="button"
                      className="btn-mobile-remove-image"
                      onClick={() => onRemovePanel(panel.id)}
                      id={`btn-mobile-remove-${idx}`}
                    >
                      🗑️ Remove Image
                    </button>
                  )}
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
        </>
      )}
    </div>
  );
}
