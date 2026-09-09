import React, { useRef } from 'react';

/**
 * Mobile-first Home / Landing Screen for PackCheck.
 * Directs users immediately into the package image capture/upload workflow.
 */
export default function HomeScreen({ onSelectFile, recentChecks = [], onSelectRecent }) {
  const fileInputRef = useRef(null);
  const cameraInputRef = useRef(null);

  const triggerFileUpload = () => {
    fileInputRef.current?.click();
  };

  const triggerCameraScan = () => {
    // If mobile supports camera capture, capture attribute prompts rear camera
    cameraInputRef.current?.click();
  };

  return (
    <div className="home-screen">
      {/* Hidden file inputs */}
      <input
        ref={cameraInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        style={{ display: 'none' }}
        onChange={(e) => onSelectFile(e.target.files?.[0])}
        id="camera-input"
      />
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/webp"
        style={{ display: 'none' }}
        onChange={(e) => onSelectFile(e.target.files?.[0])}
        id="upload-input"
      />

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
      <section className="scan-hub-card" onClick={triggerCameraScan}>
        <div className="scan-hub-viewfinder">
          <div className="viewfinder-corners" />
          <div className="viewfinder-icon">📷</div>
          <span className="viewfinder-label">Tap to Scan Principal Display Panel</span>
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
    </div>
  );
}
