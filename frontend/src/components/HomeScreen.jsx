import React, { useRef, useState } from 'react';

/**
 * Responsive Home / Landing Screen for PackCheck.
 * - In PC Mode: Full workstation layout with a large drag-and-drop dropzone,
 *   multi-panel file selection, statutory checks matrix, and recent verifications.
 * - In Mobile Mode: Preserves the existing touch-friendly mobile-first experience
 *   with camera capture and viewfinder card.
 */
export default function HomeScreen({
  onSelectFiles,
  onSelectFile,
  recentChecks = [],
  onSelectRecent,
  isPC = false,
}) {
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);
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

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (!isDragging) setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    if (e.dataTransfer?.files && e.dataTransfer.files.length > 0) {
      handleFiles(e.dataTransfer.files);
    }
  };

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
          {/* Left Column: Workstation Hero & Drag-and-Drop Area */}
          <div className="pc-home-left">
            <section className="home-hero pc-hero">
              <div className="hero-shield-pill">
                <span className="shield-symbol">🛡️</span>
                <span className="shield-text">Legal Metrology (Packaged Commodities) Rules, 2011</span>
              </div>

              <h2 className="home-hero-title pc-hero-title">
                Automated Package Compliance Workstation
              </h2>
              <p className="home-hero-sub pc-hero-sub">
                Ingest multiple package panels (Front, Back, Sides), extract statutory declarations via AI/OCR,
                and verify compliance against India's Legal Metrology standards with deterministic legal evaluators.
              </p>
            </section>

            {/* Large Drag-and-Drop Dropzone for Desktop */}
            <section
              className={`pc-dropzone-card ${isDragging ? 'is-dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragEnter={handleDragOver}
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
              <div className="pc-dropzone-content">
                <div className="pc-dropzone-icon">
                  {isDragging ? '📂' : '📥'}
                </div>
                <h3 className="pc-dropzone-title">
                  {isDragging ? 'Drop Package Images to Upload' : 'Drag & Drop Package Images Here'}
                </h3>
                <p className="pc-dropzone-hint">
                  Drop single or multiple panels (Front, Back, Sides, Bottom) or browse from your computer
                </p>

                <div className="pc-dropzone-actions" onClick={(e) => e.stopPropagation()}>
                  <button
                    type="button"
                    className="btn-primary btn-large pc-btn-browse"
                    onClick={triggerFileUpload}
                    id="btn-pc-browse"
                  >
                    <span className="btn-icon">📁</span>
                    <span>Browse Package Images</span>
                  </button>

                  <button
                    type="button"
                    className="btn-secondary pc-btn-camera"
                    onClick={triggerCameraScan}
                    id="btn-pc-camera"
                    title="Capture image via connected camera or webcam"
                  >
                    <span className="btn-icon">📷</span>
                    <span>Use Camera</span>
                  </button>
                </div>

                <div className="pc-format-tags">
                  <span className="format-tag">JPEG, PNG, WEBP</span>
                  <span className="format-tag">Up to 10 MB per image</span>
                  <span className="format-tag">Up to 10 panels at once</span>
                </div>
              </div>
            </section>
          </div>

          {/* Right Column: Statutory Checks & Recent Verifications */}
          <div className="pc-home-right">
            {/* Quick Compliance Features Matrix */}
            <section className="rules-preview-section pc-card">
              <div className="card-header-row">
                <h3 className="section-label">Automated Statutory Checks</h3>
                <span className="section-count-badge">9 Evaluators</span>
              </div>
              <div className="checks-grid pc-checks-grid">
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">Generic Identity</span>
                    <span className="check-rule-id">Rule 6(1)(a)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">Mfg / Packer Address</span>
                    <span className="check-rule-id">Rule 6(1)(b)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">Standard SI Units</span>
                    <span className="check-rule-id">Rules 11-13</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">MRP & Tax Disclaimer</span>
                    <span className="check-rule-id">Rule 6(1)(e)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">Consumer Helpline</span>
                    <span className="check-rule-id">Rule 6(1)(f)</span>
                  </div>
                </div>
                <div className="check-item">
                  <span className="check-icon">✓</span>
                  <div className="check-text-group">
                    <span className="check-text">Unit Sale Price (USP)</span>
                    <span className="check-rule-id">Rule 6(1)(h)</span>
                  </div>
                </div>
              </div>
            </section>

            {/* Recent Checks Section */}
            {recentChecks && recentChecks.length > 0 && (
              <section className="recent-checks-section pc-card">
                <h3 className="section-label">Recent Verifications</h3>
                <div className="recent-checks-list">
                  {recentChecks.slice(0, 4).map((item, idx) => (
                    <div
                      key={item.id || idx}
                      className="recent-check-item"
                      onClick={() => onSelectRecent(item)}
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

            {/* Desktop Architecture Statement Card */}
            <div className="pc-architecture-card">
              <div className="arch-header">
                <span className="arch-icon">⚙️</span>
                <span className="arch-title">Pipeline Principle</span>
              </div>
              <p className="arch-body">
                <strong>AI Vision</strong> extracts evidence &bull; <strong>Deterministic Rule Engine</strong> decides statutory compliance &bull; <strong>Human Reviewer</strong> resolves uncertainty.
              </p>
            </div>
          </div>
        </div>
      ) : (
        /* ─── MOBILE EXPERIENCE (PRESERVED) ─── */
        <>
          {/* Hero Branding Section */}
          <section className="home-hero">
            <div className="hero-shield-pill">
              <span className="shield-symbol">🛡️</span>
              <span className="shield-text">Legal Metrology Rules, 2011</span>
            </div>

            <h2 className="home-hero-title">Automated Package Compliance</h2>
            <p className="home-hero-sub">
              Check packaged commodity labels against mandatory statutory declarations with deterministic Legal Metrology rules.
            </p>
          </section>

          {/* Central Visual Camera / Upload Hero Area */}
          <section
            className={`scan-hub-card ${isDragging ? 'is-dragging' : ''}`}
            onClick={triggerCameraScan}
            onDragOver={handleDragOver}
            onDragEnter={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className="scan-hub-viewfinder">
              <div className="viewfinder-corners" />
              <div className="viewfinder-icon">{isDragging ? '📂' : '📷'}</div>
              <span className="viewfinder-label">
                {isDragging ? 'Release to upload package panels' : 'Tap to Scan Principal Display Panel'}
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
                <span className="btn-icon">📷</span>
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
                <span className="btn-icon">📁</span>
                <span>Upload Image from Device</span>
              </button>
            </div>
          </section>

          {/* Quick Compliance Features Matrix */}
          <section className="rules-preview-section">
            <h3 className="section-label">Automated Statutory Checks</h3>
            <div className="checks-grid">
              <div className="check-item">
                <span className="check-icon">✓</span>
                <span className="check-text">Generic Identity (R. 6(1)(a))</span>
              </div>
              <div className="check-item">
                <span className="check-icon">✓</span>
                <span className="check-text">Mfg / Packer Address (R. 6(1)(b))</span>
              </div>
              <div className="check-item">
                <span className="check-icon">✓</span>
                <span className="check-text">Standard SI Units (R. 11-13)</span>
              </div>
              <div className="check-item">
                <span className="check-icon">✓</span>
                <span className="check-text">MRP & Tax Disclaimer (R. 6(1)(e))</span>
              </div>
              <div className="check-item">
                <span className="check-icon">✓</span>
                <span className="check-text">Consumer Helpline (R. 6(1)(f))</span>
              </div>
              <div className="check-item">
                <span className="check-icon">✓</span>
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
                    onClick={() => onSelectRecent(item)}
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
              <strong>Architecture:</strong> AI extracts evidence &bull; Deterministic rules decide &bull; Humans resolve uncertainty.
            </p>
          </footer>
        </>
      )}
    </div>
  );
}
