import React, { useState } from 'react';
import ComplianceChecklist from './ComplianceChecklist';

/**
 * Mobile Results Screen displaying the overall verdict, summary metrics,
 * statutory compliance checklist, and raw label declarations view.
 */
export default function ResultScreen({
  verificationResponse,
  previewUrl,
  previewUrls = [],
  panels = [],
  onReset,
}) {
  const [activeTab, setActiveTab] = useState('RULES'); // 'RULES' | 'EXTRACTION'

  const {
    compliance,
    extraction,
    processing_time_ms,
    model_used,
    image_count,
    panel_labels,
  } = verificationResponse || {};

  const verdict = compliance?.overall_verdict || 'FLAGGED_FOR_REVIEW';
  const passedCount = compliance?.passed_count ?? 0;
  const failedCount = compliance?.failed_count ?? 0;
  const reviewCount = compliance?.review_count ?? 0;
  const naCount = compliance?.not_applicable_count ?? 0;
  const totalRules = compliance?.evaluations?.length ?? 9;

  // Build list of thumbnails with labels
  const displayThumbnails =
    panels && panels.length > 0
      ? panels.map((p) => ({ url: p.previewUrl, label: p.panelLabel || 'Panel' }))
      : previewUrls && previewUrls.length > 0
      ? previewUrls.map((url, idx) => ({
          url,
          label: panel_labels?.[idx] || `Panel ${idx + 1}`,
        }))
      : previewUrl
      ? [{ url: previewUrl, label: panel_labels?.[0] || 'PDP' }]
      : [];

  const effectivePanelCount = image_count || displayThumbnails.length || 1;

  // Verdict Banner Configurations
  const verdictConfigs = {
    PASS: {
      className: 'verdict-pass',
      icon: '🛡️',
      title: 'COMPLIANT',
      subtitle: `All ${passedCount} statutory declarations verified across ${effectivePanelCount} package ${
        effectivePanelCount === 1 ? 'panel' : 'panels'
      } under Legal Metrology Rules, 2011.`,
      actionHint: 'Package meets mandatory packaging standards across submitted panels.',
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
      subtitle: `${reviewCount} declaration(s) unverified or conflicting across ${effectivePanelCount} package ${
        effectivePanelCount === 1 ? 'panel' : 'panels'
      }.`,
      actionHint:
        effectivePanelCount > 1
          ? 'Human verification required to inspect unverified declarations or resolve cross-panel conflicts.'
          : 'Human verification required to inspect other package panels (rear/side).',
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
        <div className="metric-cell cell-panels">
          <span className="metric-val">{effectivePanelCount}</span>
          <span className="metric-lbl">{effectivePanelCount === 1 ? 'Panel' : 'Panels'}</span>
        </div>
      </section>

      {/* 3. Package Thumbnail & Multi-Panel Snapshot Strip */}
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
            <span className="meta-tag">{effectivePanelCount} Panels Merged</span>
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
              {effectivePanelCount > 1
                ? 'One or more statutory requirements were unreadable, missing, or contradictory across the submitted package panels.'
                : 'Rule 6 statutory requirements not visible on this photo may be printed on the back or sides of the package.'}
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
            <h4>Unified Extracted Declarations</h4>
            <span className="raw-fields-sub">
              Aggregated across {effectivePanelCount} package {effectivePanelCount === 1 ? 'panel' : 'panels'}
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
                      <span className="panel-tag-pill">📌 {field.source_panel_label}</span>
                    )}
                    {isConflict && <span className="conflict-tag-pill">CONFLICT</span>}
                  </div>
                  <span className="field-key">`{key}`</span>
                </div>
                <div className="field-val-col">
                  {isConflict ? (
                    <div className="field-conflict-content">
                      <span className="field-val-text conflict-val">{field.value}</span>
                      <span className="conflict-hint">
                        Inspector review required to confirm valid packaging declaration
                      </span>
                    </div>
                  ) : (
                    <span className="field-val-text">
                      {field.value || (
                        <span className="text-muted">Not detected across submitted panels</span>
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
