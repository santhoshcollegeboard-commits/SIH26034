import React, { useState, useEffect } from 'react';

/**
 * Polished mobile verification loading state.
 * Explains the two-stage pipeline (AI Vision Extraction -> Deterministic Rule Engine)
 * without faking artificial progress percentages.
 */
export default function VerificationLoader({ previewUrl, previewUrls = [], panelCount }) {
  const count = panelCount || (previewUrls && previewUrls.length) || (previewUrl ? 1 : 1);
  const primaryThumb = previewUrl || (previewUrls && previewUrls[0]);

  const steps = [
    {
      title: count > 1 ? `Scanning ${count} package panels in parallel...` : 'Reading packaging label...',
      subtitle:
        count > 1
          ? 'Dispatching concurrent OCR across all submitted package panels'
          : 'Scanning visible declarations on Principal Display Panel',
      badge: 'AI Vision Proposer',
    },
    {
      title: count > 1 ? 'Consolidating multi-panel evidence...' : 'Extracting mandatory fields...',
      subtitle:
        count > 1
          ? 'Merging declarations across panels and checking for conflicts'
          : 'Isolating brand, generic name, MRP, net quantity & address',
      badge: 'Evidence Aggregation',
    },
    {
      title: 'Checking Legal Metrology rules...',
      subtitle: 'Executing 9 deterministic statutory compliance evaluators once',
      badge: 'Deterministic Rule Engine',
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
    <div className="loader-container">
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
    </div>
  );
}
