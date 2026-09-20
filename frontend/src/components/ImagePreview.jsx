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
 * High-precision SVG icons for Inspection Preparation Workspace.
 */
function PackageBoxIcon({ className = '', size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <path d="M12 22V12" />
    </svg>
  );
}

function LayersIcon({ className = '', size = 16 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polygon points="12 2 2 7 12 12 22 7 12 2" />
      <polyline points="2 17 12 22 22 17" />
      <polyline points="2 12 12 17 22 12" />
    </svg>
  );
}

function UploadPlusIcon({ className = '', size = 15 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <polyline points="17 8 12 3 7 8" />
      <line x1="12" y1="3" x2="12" y2="15" />
    </svg>
  );
}

function CameraIcon({ className = '', size = 15 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
      <circle cx="12" cy="13" r="3" />
    </svg>
  );
}

function TrashIcon({ className = '', size = 14 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M3 6h18" />
      <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
      <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
    </svg>
  );
}

function VerifyIcon({ className = '', size = 17 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polygon points="5 3 19 12 5 21 5 3" />
    </svg>
  );
}

function ShieldCheckIcon({ className = '', size = 15 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function ChevronLeftIcon({ className = '', size = 15 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="15 18 9 12 15 6" />
    </svg>
  );
}

function ChevronRightIcon({ className = '', size = 15 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="9 18 15 12 9 6" />
    </svg>
  );
}

function RefreshIcon({ className = '', size = 14 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="1 4 1 10 7 10" />
      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10" />
    </svg>
  );
}

function CrossIcon({ className = '', size = 14 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}

function ReticleCorners() {
  return (
    <div className="optical-corners" aria-hidden="true">
      <span className="reticle-tl" />
      <span className="reticle-tr" />
      <span className="reticle-bl" />
      <span className="reticle-br" />
    </div>
  );
}

/**
 * Inspection Preparation Workspace (Milestone 3.5).
 * - Desktop: Calibrated two-column workstation layout with hero image viewport and inspection setup console.
 * - Mobile: Preserved vertical flow with prominent preview and primary CTA.
 */
export default function ImagePreview({
  panels = [],
  file,
  previewUrl,
  onVerify,
  onReset,
  onRemovePanel,
  onUpdatePanelLabel,
  onUpdateProductLabel,
  onAddMoreFiles,
  inspectionMode = 'MULTI_PRODUCT',
  onSetInspectionMode,
  loading = false,
  isPC = false,
  isMobile = false, // eslint-disable-line no-unused-vars
  effectiveMode, // eslint-disable-line no-unused-vars
}) {
  const addFileInputRef = useRef(null);
  const addCameraInputRef = useRef(null);
  const dragCounterRef = useRef(0);
  const [isDragging, setIsDragging] = useState(false);

  // Normalize to panels array
  const displayPanels =
    panels && panels.length > 0
      ? panels
      : file && previewUrl
      ? [{ id: 'single', file, previewUrl, panelLabel: 'Front Panel' }]
      : [];

  const [selectedPanelId, setSelectedPanelId] = useState(displayPanels[0]?.id || null);

  // Derive active panel directly during render
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

  const formatTruncatedFilename = (name, maxLen = 24) => {
    if (!name) return 'package_image.jpg';
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

  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current += 1;
    if (e.dataTransfer?.items && e.dataTransfer.items.length > 0) {
      setIsDragging(true);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'copy';
    }
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      dragCounterRef.current = 0;
      setIsDragging(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current = 0;
    setIsDragging(false);
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleMoreFiles(e.dataTransfer.files);
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

  const isMulti = inspectionMode === 'MULTI_PRODUCT';

  return (
    <div
      className={`preview-screen pc-prep-workspace ${isPC ? 'pc-preview-layout' : 'mobile-preview-layout'}`}
      onDragEnter={handleDragEnter}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Hidden file inputs for adding more items */}
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

      {/* ─── PC INSPECTION PREPARATION WORKSPACE ─── */}
      {isPC ? (
        <div className="pc-preview-container">
          {/* Workspace Top Header Bar */}
          <div className="pc-prep-topbar">
            <div className="pc-prep-topbar-left">
              <div className="pc-prep-badge">
                <span className="pc-prep-badge-dot" />
                <span>INSPECTION PREPARATION WORKSPACE</span>
                <span className="pc-prep-badge-sep">&bull;</span>
                <span className="pc-prep-badge-law">RULE 6 COMPLIANCE PROTOCOL</span>
              </div>
              <h2 className="pc-prep-title">
                {isMulti ? 'Multi-Product Batch Preparation' : 'Package Panel Inspection Setup'}
              </h2>
              <p className="pc-prep-sub">
                {isMulti
                  ? 'Review uploaded packaged commodities and configure product identifiers prior to statutory verification.'
                  : 'Review submitted packaging declarations and panel types prior to deterministic compliance evaluation.'}
              </p>
            </div>

            <div className="pc-prep-topbar-right">
              {/* Inspection Mode Segmented Switcher */}
              <div className="pc-mode-segmented-control" role="tablist" aria-label="Inspection Mode">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isMulti}
                  className={`pc-mode-segment-btn ${isMulti ? 'is-active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
                  id="btn-preview-mode-multi"
                >
                  <PackageBoxIcon size={14} className="pc-mode-btn-icon" />
                  <span>Multi-Product Batch</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={!isMulti}
                  className={`pc-mode-segment-btn ${!isMulti ? 'is-active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
                  id="btn-preview-mode-single"
                >
                  <LayersIcon size={14} className="pc-mode-btn-icon" />
                  <span>Single-Product Panels</span>
                </button>
              </div>

              {/* Items Staged Count Chip */}
              <div className="pc-prep-staged-chip">
                <span className="pc-staged-number">{displayPanels.length}</span>
                <span className="pc-staged-text">
                  {displayPanels.length === 1 ? (isMulti ? 'Product' : 'Panel') : isMulti ? 'Products' : 'Panels'} Staged
                </span>
              </div>
            </div>
          </div>

          {/* Two-Column Workstation Grid */}
          <div className="pc-prep-workstation-grid">
            {/* ── LEFT COLUMN: HERO PACKAGE PREVIEW ── */}
            <div className="pc-prep-hero-col">
              {activePanel ? (
                <div className="pc-prep-hero-card">
                  {/* Hero Viewer Header */}
                  <div className="pc-prep-hero-header">
                    <div className="pc-hero-header-left">
                      <span className="pc-hero-tag">
                        {isMulti
                          ? `PRODUCT ${(activeIndex + 1).toString().padStart(2, '0')}`
                          : `PANEL ${(activeIndex + 1).toString().padStart(2, '0')}`}
                      </span>
                      <h3 className="pc-hero-headline" title={isMulti ? activePanel.productLabel : activePanel.panelLabel}>
                        {isMulti
                          ? activePanel.productLabel || `Product ${activeIndex + 1}`
                          : activePanel.panelLabel || 'Front Panel'}
                      </h3>
                      <div className="pc-hero-fileinfo">
                        <span className="pc-hero-filename" title={activePanel.file?.name}>
                          {formatTruncatedFilename(activePanel.file?.name, 28)}
                        </span>
                        <span className="pc-hero-dot">&bull;</span>
                        <span className="pc-hero-filesize">{formatFileSize(activePanel.file?.size)}</span>
                      </div>
                    </div>

                    <div className="pc-hero-header-right">
                      {/* Navigation Chevrons if multi-item */}
                      {displayPanels.length > 1 && (
                        <div className="pc-hero-nav-pill">
                          <button
                            type="button"
                            className="pc-hero-nav-arrow"
                            onClick={handlePrevPanel}
                            disabled={activeIndex === 0}
                            title="Previous image"
                            aria-label="Previous image"
                          >
                            <ChevronLeftIcon size={14} />
                          </button>
                          <span className="pc-hero-nav-index">
                            {(activeIndex + 1).toString().padStart(2, '0')} /{' '}
                            {displayPanels.length.toString().padStart(2, '0')}
                          </span>
                          <button
                            type="button"
                            className="pc-hero-nav-arrow"
                            onClick={handleNextPanel}
                            disabled={activeIndex === displayPanels.length - 1}
                            title="Next image"
                            aria-label="Next image"
                          >
                            <ChevronRightIcon size={14} />
                          </button>
                        </div>
                      )}

                      {/* Remove current item */}
                      {onRemovePanel && (
                        <button
                          type="button"
                          className="pc-hero-remove-btn"
                          onClick={() => onRemovePanel(activePanel.id)}
                          title="Remove this image from inspection"
                          id="btn-remove-stage-image"
                        >
                          <CrossIcon size={12} />
                          <span>Remove</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Optical Inspection Hero Viewport */}
                  <div className="pc-prep-viewport">
                    <img
                      src={activePanel.previewUrl}
                      alt={`${(isMulti ? activePanel.productLabel : activePanel.panelLabel) || 'Item'} inspection view`}
                      className="pc-prep-hero-image"
                    />
                    <ReticleCorners />
                  </div>

                  {/* Item Strip (Thumbnails & Switcher) */}
                  <div className="pc-prep-strip-footer">
                    <div className="pc-prep-strip-header">
                      <span className="pc-strip-label">
                        {isMulti ? 'Staged Products for Inspection:' : 'Package Panels to Aggregate:'}
                      </span>
                      <span className="pc-strip-hint">Select card to inspect</span>
                    </div>

                    <div className="pc-prep-strip-row" role="tablist" aria-label="Staged Items">
                      {displayPanels.map((p, idx) => {
                        const isCurrent = p.id === activePanelId;
                        const labelText = isMulti
                          ? p.productLabel || `Product ${idx + 1}`
                          : p.panelLabel || `Panel #${idx + 1}`;

                        return (
                          <div
                            key={p.id || idx}
                            role="tab"
                            aria-selected={isCurrent}
                            className={`pc-strip-card ${isCurrent ? 'is-active-strip-card' : ''}`}
                            onClick={() => setSelectedPanelId(p.id)}
                            title={`Inspect ${labelText}`}
                          >
                            <div className="pc-strip-thumb-box">
                              <img src={p.previewUrl} alt={labelText} className="pc-strip-thumb-img" />
                              <span className="pc-strip-idx-chip">{(idx + 1).toString().padStart(2, '0')}</span>
                              {onRemovePanel && (
                                <button
                                  type="button"
                                  className="pc-strip-remove-btn"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    onRemovePanel(p.id);
                                  }}
                                  title={`Remove ${labelText}`}
                                  aria-label={`Remove ${labelText}`}
                                >
                                  ✕
                                </button>
                              )}
                            </div>
                            <span className="pc-strip-name" title={labelText}>
                              {labelText}
                            </span>
                          </div>
                        );
                      })}

                      {/* Compact Inline Add Card */}
                      {displayPanels.length < 10 && (
                        <button
                          type="button"
                          className="pc-strip-add-card"
                          onClick={() => addFileInputRef.current?.click()}
                          title={isMulti ? 'Add another product' : 'Add another package panel'}
                          id="btn-strip-add-item"
                        >
                          <div className="pc-strip-add-icon">
                            <UploadPlusIcon size={16} />
                          </div>
                          <span className="pc-strip-add-text">
                            {isMulti ? '+ Add Product' : '+ Add Panel'}
                          </span>
                        </button>
                      )}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="pc-no-panel-selected">
                  <p>No package items currently uploaded.</p>
                </div>
              )}
            </div>

            {/* ── RIGHT COLUMN: INSPECTION SETUP CONSOLE ── */}
            <aside className="pc-prep-sidebar-col" aria-label="Inspection Setup Console">
              <div className="pc-setup-console-card">
                {/* Console Title Bar */}
                <div className="pc-console-header">
                  <div className="pc-console-title-wrap">
                    <ShieldCheckIcon size={18} className="pc-console-shield-icon" />
                    <div>
                      <h3 className="pc-console-title">Inspection Setup</h3>
                      <span className="pc-console-sub">Pre-flight statutory configuration</span>
                    </div>
                  </div>
                  <div className="pc-console-status-pill">
                    <span className="status-live-dot" />
                    <span>READY</span>
                  </div>
                </div>

                {/* Staged Scope Overview */}
                <div className="pc-console-metrics-box">
                  <div className="pc-console-metric-item">
                    <span className="metric-label">INSPECTION MODE</span>
                    <span className="metric-val">{isMulti ? 'Multi-Product Batch' : 'Single-Product Multi-Panel'}</span>
                  </div>
                  <div className="pc-console-metric-row">
                    <div className="pc-console-metric-item half">
                      <span className="metric-label">{isMulti ? 'TOTAL PRODUCTS' : 'TOTAL PANELS'}</span>
                      <span className="metric-val-large">{displayPanels.length}</span>
                    </div>
                    <div className="pc-console-metric-item half">
                      <span className="metric-label">STATUTE</span>
                      <span className="metric-val-law">Rule 6 LM Rules</span>
                    </div>
                  </div>
                </div>

                {/* Active Target Configuration */}
                <div className="pc-target-config-block">
                  <div className="pc-target-block-header">
                    <span className="pc-target-block-label">ACTIVE ITEM SPECIFICATION</span>
                    <span className="pc-target-index-chip">
                      #{activeIndex + 1} of {displayPanels.length}
                    </span>
                  </div>

                  {isMulti ? (
                    <div className="pc-input-group">
                      <label htmlFor="pc-product-label-input" className="pc-input-label">
                        Product Name / Identifier:
                      </label>
                      <input
                        id="pc-product-label-input"
                        type="text"
                        className="pc-text-input"
                        value={activePanel?.productLabel || ''}
                        placeholder={`e.g. Product ${activeIndex + 1}`}
                        onChange={(e) =>
                          onUpdateProductLabel && onUpdateProductLabel(activePanel.id, e.target.value)
                        }
                      />
                      <span className="pc-input-hint">
                        Used to label independent Legal Metrology verdict and evidence record.
                      </span>
                    </div>
                  ) : (
                    <div className="pc-input-group">
                      <label htmlFor="pc-panel-select-input" className="pc-input-label">
                        Packaging Panel Type:
                      </label>
                      <select
                        id="pc-panel-select-input"
                        className="pc-select-input"
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
                      <span className="pc-input-hint">
                        Declarations from multiple sides are aggregated to verify mandatory rules.
                      </span>
                    </div>
                  )}
                </div>

                {/* Primary Action CTA Button (The Hero Trigger) */}
                <div className="pc-cta-section">
                  <button
                    type="button"
                    className="pc-btn-primary-start"
                    onClick={onVerify}
                    disabled={loading || displayPanels.length === 0}
                    id="btn-start-verification"
                  >
                    <div className="pc-cta-icon-wrap">
                      <VerifyIcon size={18} />
                    </div>
                    <div className="pc-cta-text-wrap">
                      <span className="pc-cta-title">
                        {isMulti ? 'START BATCH VERIFICATION' : 'START VERIFICATION'}
                      </span>
                      <span className="pc-cta-sub">
                        {isMulti
                          ? `Verify ${displayPanels.length} ${displayPanels.length === 1 ? 'Product' : 'Products in Batch'}`
                          : `Evaluate Statutory Compliance (${displayPanels.length} ${displayPanels.length === 1 ? 'Panel' : 'Panels'})`}
                      </span>
                    </div>
                  </button>
                </div>

                {/* Secondary Ingest Operations */}
                <div className="pc-secondary-controls">
                  <span className="pc-secondary-title">ADDITIONAL IMAGES</span>
                  <div className="pc-secondary-btn-row">
                    <button
                      type="button"
                      className="pc-btn-secondary-action"
                      onClick={() => addFileInputRef.current?.click()}
                      title="Upload more images from disk"
                      id="btn-sidebar-browse"
                    >
                      <UploadPlusIcon size={14} />
                      <span>Browse Files</span>
                    </button>
                    <button
                      type="button"
                      className="pc-btn-secondary-action"
                      onClick={() => addCameraInputRef.current?.click()}
                      title="Capture from camera"
                      id="btn-sidebar-camera"
                    >
                      <CameraIcon size={14} />
                      <span>Camera</span>
                    </button>
                  </div>
                </div>

                {/* Regulatory Inspection Guarantee */}
                <div className="pc-guarantee-note">
                  <ShieldCheckIcon size={14} className="pc-guarantee-icon" />
                  <p className="pc-guarantee-text">
                    Statutory rules are 100% deterministic code &bull; Zero LLM compliance bias
                  </p>
                </div>

                {/* Start Over Reset Action */}
                <div className="pc-reset-row">
                  <button
                    type="button"
                    className="pc-btn-reset-ghost"
                    onClick={onReset}
                    disabled={loading}
                    id="btn-choose-another"
                  >
                    <RefreshIcon size={13} />
                    <span>Reset and Choose Another Package</span>
                  </button>
                </div>
              </div>
            </aside>
          </div>
        </div>
      ) : (
        /* ─── MOBILE INSPECTION PREPARATION ─── */
        <div className="mobile-prep-container">
          <div className="mobile-prep-header">
            <div className="mobile-prep-badge">
              <span className="mobile-prep-dot" />
              <span>INSPECTION PREPARATION</span>
            </div>
            <h3 className="mobile-prep-title">
              {isMulti ? 'Multi-Product Inspection' : 'Package Inspection'}
            </h3>

            {/* Mobile Mode Switcher */}
            <div className="mobile-mode-switcher" role="tablist" aria-label="Inspection Mode">
              <button
                type="button"
                className={`mobile-mode-btn ${isMulti ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
              >
                <PackageBoxIcon size={14} />
                <span>Multi-Product</span>
              </button>
              <button
                type="button"
                className={`mobile-mode-btn ${!isMulti ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
              >
                <LayersIcon size={14} />
                <span>Single Product</span>
              </button>
            </div>
          </div>

          {/* Mobile Main Image Viewport */}
          {activePanel && (
            <div className="mobile-prep-hero-card">
              <div className="mobile-prep-viewport">
                <img
                  src={activePanel.previewUrl}
                  alt={isMulti ? activePanel.productLabel : activePanel.panelLabel}
                  className="mobile-prep-image"
                />
                <ReticleCorners />
              </div>

              <div className="mobile-hero-meta">
                <div className="mobile-hero-labels">
                  <span className="mobile-index-tag">#{activeIndex + 1}</span>
                  <span className="mobile-hero-name">
                    {isMulti
                      ? activePanel.productLabel || `Product ${activeIndex + 1}`
                      : activePanel.panelLabel || 'Front Panel'}
                  </span>
                </div>
                {onRemovePanel && (
                  <button
                    type="button"
                    className="mobile-remove-btn"
                    onClick={() => onRemovePanel(activePanel.id)}
                    title="Remove item"
                  >
                    <TrashIcon size={13} />
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Mobile Thumbnails Strip */}
          <div className="mobile-strip-wrapper">
            <div className="mobile-strip-scroll">
              {displayPanels.map((panel, idx) => {
                const isCurrent = panel.id === (activePanel?.id || displayPanels[0]?.id);
                return (
                  <div
                    key={panel.id || idx}
                    className={`mobile-strip-item ${isCurrent ? 'is-active' : ''}`}
                    onClick={() => setSelectedPanelId(panel.id)}
                  >
                    <img src={panel.previewUrl} alt={`Item ${idx + 1}`} className="mobile-strip-img" />
                    <span className="mobile-strip-idx">#{idx + 1}</span>
                  </div>
                );
              })}
              {displayPanels.length < 10 && (
                <button
                  type="button"
                  className="mobile-strip-add"
                  onClick={() => addFileInputRef.current?.click()}
                  title="Add more"
                >
                  <UploadPlusIcon size={16} />
                </button>
              )}
            </div>
          </div>

          {/* Mobile Item Details Input */}
          <div className="mobile-item-edit-card">
            <label htmlFor="mobile-label-input" className="mobile-edit-label">
              {isMulti ? 'Product Name:' : 'Panel Type:'}
            </label>
            {isMulti ? (
              <input
                id="mobile-label-input"
                type="text"
                className="mobile-text-input"
                value={activePanel?.productLabel || `Product ${activeIndex + 1}`}
                onChange={(e) =>
                  onUpdateProductLabel && onUpdateProductLabel(activePanel.id, e.target.value)
                }
              />
            ) : (
              <select
                id="mobile-label-input"
                className="mobile-select-input"
                value={activePanel?.panelLabel || PANEL_OPTIONS[0]}
                onChange={(e) =>
                  onUpdatePanelLabel && onUpdatePanelLabel(activePanel.id, e.target.value)
                }
              >
                {PANEL_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>
                    {opt}
                  </option>
                ))}
              </select>
            )}
          </div>

          {/* Mobile Primary Actions Footer */}
          <div className="mobile-actions-footer">
            <button
              type="button"
              className="btn-primary mobile-btn-start"
              onClick={onVerify}
              disabled={loading || displayPanels.length === 0}
              id="btn-start-verification"
            >
              <VerifyIcon size={16} />
              <span>
                {isMulti
                  ? `START BATCH VERIFICATION (${displayPanels.length})`
                  : `START VERIFICATION (${displayPanels.length})`}
              </span>
            </button>

            <div className="mobile-secondary-row">
              <button
                type="button"
                className="mobile-btn-sub"
                onClick={() => addFileInputRef.current?.click()}
              >
                <UploadPlusIcon size={14} />
                <span>Add Photos</span>
              </button>
              <button
                type="button"
                className="mobile-btn-sub"
                onClick={() => addCameraInputRef.current?.click()}
              >
                <CameraIcon size={14} />
                <span>Camera</span>
              </button>
              <button type="button" className="mobile-btn-ghost" onClick={onReset}>
                <span>Reset</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
