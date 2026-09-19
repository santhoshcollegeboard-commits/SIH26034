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
  onUpdateProductLabel,
  onAddMoreFiles,
  inspectionMode = 'MULTI_PRODUCT',
  onSetInspectionMode,
  loading = false,
  isPC = false,
}) {
  const addFileInputRef = useRef(null);
  const addCameraInputRef = useRef(null);
  const dragCounterRef = useRef(0);
  const [isDragging, setIsDragging] = useState(false);

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
              <h2 className="pc-preview-heading">
                {isMulti ? 'Multi-Product Batch Inspection' : 'Product Panel Inspection'}
              </h2>
              <p className="pc-preview-sub">
                {isMulti
                  ? 'Inspect multiple distinct products in one session. Each product receives an independent Legal Metrology report and evidence image.'
                  : 'Inspect high-resolution packaging declarations and verify panel types before compliance analysis.'}
              </p>
            </div>
            <div className="pc-header-actions">
              {/* Inspection Mode Switcher */}
              <div className="preview-mode-toggle" role="tablist" aria-label="Inspection Mode">
                <button
                  type="button"
                  className={`preview-mode-btn ${isMulti ? 'active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
                  id="btn-preview-mode-multi"
                >
                  📦 Multi-Product
                </button>
                <button
                  type="button"
                  className={`preview-mode-btn ${!isMulti ? 'active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
                  id="btn-preview-mode-single"
                >
                  📄 Multi-Panel
                </button>
              </div>

              <span className="panel-count-badge">
                {displayPanels.length} {displayPanels.length === 1 ? (isMulti ? 'Product' : 'Panel') : (isMulti ? 'Products' : 'Panels')} Selected
              </span>
            </div>
          </div>

          <div className="pc-preview-workstation-grid">
            {/* Left Column: Focused Image Stage & Multi-Product Drop Zone */}
            <div className="pc-preview-stage-col">
              {/* If Multi-Product mode: display prominent active drop zone banner */}
              {isMulti && (
                <div
                  className={`multi-product-dropzone-banner ${isDragging ? 'is-dragging' : ''}`}
                  onDragEnter={handleDragEnter}
                  onDragOver={handleDragOver}
                  onDragLeave={handleDragLeave}
                  onDrop={handleDrop}
                  onClick={() => addFileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      addFileInputRef.current?.click();
                    }
                  }}
                  aria-label="Drop additional product photos here or click to browse"
                  id="multi-product-dropzone"
                >
                  <div className="multi-dropzone-inner">
                    <span className="multi-dropzone-icon">{isDragging ? '📂' : '📦'}</span>
                    <div className="multi-dropzone-info">
                      <h4 className="multi-dropzone-title">
                        {isDragging
                          ? 'RELEASE TO ADD PRODUCT PHOTO'
                          : 'DROP ADDITIONAL PRODUCT PHOTOS HERE'}
                      </h4>
                      <p className="multi-dropzone-sub">
                        Drag & Drop or <span className="browse-link-text">Browse Files</span> &bull; Drop multiple products at any time
                      </p>
                    </div>
                    <button
                      type="button"
                      className="btn-secondary btn-compact multi-dropzone-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        addFileInputRef.current?.click();
                      }}
                      id="btn-multi-dropzone-browse"
                    >
                      📁 Browse Files
                    </button>
                  </div>
                </div>
              )}

              {/* If Multi-Product mode: display horizontal product cards strip */}
              {isMulti && displayPanels.length > 0 && (
                <div className="pc-product-strip-container">
                  <div className="pc-product-strip-header">
                    <span className="pc-product-strip-label">
                      Uploaded Products ({displayPanels.length}):
                    </span>
                    <span className="pc-product-strip-hint">
                      Click a card to inspect its photo
                    </span>
                  </div>
                  <div className="pc-product-cards-strip" role="tablist" aria-label="Uploaded Products">
                    {displayPanels.map((p, idx) => {
                      const isCurrent = p.id === activePanelId;
                      const pName = p.productLabel || `Product ${idx + 1}`;
                      return (
                        <div
                          key={p.id || idx}
                          role="tab"
                          aria-selected={isCurrent}
                          className={`pc-product-strip-card ${isCurrent ? 'is-selected-product' : ''}`}
                          onClick={() => setSelectedPanelId(p.id)}
                          title={`Inspect ${pName}`}
                        >
                          <div className="product-strip-thumb-box">
                            <img src={p.previewUrl} alt={pName} className="product-strip-img" />
                            <span className="product-strip-index">#{idx + 1}</span>
                            {onRemovePanel && (
                              <button
                                type="button"
                                className="product-strip-remove-btn"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  onRemovePanel(p.id);
                                }}
                                title={`Remove ${pName}`}
                                aria-label={`Remove ${pName}`}
                              >
                                ✕
                              </button>
                            )}
                          </div>
                          <span className="product-strip-name" title={pName}>
                            {pName}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {activePanel ? (
                <div
                  className={`pc-large-image-card ${isMulti && isDragging ? 'is-drag-target' : ''}`}
                  onDragEnter={isMulti ? handleDragEnter : undefined}
                  onDragOver={isMulti ? handleDragOver : undefined}
                  onDragLeave={isMulti ? handleDragLeave : undefined}
                  onDrop={isMulti ? handleDrop : undefined}
                >
                  {isMulti && isDragging && (
                    <div className="stage-drag-overlay">
                      <span className="stage-drag-icon">📦</span>
                      <span className="stage-drag-text">Drop product image here to add</span>
                    </div>
                  )}
                  <div className="stage-top-meta">
                    <div className="stage-panel-headline">
                      <span className="stage-pin-icon">{isMulti ? '📦' : '📌'}</span>
                      <h3 className="stage-panel-title">
                        {isMulti
                          ? activePanel.productLabel || `Product ${activeIndex + 1}`
                          : activePanel.panelLabel || 'Package Panel'}
                      </h3>
                      <span className="stage-pager-chip">
                        {isMulti ? 'Product' : 'Panel'} {activeIndex + 1} of {displayPanels.length}
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
                      alt={`${(isMulti ? activePanel.productLabel : activePanel.panelLabel) || 'Panel'} full preview`}
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
                          title="Previous item"
                          aria-label="Previous item"
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
                          title="Next item"
                          aria-label="Next item"
                        >
                          ›
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="pc-no-panel-selected">
                  <p>No item currently selected.</p>
                </div>
              )}
            </div>

            {/* Right Column: Submitted Panels / Products Sidebar (Fixed 340px) */}
            <aside className="pc-preview-sidebar-col" aria-label="Submitted Items Sidebar">
              <div className="pc-panels-manager-card">
                <div className="manager-header">
                  <div className="manager-title-row">
                    <h3 className="manager-title">
                      {isMulti
                        ? 'Products to Inspect'
                        : displayPanels.length > 1 ? 'Submitted Panels' : 'Panel Details'}
                    </h3>
                    <span className="manager-count-tag">{displayPanels.length}</span>
                  </div>

                  {displayPanels.length < 10 && (
                    <button
                      type="button"
                      className="pc-add-panel-btn-header"
                      onClick={() => addFileInputRef.current?.click()}
                      title={isMulti ? 'Add another product' : 'Add another package panel'}
                    >
                      + Add
                    </button>
                  )}
                </div>

                {/* When only 1 panel is selected */}
                {displayPanels.length === 1 ? (
                  <div className="pc-single-panel-config">
                    {isMulti ? (
                      <div className="compact-select-wrap">
                        <label htmlFor="pc-prod-input-single" className="single-panel-select-label">
                          Product Name:
                        </label>
                        <input
                          id="pc-prod-input-single"
                          type="text"
                          className="compact-text-input"
                          value={activePanel?.productLabel || ''}
                          placeholder="Product Name (e.g. Maggi, Cadbury)"
                          onChange={(e) =>
                            onUpdateProductLabel && onUpdateProductLabel(activePanel.id, e.target.value)
                          }
                        />
                      </div>
                    ) : (
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
                    )}

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
                  /* Compact List of Items */
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
                              alt={`${panel.productLabel || panel.panelLabel} thumbnail`}
                              className="compact-thumb-img"
                            />
                            <span className="compact-idx-chip">#{idx + 1}</span>
                          </div>

                          <div className="compact-details-col" onClick={(e) => e.stopPropagation()}>
                            {isMulti ? (
                              <div className="compact-select-wrap">
                                <input
                                  id={`pc-prod-input-${idx}`}
                                  type="text"
                                  className="compact-text-input"
                                  value={panel.productLabel || `Product ${idx + 1}`}
                                  placeholder={`Product ${idx + 1}`}
                                  onChange={(e) =>
                                    onUpdateProductLabel && onUpdateProductLabel(panel.id, e.target.value)
                                  }
                                />
                              </div>
                            ) : (
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
                            )}

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
                              title="Remove this item"
                              aria-label={`Remove item ${idx + 1}`}
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
                    {isMulti
                      ? 'Each product will be evaluated independently against Legal Metrology rules with its own GTIN identity and evidence image.'
                      : displayPanels.length > 1
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
                      {isMulti
                        ? `Verify ${displayPanels.length} ${displayPanels.length === 1 ? 'Product' : 'Independent Products'}`
                        : `Verify Product (${displayPanels.length} ${displayPanels.length === 1 ? 'Panel' : 'Panels'})`}
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
              <h3 className="preview-heading">
                {isMulti ? 'Multi-Product Inspection' : 'Product Panels'}
              </h3>
              <span className="panel-count-badge">
                {displayPanels.length} {displayPanels.length === 1 ? (isMulti ? 'Product' : 'Panel') : (isMulti ? 'Products' : 'Panels')} Selected
              </span>
            </div>
            <p className="preview-sub">
              {isMulti
                ? 'Each product will receive an independent statutory compliance report and evidence image.'
                : 'Verify declarations distributed across multiple sides of the packaging.'}
            </p>

            {/* Mobile Mode Switcher */}
            <div className="inspection-mode-selector mobile-mode-selector" role="tablist" aria-label="Inspection Mode">
              <button
                type="button"
                className={`mode-tab-btn ${isMulti ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
              >
                <span className="mode-tab-icon">📦</span>
                <span className="mode-tab-title">Multi-Product</span>
              </button>
              <button
                type="button"
                className={`mode-tab-btn ${!isMulti ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
              >
                <span className="mode-tab-icon">📄</span>
                <span className="mode-tab-title">Single Product</span>
              </button>
            </div>
          </div>

          {/* Mobile Dropzone for Multi-Product Mode */}
          {isMulti && (
            <div
              className={`mobile-multi-dropzone ${isDragging ? 'is-dragging' : ''}`}
              onDragEnter={handleDragEnter}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => addFileInputRef.current?.click()}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  addFileInputRef.current?.click();
                }
              }}
              aria-label="Drop additional product photos here or tap to browse"
              id="mobile-multi-dropzone"
            >
              <div className="mobile-dropzone-content">
                <span className="mobile-dropzone-icon">{isDragging ? '📂' : '📦'}</span>
                <div className="mobile-dropzone-text">
                  <h4 className="mobile-dropzone-title">
                    {isDragging ? 'RELEASE TO ADD PRODUCT' : 'DROP ADDITIONAL PRODUCT PHOTOS HERE'}
                  </h4>
                  <p className="mobile-dropzone-sub">
                    Tap to Browse or Drag & Drop Product Photos
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Multi-Panel / Multi-Product Grid / Cards */}
          <div className="panels-grid">
            {displayPanels.map((panel, idx) => (
              <div key={panel.id || idx} className="panel-card">
                <div className="panel-thumb-container">
                  <img
                    src={panel.previewUrl}
                    alt={`${(isMulti ? panel.productLabel : panel.panelLabel) || 'Item'} preview`}
                    className="panel-img"
                  />
                  <span className="panel-number-chip">#{idx + 1}</span>

                  {onRemovePanel && (
                    <button
                      type="button"
                      className="btn-remove-panel"
                      onClick={() => onRemovePanel(panel.id)}
                      title="Remove this item"
                      aria-label={`Remove item ${idx + 1}`}
                      id={`btn-remove-panel-${idx}`}
                    >
                      ✕
                    </button>
                  )}
                </div>

                <div className="panel-controls">
                  <div className="panel-select-row">
                    <label htmlFor={`label-select-${idx}`} className="panel-select-label">
                      {isMulti ? 'Product:' : 'Panel:'}
                    </label>
                    {isMulti ? (
                      <input
                        id={`label-select-${idx}`}
                        type="text"
                        className="compact-text-input mobile-product-input"
                        value={panel.productLabel || `Product ${idx + 1}`}
                        onChange={(e) =>
                          onUpdateProductLabel && onUpdateProductLabel(panel.id, e.target.value)
                        }
                      />
                    ) : (
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
                    )}
                  </div>

                  <div className="panel-meta-row">
                    <span className="panel-filename" title={panel.file?.name}>
                      {panel.file?.name || `Item ${idx + 1}`}
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

            {/* Add More Item Card */}
            {displayPanels.length < 10 && (
              <div className="add-panel-card">
                <div className="add-panel-content">
                  <span className="add-panel-icon">＋</span>
                  <span className="add-panel-text">
                    {isMulti ? 'Add Another Product' : 'Add Another Panel'}
                  </span>
                  <span className="add-panel-hint">
                    {isMulti ? 'Photo of different product' : 'e.g. Back or Side'}
                  </span>
                  <div className="add-panel-actions">
                    <button
                      type="button"
                      className="btn-add-camera"
                      onClick={() => addCameraInputRef.current?.click()}
                      title="Take photo"
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
              {isMulti
                ? 'Each product will be evaluated independently against Legal Metrology rules with its own GTIN identity and evidence image.'
                : displayPanels.length > 1
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
                {isMulti
                  ? `Verify ${displayPanels.length} ${displayPanels.length === 1 ? 'Product' : 'Independent Products'}`
                  : `Verify Product (${displayPanels.length} ${displayPanels.length === 1 ? 'Panel' : 'Panels'})`}
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
