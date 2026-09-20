import React, { useRef, useState } from 'react';

function ShieldIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function MultiProductIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <path d="M12 22V12" />
    </svg>
  );
}

function SingleProductIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <rect width="16" height="20" x="4" y="2" rx="2" />
      <path d="M8 7h8" />
      <path d="M8 12h8" />
      <path d="M8 17h5" />
    </svg>
  );
}

function IntakeTrayIcon() {
  return (
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
      <path d="M12 12v9" />
      <path d="m8 16 4-4 4 4" />
    </svg>
  );
}

function IntakeDropActiveIcon() {
  return (
    <svg width="34" height="34" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242" />
      <path d="M12 12v9" />
      <path d="m16 17-4 4-4-4" />
    </svg>
  );
}

function FolderBrowseIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 20a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.9a2 2 0 0 1-1.69-.9L9.6 3.9A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13a2 2 0 0 0 2 2Z" />
      <path d="M12 10v6" />
      <path d="m9 13 3-3 3 3" />
    </svg>
  );
}

function CameraIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14.5 4h-5L7 7H4a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2h-3l-2.5-3z" />
      <circle cx="12" cy="13" r="3" />
    </svg>
  );
}

function EvaluatorReticleIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v4" />
      <path d="M12 18v4" />
      <path d="M2 12h4" />
      <path d="M18 12h4" />
    </svg>
  );
}

function PipelineCogIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
      <circle cx="12" cy="12" r="3" />
    </svg>
  );
}

/**
 * Responsive Home / Intake Screen for PackCheck.
 * - In PC Mode: Full workstation layout with an engineered Package Intake dropzone,
 *   multi-panel/multi-product selector, statutory evaluators matrix, and pipeline principle card.
 * - In Mobile Mode: Preserves the touch-friendly mobile-first experience
 *   with camera capture and viewfinder card.
 */
export default function HomeScreen({
  onSelectFiles,
  onSelectFile,
  recentChecks = [],
  onSelectRecent,
  inspectionMode = 'MULTI_PRODUCT',
  onSetInspectionMode,
  isPC = false,
}) {
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
  const dragCounterRef = useRef(0);
  const [isDragging, setIsDragging] = useState(false);

  const handleFiles = (fileList) => {
    if (!fileList || fileList.length === 0) return;
    const files = Array.from(fileList);
    if (onSelectFiles) {
      onSelectFiles(files);
    } else if (onSelectFile) {
      onSelectFile(files[0]);
    }
  };

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const triggerCameraScan = () => {
    cameraInputRef.current?.click();
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
      handleFiles(e.dataTransfer.files);
    }
  };

  const isMultiProduct = inspectionMode === 'MULTI_PRODUCT';

  return (
    <div className={`home-screen ${isPC ? 'home-pc-layout' : 'home-mobile-layout'}`}>
      {/* Hidden file inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
        id="camera-input"
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        multiple
        style={{ display: 'none' }}
        onChange={(e) => {
          handleFiles(e.target.files);
          e.target.value = '';
        }}
        id="upload-input"
      />

      {/* ─── PC WORKSTATION LAYOUT ─── */}
      {isPC ? (
        <div className="pc-home-grid">
          {/* Left Column: Workstation Hero & Package Intake Station */}
          <div className="pc-home-left">
            <section className="home-hero pc-hero">
              <div className="hero-shield-pill">
                <span className="shield-symbol"><ShieldIcon /></span>
                <span className="shield-text">Legal Metrology (Packaged Commodities) Rules, 2011</span>
              </div>

              <h2 className="home-hero-title pc-hero-title">
                Automated Package Compliance Workstation
              </h2>
              <p className="home-hero-sub pc-hero-sub">
                {isMultiProduct
                  ? 'Upload photos of multiple distinct products (e.g. Maggi, Cadbury, Dove). Each is inspected independently with its own GTIN reconciliation, statutory rules, and evidence image.'
                  : "Ingest multiple package panels (Front, Back, Sides), extract statutory declarations via AI/OCR, and verify compliance against India's Legal Metrology standards."}
              </p>

              {/* Inspection Mode Tabs Selector */}
              <div className="inspection-mode-selector" role="tablist" aria-label="Inspection Mode">
                <button
                  type="button"
                  role="tab"
                  aria-selected={isMultiProduct}
                  className={`mode-tab-btn ${isMultiProduct ? 'active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
                  id="btn-mode-multi-product"
                >
                  <span className="mode-tab-icon"><MultiProductIcon /></span>
                  <div className="mode-tab-text">
                    <span className="mode-tab-title">Multiple Products</span>
                    <span className="mode-tab-sub">Independent Reports</span>
                  </div>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={!isMultiProduct}
                  className={`mode-tab-btn ${!isMultiProduct ? 'active' : ''}`}
                  onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
                  id="btn-mode-single-product"
                >
                  <span className="mode-tab-icon"><SingleProductIcon /></span>
                  <div className="mode-tab-text">
                    <span className="mode-tab-title">Single Product</span>
                    <span className="mode-tab-sub">Multi-Panel Aggregation</span>
                  </div>
                </button>
              </div>
            </section>

            {/* Deliberate Package Intake Workspace */}
            <section
              className={`pc-dropzone-card ${isDragging ? 'is-dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragEnter={handleDragEnter}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={triggerFileUpload}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  triggerFileUpload();
                }
              }}
              aria-label="Drag and drop package images or click to browse"
            >
              <div className="pc-dropzone-header-bar">
                <span className="dropzone-station-tag">Package Intake Station</span>
                <span className={`dropzone-live-pill ${isDragging ? 'pill-dragging' : 'pill-ready'}`}>
                  <span className="live-status-dot" />
                  <span>{isDragging ? 'Drop to Ingest' : 'Ready for Intake'}</span>
                </span>
              </div>

              <div className="pc-dropzone-content">
                <div className="pc-dropzone-target-reticle">
                  <div className="pc-dropzone-icon">
                    {isDragging ? <IntakeDropActiveIcon /> : <IntakeTrayIcon />}
                  </div>
                  <h3 className="pc-dropzone-title">
                    {isDragging
                      ? 'Drop Package Images to Ingest'
                      : isMultiProduct
                      ? 'Drag & Drop Multiple Product Photos'
                      : 'Drag & Drop Package Panel Images'}
                  </h3>
                  <p className="pc-dropzone-hint">
                    {isMultiProduct
                      ? 'Upload photos of distinct products (e.g. Maggi, Cadbury, Dove) for independent statutory evaluation.'
                      : 'Drop single or multiple panels (Front, Back, Sides, Bottom) of the same package for composite evaluation.'}
                  </p>

                  <div className="pc-dropzone-actions" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="btn-primary btn-large pc-btn-browse"
                      onClick={triggerFileUpload}
                      id="btn-pc-browse"
                    >
                      <span className="btn-icon"><FolderBrowseIcon /></span>
                      <span>{isMultiProduct ? 'Browse Product Images' : 'Browse Package Images'}</span>
                    </button>

                    <button
                      type="button"
                      className="btn-secondary pc-btn-camera"
                      onClick={triggerCameraScan}
                      id="btn-pc-camera"
                      title="Capture image via connected camera or webcam"
                    >
                      <span className="btn-icon"><CameraIcon /></span>
                      <span>Use Camera</span>
                    </button>
                  </div>

                  <div className="pc-format-tags">
                    <span className="format-tag">JPEG, PNG, WEBP</span>
                    <span className="format-tag">Up to 10 MB per image</span>
                    <span className="format-tag">Multi-panel batch ingest</span>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {/* Right Column: Statutory Checks & Verification Architecture */}
          <div className="pc-home-right">
            {/* Automated Statutory Checks (Pre-Inspection Evaluators Scope) */}
            <section className="rules-preview-section pc-card">
              <div className="card-header-row">
                <div className="card-header-titles">
                  <h3 className="section-label">Automated Statutory Checks</h3>
                  <span className="section-sub-label">Pre-configured statutory evaluators executed deterministically upon intake:</span>
                </div>
                <span className="section-count-badge">9 Evaluators</span>
              </div>
              <div className="checks-grid pc-checks-grid">
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">Generic Identity</span>
                    <span className="check-rule-id">Rule 6(1)(a)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">Mfg / Packer Address</span>
                    <span className="check-rule-id">Rule 6(1)(b)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">Standard SI Units</span>
                    <span className="check-rule-id">Rules 11-13</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">MRP & Tax Disclaimer</span>
                    <span className="check-rule-id">Rule 6(1)(e)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">Consumer Helpline</span>
                    <span className="check-rule-id">Rule 6(1)(f)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-evaluator-badge" aria-label="Rule evaluator active">
                    <EvaluatorReticleIcon />
                  </span>
                  <div className="check-text-group">
                    <span className="check-text">Unit Sale Price (USP)</span>
                    <span className="check-rule-id">Rule 6(1)(h)</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Desktop Verification Pipeline Architecture Card */}
            <div className="pc-architecture-card">
              <div className="arch-header">
                <div className="arch-header-left">
                  <span className="arch-icon"><PipelineCogIcon /></span>
                  <span className="arch-title">Pipeline Principle</span>
                </div>
                <span className="arch-badge">Deterministic Enforcement</span>
              </div>
              <div className="arch-triad-grid">
                <div className="triad-step">
                  <div className="triad-step-num">1</div>
                  <div className="triad-step-content">
                    <strong className="triad-step-title">AI Vision Evidence</strong>
                    <span className="triad-step-desc">Multimodal OCR and spatial models extract statutory text and bounding boxes.</span>
                  </div>
                </div>
                <div className="triad-step">
                  <div className="triad-step-num">2</div>
                  <div className="triad-step-content">
                    <strong className="triad-step-title">Deterministic Engine</strong>
                    <span className="triad-step-desc">Evaluates compliance strictly against Legal Metrology Rules without hallucination.</span>
                  </div>
                </div>
                <div className="triad-step">
                  <div className="triad-step-num">3</div>
                  <div className="triad-step-content">
                    <strong className="triad-step-title">Human Inspector Review</strong>
                    <span className="triad-step-desc">Audit workflow with localized crops resolves uncertainty flags and discrepancies.</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Checks Section (preserved) */}
            {recentChecks && recentChecks.length > 0 && (
              <section className="recent-checks-section pc-card">
                <h3 className="section-label">Recent Verifications</h3>
                <div className="recent-checks-list">
                  {recentChecks.slice(0, 4).map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="recent-check-item"
                      onClick={() => onSelectRecent && onSelectRecent(item)}
                    >
                      <div className="recent-check-left">
                        <span className={`recent-verdict-dot dot-${item.verdict?.toLowerCase()}`} />
                        <div className="recent-info">
                          <span className="recent-name">{item.productName || 'Packaged Commodity'}</span>
                          <span className="recent-time">{item.timestamp}</span>
                        </div>
                      </div>
                      <span className={`recent-badge badge-${item.verdict?.toLowerCase()}`}>
                        {item.verdict}
                      </span>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        </div>
      ) : (
        /* ─── MOBILE EXPERIENCE (PRESERVED) ─── */
        <>
          {/* Hero Branding Section */}
          <section className="home-hero">
            <div className="hero-shield-pill">
              <span className="shield-symbol"><ShieldIcon /></span>
              <span className="shield-text">Legal Metrology Rules, 2011</span>
            </div>

            <h2 className="home-hero-title">Automated Package Compliance</h2>
            <p className="home-hero-sub">
              {isMultiProduct
                ? 'Inspect multiple distinct products in one session. Each product gets an independent report.'
                : 'Check packaged commodity labels against mandatory statutory declarations with deterministic Legal Metrology rules.'}
            </p>

            {/* Mobile Inspection Mode Selector */}
            <div className="inspection-mode-selector mobile-mode-selector" role="tablist" aria-label="Inspection Mode">
              <button
                type="button"
                role="tab"
                aria-selected={isMultiProduct}
                className={`mode-tab-btn ${isMultiProduct ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('MULTI_PRODUCT')}
                id="btn-mobile-mode-multi-product"
              >
                <span className="mode-tab-icon"><MultiProductIcon /></span>
                <span className="mode-tab-title">Multi-Product</span>
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={!isMultiProduct}
                className={`mode-tab-btn ${!isMultiProduct ? 'active' : ''}`}
                onClick={() => onSetInspectionMode && onSetInspectionMode('SINGLE_PRODUCT')}
                id="btn-mobile-mode-single-product"
              >
                <span className="mode-tab-icon"><SingleProductIcon /></span>
                <span className="mode-tab-title">Single Product</span>
              </button>
            </div>
          </section>

          {/* Central Visual Camera / Upload Hero Area */}
          <section
            className={`scan-hub-card ${isDragging ? 'is-dragging' : ''}`}
            onClick={triggerCameraScan}
            onDragOver={handleDragOver}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="scan-hub-viewfinder">
              <div className="viewfinder-corners" />
              <div className="viewfinder-icon">
                {isDragging ? <IntakeDropActiveIcon /> : <CameraIcon />}
              </div>
              <span className="viewfinder-label">
                {isDragging
                  ? isMultiProduct
                    ? 'Release to upload multiple product photos'
                    : 'Release to upload package panels'
                  : isMultiProduct
                  ? 'Tap to Scan Product Photo'
                  : 'Tap to Scan Principal Display Panel'}
              </span>
            </div>

            <div className="scan-hub-actions">
              <button
                type="button"
                className="btn-primary btn-large"
                onClick={(e) => {
                  e.stopPropagation();
                  triggerCameraScan();
                }}
                id="btn-scan-package"
              >
                <span className="btn-icon"><CameraIcon /></span>
                <span>Scan Package</span>
              </button>

              <button
                type="button"
                className="btn-secondary"
                onClick={(e) => {
                  e.stopPropagation();
                  triggerFileUpload();
                }}
                id="btn-upload-image"
              >
                <span className="btn-icon"><FolderBrowseIcon /></span>
                <span>Upload Image from Device</span>
              </button>
            </div>
          </section>

          {/* Quick Compliance Features Matrix */}
          <section className="rules-preview-section">
            <div className="card-header-row">
              <h3 className="section-label">Automated Statutory Checks</h3>
              <span className="section-count-badge">9 Evaluators</span>
            </div>
            <div className="checks-grid">
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">Generic Identity (R. 6(1)(a))</span>
              </div>
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">Mfg / Packer Address (R. 6(1)(b))</span>
              </div>
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">Standard SI Units (R. 11-13)</span>
              </div>
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">MRP & Tax Disclaimer (R. 6(1)(e))</span>
              </div>
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">Consumer Helpline (R. 6(1)(f))</span>
              </div>
              <div className="check-item">
                <span className="check-evaluator-badge"><EvaluatorReticleIcon /></span>
                <span className="check-text">Unit Sale Price (R. 6(1)(h))</span>
              </div>
            </div>
          </section>

          {/* Recent Checks (Local session state) */}
          {recentChecks && recentChecks.length > 0 && (
            <section className="recent-checks-section">
              <h3 className="section-label">Recent Verifications</h3>
              <div className="recent-checks-list">
                {recentChecks.slice(0, 3).map((item, idx) => (
                  <div
                    key={item.id || idx}
                    className="recent-check-item"
                    onClick={() => onSelectRecent && onSelectRecent(item)}
                  >
                    <div className="recent-check-left">
                      <span className={`recent-verdict-dot dot-${item.verdict?.toLowerCase()}`} />
                      <div className="recent-info">
                        <span className="recent-name">{item.productName || 'Packaged Commodity'}</span>
                        <span className="recent-time">{item.timestamp}</span>
                      </div>
                    </div>
                    <span className={`recent-badge badge-${item.verdict?.toLowerCase()}`}>
                      {item.verdict}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Trust & Architecture Statement */}
          <footer className="home-architecture-footer">
            <p className="footer-principle">
              <strong>Architecture:</strong> AI Vision extracts evidence &bull; Deterministic Rule Engine decides &bull; Human Reviewer resolves uncertainty.
            </p>
          </footer>
        </>
      )}
    </div>
  );
}
