import React, { useState, useEffect } from 'react';

/**
 * Polished mobile verification loading state.
 * Explains the two-stage pipeline (AI Vision Extraction -> Deterministic Rule Engine)
 * without faking artificial progress percentages.
 */
export default function VerificationLoader({ previewUrl }) {
  const steps = [
    {
      title: 'Reading packaging label...',
      subtitle: 'Scanning visible declarations on Principal Display Panel',
      badge: 'AI Vision Proposer',
    },
    {
      title: 'Extracting mandatory fields...',
      subtitle: 'Isolating brand, generic name, MRP, net quantity & address',
      badge: 'OCR Feature Extraction',
    },
    {
      title: 'Checking Legal Metrology rules...',
      subtitle: 'Executing deterministic statutory compliance evaluators',
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
        {previewUrl ? (
          <img src={previewUrl} alt="Package under inspection" className="scanner-preview" />
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
