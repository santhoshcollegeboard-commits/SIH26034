import React, { useState } from 'react';
import ComplianceChecklist from './ComplianceChecklist';
import GTINIdentityCard from './GTINIdentityCard';
import ProductEvidenceViewer from './ProductEvidenceViewer';
import { downloadInspectionReportPdf } from '../services/pdfReportGenerator';

/* ─── Executive Metrology SVG Icon Suite ─── */

function ShieldCheckIcon({ className = '', size = 16 }) {
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

function AlertTriangleIcon({ className = '', size = 16 }) {
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
      <path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z" />
      <line x1="12" y1="9" x2="12" y2="13" />
      <line x1="12" y1="17" x2="12.01" y2="17" />
    </svg>
  );
}

function CheckCircle2Icon({ className = '', size = 16 }) {
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
      <path d="m9 12 2 2 4-4" />
    </svg>
  );
}

function XCircleIcon({ className = '', size = 16 }) {
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
      <line x1="15" y1="9" x2="9" y2="15" />
      <line x1="9" y1="9" x2="15" y2="15" />
    </svg>
  );
}

function SearchIcon({ className = '', size = 16 }) {
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
      <circle cx="11" cy="11" r="8" />
      <line x1="21" y1="21" x2="16.65" y2="16.65" />
    </svg>
  );
}

function CameraIcon({ className = '', size = 16 }) {
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

function PinIcon({ className = '', size = 12 }) {
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
      <line x1="12" y1="17" x2="12" y2="22" />
      <path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.89A2 2 0 0 1 15 10.76V6h1a1 1 0 0 0 1-1V3a1 1 0 0 0-1-1H8a1 1 0 0 0-1 1v2a1 1 0 0 0 1 1h1v4.76a2 2 0 0 1-1.11 1.79l-1.78.89A2 2 0 0 0 5 15.24Z" />
    </svg>
  );
}

function DownloadIcon({ className = '', size = 16 }) {
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
      <polyline points="7 10 12 15 17 10" />
      <line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}

function RefreshCwIcon({ className = '', size = 16 }) {
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
      <path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8" />
      <path d="M3 3v5h5" />
      <path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16" />
      <path d="M16 21h5v-5" />
    </svg>
  );
}

function PackageIcon({ className = '', size = 16 }) {
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
      <path d="m7.5 4.27 9 5.15" />
      <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z" />
      <path d="m3.3 7 8.7 5 8.7-5" />
      <line x1="12" y1="22" x2="12" y2="12" />
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

function ScaleIcon({ className = '', size = 16 }) {
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

function FileTextIcon({ className = '', size = 16 }) {
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
      <path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z" />
      <polyline points="14 2 14 8 20 8" />
      <line x1="16" y1="13" x2="8" y2="13" />
      <line x1="16" y1="17" x2="8" y2="17" />
      <line x1="10" y1="9" x2="8" y2="9" />
    </svg>
  );
}

/**
 * ResultScreen — Executive Legal Metrology Inspection Report Workspace
 *
 * Implements UI Milestone 4:
 * - High-authority statutory report presentation under Legal Metrology Rules, 2011.
 * - Above-the-fold verdict and key metric scorecard.
 * - Independent multi-product tab switching without cross-contamination.
 * - Sticky left evidence inspector viewport with package angle switcher strip.
 * - Clear statutory rules checklist vs unified extracted declarations view.
 * - Clean SVG iconography with zero emojis.
 * - Calibrated for 1080p desktop workstation (1920x1080) with full responsive support.
 */
export default function ResultScreen({
  verificationResponse,
  previewUrl,
  previewUrls = [],
  panels = [],
  onReset,
  inspectionMode,
  isPC = false,
}) {
  const [activeTab, setActiveTab] = useState('RULES'); // 'RULES' | 'EXTRACTION'
  const [activeProductIdx, setActiveProductIdx] = useState(0);
  const [selectedThumbIdx, setSelectedThumbIdx] = useState(0);

  // Extract products list: support both multi-product response array and single-product legacy
  const products =
    verificationResponse?.results && verificationResponse.results.length > 0
      ? verificationResponse.results
      : verificationResponse
      ? [verificationResponse]
      : [];

  const isMultiProduct =
    verificationResponse?.inspection_mode === 'multi_product' ||
    inspectionMode === 'MULTI_PRODUCT' ||
    products.length > 1;

  const safeProductIdx =
    products.length > 0
      ? Math.min(Math.max(0, activeProductIdx), products.length - 1)
      : 0;

  const currentProduct = products[safeProductIdx] || verificationResponse || {};

  const {
    compliance,
    extraction,
    processing_time_ms,
    model_used,
    image_count,
    panel_labels,
    barcode,
    gtin_identity,
    product_evidence,
    success = true,
    error: productError,
  } = currentProduct;

  const verdict = compliance?.overall_verdict || (success === false ? 'ERROR' : 'FLAGGED_FOR_REVIEW');
  const passedCount = compliance?.passed_count ?? 0;
  const failedCount = compliance?.failed_count ?? 0;
  const reviewCount = compliance?.review_count ?? 0;
  const naCount = compliance?.not_applicable_count ?? 0;
  const totalRules = compliance?.evaluations?.length ?? 9;

  const effectiveGtin =
    product_evidence?.gtin ||
    currentProduct.gtin ||
    gtin_identity?.product_record?.gtin ||
    barcode?.primary_gtin;

  const effectiveProductEvidence =
    product_evidence ||
    (effectiveGtin
      ? {
          gtin: effectiveGtin,
          product_name:
            gtin_identity?.product_record?.product_name ||
            extraction?.product_name?.value ||
            currentProduct.product_name,
        }
      : null);

  // Build list of thumbnails for current active product
  let displayThumbnails = [];
  if (isMultiProduct) {
    const matchingPanel = panels?.[safeProductIdx];
    if (matchingPanel) {
      displayThumbnails = [
        {
          url: matchingPanel.previewUrl,
          label: matchingPanel.productLabel || currentProduct.product_name || `Product ${safeProductIdx + 1}`,
          filename: matchingPanel.file?.name,
        },
      ];
    } else if (previewUrls?.[safeProductIdx]) {
      displayThumbnails = [
        {
          url: previewUrls[safeProductIdx],
          label: currentProduct.product_name || `Product ${safeProductIdx + 1}`,
          filename: `Product ${safeProductIdx + 1}`,
        },
      ];
    } else if (previewUrl && safeProductIdx === 0) {
      displayThumbnails = [
        {
          url: previewUrl,
          label: currentProduct.product_name || 'Product 1',
          filename: 'Inspected Image',
        },
      ];
    }

    if (effectiveProductEvidence?.evidence_image) {
      displayThumbnails.push({
        url: effectiveProductEvidence.evidence_image,
        label: 'Verified Reference',
        filename: 'Statutory Fault Localization (Reference)',
      });
    }
  } else {
    displayThumbnails =
      panels && panels.length > 0
        ? panels.map((p) => ({ url: p.previewUrl, label: p.panelLabel || 'Panel', filename: p.file?.name }))
        : previewUrls && previewUrls.length > 0
        ? previewUrls.map((url, idx) => ({
            url,
            label: panel_labels?.[idx] || `Panel ${idx + 1}`,
            filename: `Panel ${idx + 1}`,
          }))
        : previewUrl
        ? [{ url: previewUrl, label: panel_labels?.[0] || 'PDP', filename: 'Principal Display Panel' }]
        : [];

    if (effectiveProductEvidence?.evidence_image) {
      displayThumbnails.push({
        url: effectiveProductEvidence.evidence_image,
        label: 'Verified Reference',
        filename: 'Statutory Fault Localization (Reference)',
      });
    }
  }

  const effectivePanelCount = image_count || displayThumbnails.length || 1;
  const activeInspectThumb = displayThumbnails[selectedThumbIdx] || displayThumbnails[0];

  const displayedProductName =
    currentProduct.product_name ||
    extraction?.common_or_generic_name?.value ||
    extraction?.product_name?.value ||
    `Product ${safeProductIdx + 1}`;

  const [isGeneratingPdf, setIsGeneratingPdf] = useState(false);

  const handleDownloadPdf = async () => {
    try {
      setIsGeneratingPdf(true);
      await downloadInspectionReportPdf({
        verificationResponse,
        products,
        inspectionMode,
        panels,
      });
    } catch (err) {
      console.error('Failed to generate inspection report PDF:', err);
    } finally {
      setIsGeneratingPdf(false);
    }
  };

  const handleDownloadJson = () => {
    const reportData = {
      report_title: 'PackCheck Legal Metrology Statutory Compliance Report',
      inspection_date: new Date().toISOString(),
      product_id: currentProduct.product_id || `product_${safeProductIdx + 1}`,
      product_name: displayedProductName,
      gtin: effectiveGtin || 'Not Detected',
      overall_verdict: verdict,
      compliance_summary: compliance?.summary || '',
      passed_count: passedCount,
      failed_count: failedCount,
      review_count: reviewCount,
      exempt_count: naCount,
      evaluations: compliance?.evaluations || [],
      extracted_declarations: extraction || {},
      product_evidence: effectiveProductEvidence || null,
      processing_time_ms: processing_time_ms || null,
      model_used: model_used || null,
    };

    const blob = new Blob([JSON.stringify(reportData, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `PackCheck_Inspection_Report_${effectiveGtin || safeProductIdx + 1}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Verdict Banner Configurations with high-precision SVG icons
  const verdictConfigs = {
    PASS: {
      className: 'verdict-pass',
      icon: <ShieldCheckIcon size={24} className="verdict-svg-icon" />,
      title: 'STATUTORY COMPLIANCE CONFIRMED',
      subtitle: `All mandatory statutory declarations verified compliant across ${effectivePanelCount} package ${
        effectivePanelCount === 1 ? 'panel' : 'panels'
      } under Legal Metrology (Packaged Commodities) Rules, 2011.`,
      actionHint: 'Package meets all mandatory packaging standards across submitted panels for retail distribution.',
    },
    FAIL: {
      className: 'verdict-fail',
      icon: <AlertTriangleIcon size={24} className="verdict-svg-icon" />,
      title: 'STATUTORY NON-COMPLIANCE DETECTED',
      subtitle: `${failedCount} mandatory statutory rule violation(s) identified. Immediate packaging remediation or corrective action required.`,
      actionHint: 'Prohibited unit format, missing tax disclaimer, or bare numeric quantity detected in declarations.',
    },
    FLAGGED_FOR_REVIEW: {
      className: 'verdict-review',
      icon: <SearchIcon size={24} className="verdict-svg-icon" />,
      title: 'INSPECTOR VERIFICATION REQUIRED',
      subtitle: `${reviewCount} declaration(s) unverified, partially occluded, or conflicting across ${effectivePanelCount} package ${
        effectivePanelCount === 1 ? 'panel' : 'panels'
      }.`,
      actionHint:
        effectivePanelCount > 1
          ? 'Human inspector verification required to inspect unverified declarations or resolve cross-panel conflicts.'
          : 'Human inspector verification required to inspect secondary package panels (rear, base, or side declarations).',
    },
    ERROR: {
      className: 'verdict-fail',
      icon: <AlertTriangleIcon size={24} className="verdict-svg-icon" />,
      title: 'INSPECTION INCOMPLETE',
      subtitle: productError || 'An error occurred during verification of this product.',
      actionHint: 'Please check the uploaded package image and retry inspection.',
    },
  };

  const currentVerdict = verdictConfigs[verdict] || verdictConfigs.FLAGGED_FOR_REVIEW;

  // Actual backend extraction fields definition
  const rawFields = [
    { key: 'product_name', label: 'Brand / Trade Name' },
    { key: 'common_or_generic_name', label: 'Common / Generic Identity' },
    { key: 'net_quantity', label: 'Net Quantity' },
    { key: 'mrp', label: 'Maximum Retail Price (MRP)' },
    { key: 'month_year_of_manufacture', label: 'Mfg / Packaging Date' },
    { key: 'manufacturer_name', label: 'Manufacturer' },
    { key: 'manufacturer_address', label: 'Manufacturer Address' },
    { key: 'packer_name', label: 'Packer' },
    { key: 'importer_name', label: 'Importer' },
    { key: 'country_of_origin', label: 'Country of Origin' },
    { key: 'consumer_care_details', label: 'Consumer Helpline' },
  ];

  // Render raw fields extraction view
  const renderRawFieldsList = () => (
    <div className="raw-extraction-list">
      <div className="raw-fields-header">
        <h4>Unified Extracted Declarations</h4>
        <span className="raw-fields-sub">
          {isMultiProduct
            ? `Extracted declarations for ${currentProduct.product_name || `Product ${safeProductIdx + 1}`}`
            : `Aggregated across ${effectivePanelCount} package ${effectivePanelCount === 1 ? 'panel' : 'panels'}`}
        </span>
      </div>
      {rawFields.map(({ key, label }) => {
        const field = extraction?.[key] || {};
        const isConflict = field.status === 'conflict';
        const isPresent = field.status === 'extracted' && field.value;

        return (
          <div
            key={key}
            className={`raw-field-item ${
              isConflict ? 'field-conflict' : isPresent ? '' : 'field-missing'
            }`}
          >
            <div className="field-label-col">
              <div className="field-title-row">
                <span className="field-title">{label}</span>
                {field.source_panel_label && (
                  <span className="panel-tag-pill">
                    <PinIcon size={11} className="tag-pin-svg" />
                    <span>{field.source_panel_label}</span>
                  </span>
                )}
                {isConflict && <span className="conflict-tag-pill">CONFLICT</span>}
              </div>
              <span className="field-key">`{key}`</span>
            </div>
            <div className="field-val-col">
              {isConflict ? (
                <div className="field-conflict-content">
                  <span className="field-val-text conflict-val">“{field.value}”</span>
                  <span className="conflict-hint">
                    Inspector review required to confirm valid packaging declaration
                  </span>
                </div>
              ) : (
                <span className="field-val-text">
                  {field.value ? (
                    `“${field.value}”`
                  ) : (
                    <span className="text-muted">Not detected on package</span>
                  )}
                </span>
              )}
              {field.confidence !== undefined && field.confidence !== null && (
                <span className="field-conf-tag">
                  {Math.round(field.confidence * 100)}% conf
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );

  const renderEvidenceAndExtractions = () => (
    <div className="evidence-tab-stack">
      <ProductEvidenceViewer
        key={effectiveGtin || `prod-${safeProductIdx}`}
        productEvidence={effectiveProductEvidence}
      />
      {renderRawFieldsList()}
    </div>
  );

  return (
    <div className={`result-screen ${isPC ? 'pc-result-layout' : 'mobile-result-layout'}`}>
      {/* 1. Executive Metrology Dossier Header */}
      <header className="result-dossier-header" aria-label="Statutory Audit Dossier Header">
        <div className="dossier-header-left">
          <div className="dossier-act-badge">
            <ShieldCheckIcon size={13} className="dossier-shield-svg" />
            <span>LEGAL METROLOGY &bull; PACKAGED COMMODITIES</span>
          </div>
          <h1 className="dossier-title">PackCheck Inspection Report</h1>
        </div>
        <div className="dossier-header-right">
          <div className="dossier-meta-item">
            <span className="dossier-meta-label">Audit Mode</span>
            <span className="dossier-meta-val">
              {isMultiProduct
                ? 'Batch Multi-Commodity'
                : effectivePanelCount > 1
                ? `${effectivePanelCount}-Panel Composite`
                : 'Single-Panel Standard'}
            </span>
          </div>
          <div className="dossier-meta-item">
            <span className="dossier-meta-label">Dossier ID</span>
            <span className="dossier-meta-val dossier-id-mono">
              {effectiveGtin ? `PC-${effectiveGtin.slice(-6)}` : `PC-AUDIT-${safeProductIdx + 1}`}
            </span>
          </div>
        </div>
      </header>

      {/* 2. Multi-Product Navigation Bar (When multi-product inspection active) */}
      {isMultiProduct && products.length > 0 && (
        <nav className="product-reports-nav" aria-label="Product Inspections Navigation">
          <div className="product-reports-nav-header">
            <div className="nav-header-left">
              <span className="nav-header-icon">
                <PackageIcon size={18} />
              </span>
              <span className="nav-header-title">Multi-Product Inspection Workspace</span>
              <span className="nav-header-badge">{products.length} Commodities Inspected</span>
            </div>
            <span className="nav-header-hint">
              Select a commodity to view its independent statutory audit dossier
            </span>
          </div>
          <div className="product-tabs-track" role="tablist">
            {products.map((p, idx) => {
              const isSelected = idx === safeProductIdx;
              const pVerdict = p.compliance?.overall_verdict || (p.success === false ? 'ERROR' : 'REVIEW');
              const pGtin =
                p.gtin ||
                p.product_evidence?.gtin ||
                p.gtin_identity?.product_record?.gtin ||
                p.barcode?.primary_gtin;
              const pName =
                p.product_name ||
                p.extraction?.product_name?.value ||
                p.extraction?.common_or_generic_name?.value ||
                `Product ${idx + 1}`;

              let pillClass = 'pill-review';
              let pillText = 'REVIEW';
              if (p.success === false) {
                pillClass = 'pill-fail';
                pillText = 'ERROR';
              } else if (pVerdict === 'PASS') {
                pillClass = 'pill-pass';
                pillText = 'COMPLIANT';
              } else if (pVerdict === 'FAIL') {
                pillClass = 'pill-fail';
                pillText = 'VIOLATIONS';
              }

              return (
                <button
                  key={p.product_id || idx}
                  type="button"
                  role="tab"
                  aria-selected={isSelected}
                  className={`product-nav-tab ${isSelected ? 'active-product-tab' : ''}`}
                  onClick={() => {
                    setActiveProductIdx(idx);
                    setSelectedThumbIdx(0);
                  }}
                >
                  <div className="tab-top-row">
                    <span className="tab-num">#{idx + 1}</span>
                    <span className={`tab-verdict-badge ${pillClass}`}>{pillText}</span>
                  </div>
                  <div className="tab-name" title={pName}>
                    {pName}
                  </div>
                  <div className="tab-gtin">
                    {pGtin ? `GTIN: ${pGtin}` : 'No Barcode'}
                  </div>
                </button>
              );
            })}
          </div>
        </nav>
      )}

      {/* If current product had an error, render isolated error card */}
      {success === false ? (
        <div className="product-error-container">
          <section className="verdict-banner verdict-fail">
            <div className="verdict-badge-row">
              <span className="verdict-icon">
                <AlertTriangleIcon size={24} className="verdict-svg-icon" />
              </span>
              <h2 className="verdict-title">PRODUCT INSPECTION INCOMPLETE</h2>
            </div>
            <p className="verdict-sub">
              {productError || 'An error occurred during verification of this product.'}
            </p>
            <div className="verdict-hint">
              <span>
                Other products in this inspection were processed independently. Select another product above to review its statutory report.
              </span>
            </div>
          </section>

          <div className="product-error-card">
            <div className="product-error-icon">
              <AlertTriangleIcon size={28} />
            </div>
            <h4 className="product-error-title">Inspection Incomplete for this Product</h4>
            <p className="product-error-desc">
              {productError || 'Failed to extract declarations or decode barcode for this package image.'}
            </p>
            <div className="product-error-actions">
              <button
                type="button"
                className="btn-primary btn-large"
                onClick={onReset}
              >
                <RefreshCwIcon size={16} className="btn-icon-svg" />
                <span>Inspect Another Package</span>
              </button>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* 3. Prominent Verdict Banner */}
          <section className={`verdict-banner ${currentVerdict.className}`} id="verdict-banner">
            <div className="verdict-badge-row">
              <span className="verdict-icon">{currentVerdict.icon}</span>
              <h2 className="verdict-title">{currentVerdict.title}</h2>
            </div>
            <p className="verdict-sub">{currentVerdict.subtitle}</p>
            <div className="verdict-hint">
              <span>{currentVerdict.actionHint}</span>
            </div>
          </section>

          {/* 4. Key Metrics Summary Grid (Above-the-Fold Scorecard) */}
          <section className="metrics-grid" aria-label="Compliance Summary Scorecard">
            <div className="metric-cell cell-total">
              <span className="metric-val">{totalRules}</span>
              <span className="metric-lbl">Total Rules</span>
            </div>
            <div className="metric-cell cell-pass">
              <div className="metric-icon-val-row">
                <CheckCircle2Icon size={16} className="metric-cell-icon icon-pass" />
                <span className="metric-val">{passedCount}</span>
              </div>
              <span className="metric-lbl">Passed</span>
            </div>
            {failedCount > 0 && (
              <div className="metric-cell cell-fail">
                <div className="metric-icon-val-row">
                  <XCircleIcon size={16} className="metric-cell-icon icon-fail" />
                  <span className="metric-val">{failedCount}</span>
                </div>
                <span className="metric-lbl">Violations</span>
              </div>
            )}
            <div className="metric-cell cell-review">
              <div className="metric-icon-val-row">
                <SearchIcon size={16} className="metric-cell-icon icon-review" />
                <span className="metric-val">{reviewCount}</span>
              </div>
              <span className="metric-lbl">Review</span>
            </div>
            {naCount > 0 && (
              <div className="metric-cell cell-na">
                <span className="metric-val">{naCount}</span>
                <span className="metric-lbl">Exempt</span>
              </div>
            )}
            <div className="metric-cell cell-panels">
              <div className="metric-icon-val-row">
                <LayersIcon size={16} className="metric-cell-icon icon-panels" />
                <span className="metric-val">{effectivePanelCount}</span>
              </div>
              <span className="metric-lbl">{effectivePanelCount === 1 ? 'Panel' : 'Panels'}</span>
            </div>
          </section>

          {/* ─── PC WORKSTATION TWO-COLUMN RESULTS (1080p Calibrated) ─── */}
          {isPC ? (
            <div className="pc-result-workstation-grid">
              {/* Left Column: Sticky Package Evidence Viewer & Metadata */}
              <div className="pc-result-stage-col">
                <div className="pc-result-image-card">
                  <div className="pc-stage-image-header">
                    <div className="pc-image-header-title">
                      <CameraIcon size={16} className="pc-header-icon-svg" />
                      <span className="pc-header-title-text">Package Evidence Viewport</span>
                      {activeInspectThumb && (
                        <span className="pc-active-panel-tag">
                          <PinIcon size={10} className="tag-pin-svg" />
                          <span>{activeInspectThumb.label}</span>
                        </span>
                      )}
                    </div>
                    {activeInspectThumb?.filename && (
                      <span className="pc-filename-sub">{activeInspectThumb.filename}</span>
                    )}
                  </div>

                  {/* Large Image Viewport */}
                  <div className="pc-large-inspect-box">
                    {activeInspectThumb ? (
                      <img
                        src={activeInspectThumb.url}
                        alt={`${activeInspectThumb.label} inspected evidence`}
                        className="pc-inspect-main-img"
                      />
                    ) : (
                      <div className="pc-no-img-box">No image available</div>
                    )}
                  </div>

                  {/* Multi-Panel Thumbnails Switcher Strip */}
                  {displayThumbnails.length > 1 && (
                    <div className="pc-snapshot-thumbs-strip">
                      <span className="pc-thumbs-strip-title">Package Panels & Reference Angles:</span>
                      <div className="pc-thumbs-track">
                        {displayThumbnails.map((t, idx) => {
                          const isSelected = idx === selectedThumbIdx;
                          return (
                            <button
                              key={idx}
                              type="button"
                              className={`pc-thumb-btn ${isSelected ? 'is-selected-thumb' : ''}`}
                              onClick={() => setSelectedThumbIdx(idx)}
                              title={`View ${t.label}`}
                            >
                              <img src={t.url} alt={t.label} className="pc-strip-thumb-img" />
                              <span className="pc-strip-thumb-label">{t.label}</span>
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  )}

                  {/* Commodity Identity Card */}
                  <div className="pc-commodity-info-box">
                    <div className="pc-commodity-header-row">
                      <PackageIcon size={16} className="pc-commodity-icon" />
                      <h4 className="pc-commodity-name">{displayedProductName}</h4>
                    </div>
                    {extraction?.product_name?.value &&
                      extraction?.common_or_generic_name?.value &&
                      extraction?.product_name?.value !== extraction?.common_or_generic_name?.value && (
                        <span className="pc-commodity-brand">
                          Declared Brand: {extraction.product_name.value}
                        </span>
                      )}
                    <div className="pc-commodity-tags">
                      <span className="meta-tag">
                        {effectivePanelCount === 1 ? '1 Panel' : `${effectivePanelCount} Panels Merged`}
                      </span>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="pc-stage-actions">
                    <button
                      type="button"
                      className="btn-primary btn-large pc-btn-download-report"
                      onClick={handleDownloadPdf}
                      disabled={isGeneratingPdf}
                      id="btn-download-report"
                    >
                      <DownloadIcon size={16} className="btn-icon-svg" />
                      <span>{isGeneratingPdf ? 'Generating PDF...' : 'DOWNLOAD PDF REPORT'}</span>
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-large pc-btn-download-json"
                      onClick={handleDownloadJson}
                      id="btn-download-json"
                      title="Download raw technical inspection data in JSON format"
                    >
                      <FileTextIcon size={15} className="btn-icon-svg" />
                      <span>Download JSON</span>
                    </button>
                    <button
                      type="button"
                      className="btn-secondary btn-large pc-btn-scan-another"
                      onClick={onReset}
                      id="btn-pc-scan-another"
                    >
                      <RefreshCwIcon size={16} className="btn-icon-svg" />
                      <span>Inspect Another Package</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* Right Column: Statutory Audit Checklist & Tabs */}
              <div className="pc-result-audit-col">
                {/* Human Review Action Callout (For FLAGGED_FOR_REVIEW) */}
                {verdict === 'FLAGGED_FOR_REVIEW' && (
                  <div className="review-notice-box pc-review-notice">
                    <div className="notice-icon-col">
                      <AlertTriangleIcon size={18} className="notice-warn-svg" />
                    </div>
                    <div className="notice-text-col">
                      <strong>Human Inspector Review Required</strong>
                      <p>
                        {effectivePanelCount > 1
                          ? 'One or more statutory requirements were unreadable, missing, or contradictory across the submitted package panels.'
                          : 'Rule 6 statutory requirements not visible on this photo may be printed on the back or sides of the package.'}
                      </p>
                    </div>
                  </div>
                )}

                {/* GTIN / Product Identity Verification */}
                {(gtin_identity || barcode) && (
                  <GTINIdentityCard gtinIdentity={gtin_identity} barcode={barcode} />
                )}

                {/* View Switcher (Statutory Rules vs Label Declarations) */}
                <div className="view-switch-row" role="tablist">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'RULES'}
                    className={`switch-btn ${activeTab === 'RULES' ? 'active' : ''}`}
                    onClick={() => setActiveTab('RULES')}
                  >
                    <ScaleIcon size={14} className="tab-switch-icon" />
                    <span>Statutory Rules ({totalRules})</span>
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={activeTab === 'EXTRACTION'}
                    className={`switch-btn ${activeTab === 'EXTRACTION' ? 'active' : ''}`}
                    onClick={() => setActiveTab('EXTRACTION')}
                  >
                    <FileTextIcon size={14} className="tab-switch-icon" />
                    <span>Evidence & Extractions ({rawFields.length})</span>
                  </button>
                </div>

                {/* Content Section */}
                {activeTab === 'RULES' ? (
                  <ComplianceChecklist
                    evaluations={compliance?.evaluations || []}
                    extraction={extraction || {}}
                  />
                ) : (
                  renderEvidenceAndExtractions()
                )}
              </div>
            </div>
          ) : (
            /* ─── MOBILE RESULTS EXPERIENCE ─── */
            <>
              {/* Package Thumbnail & Multi-Panel Snapshot Strip */}
              <section className="package-snapshot-card">
                {displayThumbnails.length > 0 && (
                  <div className="snapshot-thumbs-strip">
                    {displayThumbnails.map((t, idx) => (
                      <div key={idx} className="snapshot-thumb-col">
                        <img src={t.url} alt={`${t.label} thumbnail`} className="multi-thumb-img" />
                        <span className="multi-thumb-pill">{t.label}</span>
                      </div>
                    ))}
                  </div>
                )}
                <div className="snapshot-details">
                  <h4 className="snapshot-product">{displayedProductName}</h4>
                  {extraction?.product_name?.value &&
                    extraction?.common_or_generic_name?.value &&
                    extraction?.product_name?.value !== extraction?.common_or_generic_name?.value && (
                      <span className="snapshot-brand">
                        Brand: {extraction.product_name.value}
                      </span>
                    )}
                  <div className="snapshot-meta-tags">
                    <span className="meta-tag">
                      {effectivePanelCount === 1 ? '1 Panel' : `${effectivePanelCount} Panels Merged`}
                    </span>
                  </div>
                </div>
              </section>

              {/* Human Review Action Callout (For FLAGGED_FOR_REVIEW) */}
              {verdict === 'FLAGGED_FOR_REVIEW' && (
                <div className="review-notice-box">
                  <div className="notice-icon-col">
                    <AlertTriangleIcon size={18} className="notice-warn-svg" />
                  </div>
                  <div className="notice-text-col">
                    <strong>Human Inspector Review Required</strong>
                    <p>
                      {effectivePanelCount > 1
                        ? 'One or more statutory requirements were unreadable, missing, or contradictory across the submitted package panels.'
                        : 'Rule 6 statutory requirements not visible on this photo may be printed on the back or sides of the package.'}
                    </p>
                  </div>
                </div>
              )}

              {/* GTIN / Product Identity Verification */}
              {(gtin_identity || barcode) && (
                <GTINIdentityCard gtinIdentity={gtin_identity} barcode={barcode} />
              )}

              {/* View Switcher (Statutory Rules vs Label Declarations) */}
              <div className="view-switch-row" role="tablist">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'RULES'}
                  className={`switch-btn ${activeTab === 'RULES' ? 'active' : ''}`}
                  onClick={() => setActiveTab('RULES')}
                >
                  <ScaleIcon size={14} className="tab-switch-icon" />
                  <span>Statutory Rules ({totalRules})</span>
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'EXTRACTION'}
                  className={`switch-btn ${activeTab === 'EXTRACTION' ? 'active' : ''}`}
                  onClick={() => setActiveTab('EXTRACTION')}
                >
                  <FileTextIcon size={14} className="tab-switch-icon" />
                  <span>Evidence & Extractions ({rawFields.length})</span>
                </button>
              </div>

              {/* Content Section */}
              {activeTab === 'RULES' ? (
                <ComplianceChecklist
                  evaluations={compliance?.evaluations || []}
                  extraction={extraction || {}}
                />
              ) : (
                renderEvidenceAndExtractions()
              )}

              {/* Sticky Bottom Action */}
              <div className="result-sticky-footer">
                <button
                  type="button"
                  className="btn-primary btn-large"
                  onClick={handleDownloadPdf}
                  disabled={isGeneratingPdf}
                  id="btn-mobile-download-report"
                >
                  <DownloadIcon size={16} className="btn-icon-svg" />
                  <span>{isGeneratingPdf ? 'Generating PDF...' : 'DOWNLOAD PDF REPORT'}</span>
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-large"
                  onClick={handleDownloadJson}
                  id="btn-mobile-download-json"
                  title="Download JSON technical export"
                >
                  <FileTextIcon size={15} className="btn-icon-svg" />
                  <span>Download JSON</span>
                </button>
                <button
                  type="button"
                  className="btn-secondary btn-large"
                  onClick={onReset}
                  id="btn-scan-another"
                >
                  <RefreshCwIcon size={16} className="btn-icon-svg" />
                  <span>Scan Another Package</span>
                </button>
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
