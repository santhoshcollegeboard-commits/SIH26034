import React, { useState } from 'react';
import ComplianceChecklist from './ComplianceChecklist';

/**
 * Mobile Results Screen displaying the overall verdict, summary metrics,
 * statutory compliance checklist, and raw label declarations view.
 */
export default function ResultScreen({
  verificationResponse,
  previewUrl,
  onReset,
}) {
  const [activeTab, setActiveTab] = useState('RULES'); // 'RULES' | 'EXTRACTION'

  const { compliance, extraction, processing_time_ms, model_used } =
    verificationResponse || {};

  const verdict = compliance?.overall_verdict || 'FLAGGED_FOR_REVIEW';
  const passedCount = compliance?.passed_count ?? 0;
  const failedCount = compliance?.failed_count ?? 0;
  const reviewCount = compliance?.review_count ?? 0;
  const naCount = compliance?.not_applicable_count ?? 0;
  const totalRules = compliance?.evaluations?.length ?? 9;

  // Verdict Banner Configurations
  const verdictConfigs = {
    PASS: {
      className: 'verdict-pass',
      icon: '🛡️',
      title: 'COMPLIANT',
      subtitle: `All ${passedCount} applicable statutory declarations verified under Legal Metrology Rules, 2011.`,
      actionHint: 'Package meets mandatory packaging standards on this panel.',
    },
    FAIL: {
      className: 'verdict-fail',
      icon: '⚠️',
      title: 'NON-COMPLIANT',
      subtitle: `${failedCount} statutory rule violation(s) identified. Immediate remediation required.`,
      actionHint: 'Prohibited unit format, missing tax disclaimer, or bare numeric quantity detected.',
    },
    FLAGGED_FOR_REVIEW: {
      className: 'verdict-review',
      icon: '🔍',
      title: 'REVIEW REQUIRED',
      subtitle: `${reviewCount} declaration(s) unverified or not detected on this single packaging view.`,
      actionHint: 'Human verification required to inspect other package panels (rear/side).',
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

  return (
    <div className="result-screen">
      {/* 1. Prominent Verdict Banner */}
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

      {/* 2. Key Metrics Summary Grid */}
      <section className="metrics-grid" aria-label="Compliance Summary">
        <div className="metric-cell cell-total">
          <span className="metric-val">{totalRules}</span>
          <span className="metric-lbl">Rules</span>
        </div>
        <div className="metric-cell cell-pass">
          <span className="metric-val">{passedCount}</span>
          <span className="metric-lbl">Passed</span>
        </div>
        {failedCount > 0 && (
          <div className="metric-cell cell-fail">
            <span className="metric-val">{failedCount}</span>
            <span className="metric-lbl">Failed</span>
          </div>
        )}
        <div className="metric-cell cell-review">
          <span className="metric-val">{reviewCount}</span>
          <span className="metric-lbl">Review</span>
        </div>
        {naCount > 0 && (
          <div className="metric-cell cell-na">
            <span className="metric-val">{naCount}</span>
            <span className="metric-lbl">Exempt</span>
          </div>
        )}
      </section>

      {/* 3. Package Thumbnail & Metadata Snapshot */}
      <section className="package-snapshot-card">
        {previewUrl && (
          <div className="snapshot-thumb">
            <img src={previewUrl} alt="Inspected package thumbnail" />
          </div>
        )}
        <div className="snapshot-details">
          <h4 className="snapshot-product">
            {extraction?.common_or_generic_name?.value ||
              extraction?.product_name?.value ||
              'Packaged Commodity'}
          </h4>
          {extraction?.product_name?.value &&
            extraction?.common_or_generic_name?.value &&
            extraction?.product_name?.value !== extraction?.common_or_generic_name?.value && (
              <span className="snapshot-brand">
                Brand: {extraction.product_name.value}
              </span>
            )}
          <div className="snapshot-meta-tags">
            {processing_time_ms && (
              <span className="meta-tag">{processing_time_ms} ms</span>
            )}
            {model_used && <span className="meta-tag">{model_used}</span>}
          </div>
        </div>
      </section>

      {/* 4. Human Review Action Callout (For FLAGGED_FOR_REVIEW) */}
      {verdict === 'FLAGGED_FOR_REVIEW' && (
        <div className="review-notice-box">
          <div className="notice-icon-col">⚠️</div>
          <div className="notice-text-col">
            <strong>Human Inspector Review Required</strong>
            <p>
              Rule 6 statutory requirements not visible on this photo may be printed on the back or sides of the package.
            </p>
          </div>
        </div>
      )}

      {/* 5. View Switcher (Statutory Rules vs Label Declarations) */}
      <div className="view-switch-row" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'RULES'}
          className={`switch-btn ${activeTab === 'RULES' ? 'active' : ''}`}
          onClick={() => setActiveTab('RULES')}
        >
          Statutory Rules ({totalRules})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'EXTRACTION'}
          className={`switch-btn ${activeTab === 'EXTRACTION' ? 'active' : ''}`}
          onClick={() => setActiveTab('EXTRACTION')}
        >
          Label Text ({rawFields.length})
        </button>
      </div>

      {/* 6. Content Section */}
      {activeTab === 'RULES' ? (
        <ComplianceChecklist
          evaluations={compliance?.evaluations || []}
          extraction={extraction || {}}
        />
      ) : (
        <div className="raw-extraction-list">
          <div className="raw-fields-header">
            <h4>Raw Extracted Declarations</h4>
            <span className="raw-fields-sub">Evidence proposed by AI/OCR</span>
          </div>
          {rawFields.map(({ key, label }) => {
            const field = extraction?.[key] || {};
            const isPresent = field.status === 'extracted' && field.value;

            return (
              <div key={key} className={`raw-field-item ${isPresent ? '' : 'field-missing'}`}>
                <div className="field-label-col">
                  <span className="field-title">{label}</span>
                  <span className="field-key">`{key}`</span>
                </div>
                <div className="field-val-col">
                  <span className="field-val-text">
                    {field.value || <span className="text-muted">Not detected on this view</span>}
                  </span>
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
      )}

      {/* 7. Sticky Bottom Action */}
      <div className="result-sticky-footer">
        <button
          type="button"
          className="btn-primary btn-large"
          onClick={onReset}
          id="btn-scan-another"
        >
          <span className="btn-icon">↺</span>
          <span>Scan Another Package</span>
        </button>
      </div>
    </div>
  );
}
