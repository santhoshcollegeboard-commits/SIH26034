import React, { useState, useEffect, useMemo } from 'react';

/**
 * Clean inline SVG icons for Executive Metrology Suite & Optical QC aesthetic.
 */
function ShieldCheckIcon({ className = '', size = 20 }) {
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

function EyeScanIcon({ className = '', size = 18 }) {
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
      <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z" />
      <circle cx="12" cy="12" r="3" />
      <path d="M3 7V5a2 2 0 0 1 2-2h2" />
      <path d="M17 3h2a2 2 0 0 1 2 2v2" />
      <path d="M21 17v2a2 2 0 0 1-2 2h-2" />
      <path d="M7 21H5a2 2 0 0 1-2-2v-2" />
    </svg>
  );
}

function AggregationIcon({ className = '', size = 18 }) {
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
      <rect width="8" height="8" x="3" y="3" rx="2" />
      <rect width="8" height="8" x="13" y="3" rx="2" />
      <rect width="8" height="8" x="8" y="13" rx="2" />
      <path d="M7 11v4a1 1 0 0 0 1 1h4" />
      <path d="M17 11v4a1 1 0 0 1-1 1h-4" />
    </svg>
  );
}

function RuleEngineIcon({ className = '', size = 18 }) {
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
      <path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
      <path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z" />
      <path d="M7 21h10" />
      <path d="M12 3v18" />
      <path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2" />
    </svg>
  );
}

function CheckCircleIcon({ className = '', size = 13 }) {
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
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function SpinnerIcon({ className = '', size = 13 }) {
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
      className={`pc-spin ${className}`}
      aria-hidden="true"
    >
      <path d="M21 12a9 9 0 1 1-6.219-8.56" />
    </svg>
  );
}

function ClockIcon({ className = '', size = 13 }) {
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
      <circle cx="12" cy="12" r="10" />
      <polyline points="12 6 12 12 16 14" />
    </svg>
  );
}

/**
 * Optical Reticles for QC viewfinder cards
 */
function OpticalReticleCorners() {
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
 * Responsive verification loading state for PackCheck.
 * - PC Mode: Executive Metrology Suite layout with parallel optical QC scanning deck and staged pipeline cards.
 * - Mobile Mode: Preserved compact viewfinder and staged status flow.
 */
export default function VerificationLoader({
  previewUrl,
  previewUrls = [],
  panelCount,
  panels = [],
  inspectionMode = 'SINGLE_PRODUCT',
  isPC = false,
  isMobile = false, // eslint-disable-line no-unused-vars
  effectiveMode, // eslint-disable-line no-unused-vars
}) {
  const isMulti = inspectionMode === 'MULTI_PRODUCT';

  // Normalize items array with accurate product vs panel labeling
  const items = useMemo(() => {
    if (panels && panels.length > 0) {
      return panels.map((p, idx) => {
        const itemNumber = (idx + 1).toString().padStart(2, '0');
        const defaultLabel = isMulti ? `Product ${idx + 1}` : `Panel #${idx + 1}`;
        const cleanName = p.file?.name ? p.file.name.replace(/\.[^/.]+$/, '') : defaultLabel;
        const assignedLabel = isMulti
          ? (p.productLabel || cleanName)
          : (p.panelLabel || defaultLabel);
        const chipLabel = isMulti ? `Product ${itemNumber}` : `Panel ${itemNumber}`;

        return {
          id: p.id || `item-${idx}`,
          url: p.previewUrl,
          label: assignedLabel,
          chip: chipLabel,
        };
      });
    }

    if (previewUrls && previewUrls.length > 0) {
      return previewUrls.map((url, idx) => {
        const itemNumber = (idx + 1).toString().padStart(2, '0');
        return {
          id: `thumb-${idx}`,
          url,
          label: isMulti ? `Product ${idx + 1}` : `Panel #${idx + 1}`,
          chip: isMulti ? `Product ${itemNumber}` : `Panel ${itemNumber}`,
        };
      });
    }

    if (previewUrl) {
      return [
        {
          id: 'thumb-0',
          url: previewUrl,
          label: isMulti ? 'Product 01' : 'Panel #1',
          chip: isMulti ? 'Product 01' : 'Panel 01',
        },
      ];
    }

    return [];
  }, [panels, previewUrls, previewUrl, isMulti]);

  const count = panelCount || items.length || 1;
  const primaryThumb = items[0]?.url;

  const steps = [
    {
      id: '01',
      badge: 'AI Vision Evidence',
      title: isMulti
        ? `Extracting declarations across ${count} products...`
        : count > 1
        ? `Scanning ${count} package panels in parallel...`
        : 'Reading packaging label...',
      subtitle: 'Extracting visible package declarations and evidence.',
      icon: EyeScanIcon,
    },
    {
      id: '02',
      badge: 'Evidence Aggregation',
      title: isMulti
        ? 'Structuring multi-product declarations...'
        : count > 1
        ? 'Consolidating multi-panel evidence...'
        : 'Extracting mandatory fields...',
      subtitle: 'Reconciling observations across submitted images.',
      icon: AggregationIcon,
    },
    {
      id: '03',
      badge: 'Deterministic Rule Engine',
      title: 'Checking Legal Metrology rules...',
      subtitle: 'Evaluating statutory conditions.',
      icon: RuleEngineIcon,
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
        /* ─── PC WORKSTATION METROLOGY SUITE LOADER ─── */
        <div className="pc-loader-card">
          <div className="pc-loader-header">
            <div className="pc-loader-header-top">
              <div className="pc-loader-icon-wrap">
                <ShieldCheckIcon size={24} className="pc-loader-shield-svg" />
              </div>
              <div className="pc-loader-header-info">
                <div className="pc-loader-context-badge">
                  <span className="pc-context-dot" />
                  {isMulti
                    ? `INDEPENDENT PRODUCT BATCH • ${count} ${count === 1 ? 'PRODUCT' : 'PRODUCTS'}`
                    : count > 1
                    ? `MULTI-PANEL AGGREGATION • ${count} PANELS`
                    : 'SINGLE-PANEL INSPECTION • 1 PANEL'}
                </div>
                <h2 className="pc-loader-title">Legal Metrology Compliance Inspection</h2>
                <p className="pc-loader-desc">
                  Executing staged statutory evaluation pipeline across {count}{' '}
                  {isMulti ? (count === 1 ? 'product' : 'products') : (count === 1 ? 'package panel' : 'package panels')}
                </p>
              </div>
            </div>
          </div>

          {/* Optical QC Multi-Item Inspection Deck */}
          <div className="pc-scanner-deck">
            {items.slice(0, 6).map((item, idx) => (
              <div key={item.id || idx} className="pc-scan-thumb-card">
                <div className="pc-thumb-wrap">
                  {item.url ? (
                    <img src={item.url} alt={item.label} className="pc-scan-thumb-img" />
                  ) : (
                    <div className="pc-scan-placeholder">📦</div>
                  )}
                  <div className="pc-scan-overlay" />
                  <div className="pc-optical-sweep" />
                  <OpticalReticleCorners />
                </div>
                <div className="pc-thumb-meta">
                  <span className="pc-thumb-index-chip">{item.chip}</span>
                  <span className="pc-thumb-label" title={item.label}>
                    {item.label}
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Pipeline Stage Cards */}
          <div className="pc-pipeline-stages-row">
            {steps.map((step, idx) => {
              const isActive = idx === currentStep;
              const isDone = idx < currentStep;
              const StepIcon = step.icon;

              return (
                <div
                  key={step.id}
                  className={`pc-stage-card ${isActive ? 'is-active' : isDone ? 'is-done' : 'is-pending'}`}
                >
                  <div className="pc-stage-header">
                    <div className="pc-stage-lead">
                      <span className="stage-number-tag">STAGE {step.id}</span>
                      <span className="pc-stage-badge">{step.badge}</span>
                    </div>
                    <div
                      className={`pc-stage-status-indicator ${
                        isActive ? 'is-active' : isDone ? 'is-done' : 'is-pending'
                      }`}
                    >
                      {isDone ? (
                        <>
                          <CheckCircleIcon size={12} />
                          <span>COMPLETED</span>
                        </>
                      ) : isActive ? (
                        <>
                          <SpinnerIcon size={12} />
                          <span>IN PROGRESS</span>
                        </>
                      ) : (
                        <>
                          <ClockIcon size={12} />
                          <span>WAITING</span>
                        </>
                      )}
                    </div>
                  </div>

                  <div className="pc-stage-body">
                    <div className="pc-stage-icon-wrap">
                      <StepIcon size={18} />
                    </div>
                    <div className="pc-stage-text">
                      <h4 className="pc-stage-title">{step.title}</h4>
                      <p className="pc-stage-sub">{step.subtitle}</p>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="loader-guarantee pc-guarantee">
            <ShieldCheckIcon size={15} className="guarantee-shield-svg" />
            <span className="guarantee-text">
              Zero LLM compliance bias &bull; Statutory rules are 100% deterministic code
            </span>
          </div>
        </div>
      ) : (
        /* ─── MOBILE EXPERIENCE ─── */
        <div className="mobile-loader-card">
          <div className="scanner-frame">
            {primaryThumb ? (
              <img src={primaryThumb} alt="Package under inspection" className="scanner-preview" />
            ) : (
              <div className="scanner-placeholder">
                <ShieldCheckIcon size={40} className="scanner-placeholder-svg" />
              </div>
            )}
            <div className="scanner-overlay" />
            <div className="scanner-line" />
            <OpticalReticleCorners />
          </div>

          {/* Stage Status */}
          <div className="loader-content">
            <div className="stage-badge-pill">
              <span className="stage-number-pill">STAGE {steps[currentStep].id}</span>
              <span>{steps[currentStep].badge}</span>
            </div>
            <h3 className="loader-title">{steps[currentStep].title}</h3>
            <p className="loader-subtitle">{steps[currentStep].subtitle}</p>
            <div className={`mobile-status-chip ${currentStep === 2 ? 'is-evaluating' : 'is-active'}`}>
              <SpinnerIcon size={12} />
              <span>IN PROGRESS</span>
            </div>
          </div>

          {/* Pipeline Stage Indicators */}
          <div className="stages-indicator-row">
            {steps.map((step, idx) => (
              <div
                key={step.id}
                className={`stage-dot ${idx === currentStep ? 'active' : idx < currentStep ? 'completed' : ''}`}
                title={`Stage ${step.id}: ${step.badge}`}
              />
            ))}
          </div>

          <div className="loader-guarantee">
            <ShieldCheckIcon size={14} className="guarantee-shield-svg" />
            <span className="guarantee-text">
              Zero LLM compliance bias &bull; Rules are 100% deterministic
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
