import React, { useState } from 'react';

/**
 * GTIN / Product Identity Card
 *
 * Displays:
 * 1. Resolved GTIN and barcode format
 * 2. Overall identity status (MATCH, PARTIAL_MATCH, MISMATCH, NOT_VERIFIABLE)
 * 3. Registry lookup status (FOUND, NOT_FOUND, SERVICE_UNAVAILABLE, AMBIGUOUS_GTIN, etc.)
 * 4. Product identity record (Brand, Product Name, Net Qty, Company, Source)
 * 5. Field-level comparisons (Label/OCR value vs GTIN registry value)
 * 6. Neutral interpretation callout (no alarmist words like counterfeit/fake)
 */
export default function GTINIdentityCard({ gtinIdentity, barcode }) {
  const [showComparisons, setShowComparisons] = useState(true);

  if (!gtinIdentity && !barcode) {
    return null;
  }

  const identityStatus = gtinIdentity?.overall_status || 'NOT_VERIFIABLE';
  const lookupStatus = gtinIdentity?.lookup_status || (barcode?.detected ? 'FOUND' : 'NO_GTIN_DETECTED');
  const targetGtin = gtinIdentity?.gtin || barcode?.primary_gtin;
  const productRecord = gtinIdentity?.product_record;
  const comparisons = gtinIdentity?.field_comparisons || [];

  // When a valid GTIN is resolved, display the format belonging to that GTIN barcode.
  // When no valid GTIN is resolved, do not display QR_CODE as if it were the GTIN format.
  const gtinFormat = (() => {
    if (targetGtin) {
      const matching = barcode?.barcodes?.find(
        (b) => (b.gtin === targetGtin || b.raw_value === targetGtin) && b.is_valid_gtin
      );
      if (matching?.format) return matching.format;
      const anyValid = barcode?.barcodes?.find((b) => b.is_valid_gtin);
      if (anyValid?.format) return anyValid.format;
    }
    return null;
  })();

  const isOFF =
    gtinIdentity?.provider_name === 'Open Food Facts' ||
    productRecord?.source === 'Open Food Facts' ||
    gtinIdentity?.summary?.includes('Open Food Facts') ||
    (gtinIdentity?.provider_name !== 'GS1 / DataKart' &&
      productRecord?.source !== 'LOCAL_GS1_FIXTURE' &&
      productRecord?.source !== 'GS1 India' &&
      productRecord?.source !== 'DataKart');

  // Status Badge Configuration
  const identityConfigs = {
    MATCH: {
      label: 'IDENTITY MATCH',
      icon: '✓',
      badgeClass: 'gtin-badge-match',
      boxClass: 'gtin-box-match',
      interpretation: isOFF
        ? 'Packaging label declarations match the Open Food Facts product record.'
        : 'Packaging label declarations match the registered GS1 India / DataKart product identity.',
    },
    PARTIAL_MATCH: {
      label: 'PARTIAL MATCH',
      icon: '≈',
      badgeClass: 'gtin-badge-partial',
      boxClass: 'gtin-box-partial',
      interpretation: isOFF
        ? 'Packaging declarations partially align with the Open Food Facts product record. No direct contradictions detected.'
        : 'Packaging declarations partially align with the registered GS1 India / DataKart record. No direct contradictions detected.',
    },
    MISMATCH: {
      label: 'IDENTITY MISMATCH',
      icon: '≠',
      badgeClass: 'gtin-badge-mismatch',
      boxClass: 'gtin-box-mismatch',
      interpretation: isOFF
        ? 'Label information differs from the available Open Food Facts product record. Review recommended.'
        : 'Label information differs from the available GS1 India / DataKart record. Review recommended.',
    },
    NOT_VERIFIABLE: {
      label: 'NOT VERIFIED',
      icon: '—',
      badgeClass: 'gtin-badge-unverified',
      boxClass: 'gtin-box-unverified',
      interpretation: isOFF
        ? (lookupStatus === 'NOT_FOUND'
            ? `GTIN ${targetGtin || 'barcode'} was not found in Open Food Facts. Product identity could not be verified against the available product database.`
            : (gtinIdentity?.summary || 'Product identity could not be verified against Open Food Facts.'))
        : (gtinIdentity?.summary || 'Product identity could not be verified against an authoritative registry.'),
    },
  };

  const lookupLabels = {
    FOUND: {
      text: isOFF ? 'Found in Open Food Facts' : 'Registered in GS1 / DataKart',
      icon: '📦',
      class: 'lookup-pill-found',
    },
    NOT_FOUND: {
      text: isOFF ? 'Not in Open Food Facts' : 'Not in GS1 / DataKart Registry',
      icon: '❓',
      class: 'lookup-pill-muted',
    },
    SERVICE_UNAVAILABLE: {
      text: isOFF ? 'Open Food Facts Unavailable' : 'Registry Service Unavailable',
      icon: '⚡',
      class: 'lookup-pill-warn',
    },
    AMBIGUOUS_GTIN: { text: 'Multiple Barcodes Detected', icon: '🔀', class: 'lookup-pill-warn' },
    INVALID_GTIN: { text: 'Invalid Barcode / Check Digit', icon: '⚠️', class: 'lookup-pill-fail' },
    NO_GTIN_DETECTED: { text: 'No Barcode Detected', icon: '🔍', class: 'lookup-pill-muted' },
  };

  const fieldLabels = {
    product_name: 'Product Title',
    brand: 'Brand Name',
    net_quantity: 'Net Quantity',
    manufacturer: 'Manufacturer',
  };

  const fieldStatusPills = {
    MATCH: { label: 'MATCH', icon: '✓', class: 'pill-match' },
    PARTIAL_MATCH: { label: 'PARTIAL', icon: '≈', class: 'pill-partial' },
    MISMATCH: { label: 'MISMATCH', icon: '≠', class: 'pill-mismatch' },
    NOT_COMPARABLE: { label: 'N/A', icon: '—', class: 'pill-na' },
  };

  const currentConfig = identityConfigs[identityStatus] || identityConfigs.NOT_VERIFIABLE;
  const currentLookup = lookupLabels[lookupStatus] || lookupLabels.NO_GTIN_DETECTED;

  return (
    <section className={`gtin-identity-card ${currentConfig.boxClass}`} aria-label="GTIN Product Identity">
      {/* 1. Header Bar */}
      <div className="gtin-card-header">
        <div className="gtin-header-left">
          <span className="gtin-card-icon">🏷️</span>
          <div className="gtin-header-titles">
            <h3 className="gtin-card-title">GTIN / Product Identity</h3>
            <span className="gtin-sub-text">
              {isOFF ? 'Open Food Facts' : 'GS1 India / DataKart Registry'}
            </span>
          </div>
        </div>
        <span className={`gtin-status-pill ${currentConfig.badgeClass}`}>
          <span className="gtin-pill-icon">{currentConfig.icon}</span>
          <span className="gtin-pill-text">{currentConfig.label}</span>
        </span>
      </div>

      {/* 2. Metadata Chips Strip */}
      <div className="gtin-meta-row">
        <div className="gtin-code-chip">
          <span className="chip-label">GTIN</span>
          <span className="chip-value">{targetGtin || 'None Verified'}</span>
        </div>

        {gtinFormat && (
          <div className="gtin-format-chip">
            <span className="chip-label">FORMAT</span>
            <span className="chip-value">{gtinFormat}</span>
          </div>
        )}

        <div className={`gtin-lookup-pill ${currentLookup.class}`}>
          <span className="lookup-icon">{currentLookup.icon}</span>
          <span>{currentLookup.text}</span>
        </div>
      </div>

      {/* 3. Product Registry Record (when available) */}
      {productRecord && (
        <div className="gtin-record-box">
          <div className="gtin-record-grid">
            <div className="gtin-record-item">
              <span className="record-lbl">Brand</span>
              <strong className="record-val">{productRecord.brand_name || '—'}</strong>
            </div>
            <div className="gtin-record-item">
              <span className="record-lbl">Product Name</span>
              <strong className="record-val">{productRecord.product_name || productRecord.product_description || '—'}</strong>
            </div>
            <div className="gtin-record-item">
              <span className="record-lbl">Manufacturer</span>
              <strong className="record-val">{productRecord.company_name || '—'}</strong>
            </div>
            <div className="gtin-record-item">
              <span className="record-lbl">Net Quantity</span>
              <strong className="record-val">
                {productRecord.net_quantity ? `${productRecord.net_quantity} ${productRecord.net_quantity_unit || ''}`.trim() : '—'}
              </strong>
            </div>
          </div>
          {productRecord.source && (
            <div className="gtin-source-row">
              <span className="source-tag">Source: {productRecord.source}</span>
            </div>
          )}
        </div>
      )}

      {/* 4. Field Comparisons Table */}
      {comparisons.length > 0 && (
        <div className="gtin-comparisons-section">
          <button
            type="button"
            className="gtin-collapse-btn"
            onClick={() => setShowComparisons(!showComparisons)}
            aria-expanded={showComparisons}
          >
            <span className="collapse-title">
              Declaration vs {isOFF ? 'Open Food Facts' : 'Registry'} Reconciliation ({comparisons.length})
            </span>
            <span className="collapse-arrow">{showComparisons ? '▲' : '▼'}</span>
          </button>

          {showComparisons && (
            <div className="gtin-comparisons-table">
              <div className="comparisons-table-head">
                <span className="col-field">Field</span>
                <span className="col-label">Packaging Label</span>
                <span className="col-registry">
                  {isOFF ? 'Open Food Facts' : 'Registry Record'}
                </span>
                <span className="col-status">Status</span>
              </div>
              {comparisons.map((c, idx) => {
                const pill = fieldStatusPills[c.status] || fieldStatusPills.NOT_COMPARABLE;
                const fieldTitle = fieldLabels[c.field_name] || c.field_name;

                return (
                  <div key={idx} className="comparisons-table-row">
                    <div className="col-field">
                      <strong>{fieldTitle}</strong>
                    </div>
                    <div className="col-label">
                      <span>{c.ocr_value || <span className="text-muted">Not extracted</span>}</span>
                    </div>
                    <div className="col-registry">
                      <span>{c.gtin_value || <span className="text-muted">Not specified</span>}</span>
                    </div>
                    <div className="col-status">
                      <span className={`comp-pill ${pill.class}`} title={c.message}>
                        <span className="comp-pill-icon">{pill.icon}</span>
                        <span className="comp-pill-text">{pill.label}</span>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* 5. Status Interpretation Callout */}
      <div className="gtin-interpretation-box">
        <span className="interpretation-icon">
          {identityStatus === 'MATCH' ? '🛡️' : identityStatus === 'MISMATCH' ? 'ℹ️' : '🔍'}
        </span>
        <div className="interpretation-text">
          <p>{currentConfig.interpretation}</p>
        </div>
      </div>
    </section>
  );
}
