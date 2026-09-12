import React, { useState, useEffect } from 'react';

/**
 * Responsive verification loading state.
 * - PC Mode: Workstation progress view showing parallel panel scanning and staged pipeline flow.
 * - Mobile Mode: Preserved compact scanner viewfinder and stage indicators.
 */
export default function VerificationLoader({
  previewUrl,
  previewUrls = [],
  panelCount,
  isPC = false,
}) {
  const count = panelCount || (previewUrls && previewUrls.length) || (previewUrl ? 1 : 1);
  const thumbs =
    previewUrls && previewUrls.length > 0
      ? previewUrls
      : previewUrl
      ? [previewUrl]
      : [];
  const primaryThumb = thumbs[0];

  const steps = [
    {
      title: count > 1 ? `Scanning ${count} package panels in parallel...` : 'Reading packaging label...',
      subtitle:
        count > 1
          ? 'Dispatching concurrent OCR across all submitted package panels'
          : 'Scanning visible declarations on Principal Display Panel',
      badge: 'AI Vision Proposer',
      icon: '👁️',
    },
    {
      title: count > 1 ? 'Consolidating multi-panel evidence...' : 'Extracting mandatory fields...',
      subtitle:
        count > 1
          ? 'Merging declarations across panels and checking for conflicts'
          : 'Isolating brand, generic name, MRP, net quantity & address',
      badge: 'Evidence Aggregation',
      icon: '🧩',
    },
    {
      title: 'Checking Legal Metrology rules...',
      subtitle: 'Executing 9 deterministic statutory compliance evaluators once',
      badge: 'Deterministic Rule Engine',
      icon: '⚖️',
    },
  ];

  const [currentStep, setCurrentStep] = useState(0);

  useEffect(() => {
    const timer = setInterval(() => {
      setCurrentStep((prev) => (prev < steps.length - 1 ? prev + 1 : prev));
    }, 2400);

    return () => clearInterval(timer);
  }, [steps.length]);

  return (
    <div className={`loader-container ${isPC ? 'pc-loader-container' : 'mobile-loader-container'}`}>
      {isPC ? (
        /* ─── PC WORKSTATION LOADER ─── */
        <div className="pc-loader-card">
          <div className="pc-loader-header">
            <span className="pc-loader-shield">🛡️</span>
            <h2 className="pc-loader-title">Legal Metrology Compliance Inspection</h2>
            <p className="pc-loader-desc">
              Executing staged statutory evaluation pipeline across {count} {count === 1 ? 'panel' : 'panels'}
            </p>
          </div>

          {/* Multi-Panel Visual Scan Deck */}
          <div className="pc-scanner-deck">
            {thumbs.slice(0, 6).map((url, idx) => (
              <div key={idx} className="pc-scan-thumb-card">
                <div className="pc-thumb-wrap">
                  <img src={url} alt={`Panel ${idx + 1}`} className="pc-scan-thumb-img" />
                  <div className="pc-scan-overlay" />
                  <div className="pc-scan-beam" />
                </div>
                <span className="pc-thumb-label">Panel #{idx + 1}</span>
              </div>
            ))}
          </div>

          {/* Pipeline Stage Cards */}
          <div className="pc-pipeline-stages-row">
            {steps.map((step, idx) => {
              const isActive = idx === currentStep;
              const isDone = idx < currentStep;
              return (
                <div
                  key={step.title}
                  className={`pc-stage-card ${isActive ? 'is-active' : isDone ? 'is-done' : 'is-pending'}`}
                >
                  <div className="pc-stage-badge-row">
                    <span className="pc-stage-icon">{step.icon}</span>
                    <span className="pc-stage-badge">{step.badge}</span>
                    <span className="pc-stage-status-indicator">
                      {isDone ? '✓ Completed' : isActive ? '● In Progress' : '○ Pending'}
                    </span>
                  </div>
                  <h4 className="pc-stage-title">{step.title}</h4>
                  <p className="pc-stage-sub">{step.subtitle}</p>
                </div>
              );
            })}
          </div>

          <div className="loader-guarantee pc-guarantee">
            <span className="guarantee-icon">🛡️</span>
            <span className="guarantee-text">
              Zero LLM compliance bias &bull; Statutory rules are 100% deterministic code
            </span>
          </div>
        </div>
      ) : (
        /* ─── MOBILE EXPERIENCE (PRESERVED) ─── */
        <>
          {/* Visual Scanning Animation over package thumbnail */}
          <div className="scanner-frame">
            {primaryThumb ? (
              <img src={primaryThumb} alt="Package under inspection" className="scanner-preview" />
            ) : (
              <div className="scanner-placeholder">📦</div>
            )}
            <div className="scanner-overlay" />
            <div className="scanner-line" />
            <div className="scanner-corners" />
          </div>

          {/* Stage Status */}
          <div className="loader-content">
            <div className="stage-badge-pill">{steps[currentStep].badge}</div>
            <h3 className="loader-title">{steps[currentStep].title}</h3>
            <p className="loader-subtitle">{steps[currentStep].subtitle}</p>
          </div>

          {/* Pipeline Stage Indicators */}
          <div className="stages-indicator-row">
            {steps.map((step, idx) => (
              <div
                key={step.title}
                className={`stage-dot ${idx === currentStep ? 'active' : idx < currentStep ? 'completed' : ''}`}
                title={step.badge}
              />
            ))}
          </div>

          <div className="loader-guarantee">
            <span className="guarantee-icon">🛡️</span>
            <span className="guarantee-text">
              Zero LLM compliance bias &bull; Rules are 100% deterministic
            </span>
          </div>
        </>
      )}
    </div>
  );
}
