import React, { useState } from 'react';

/**
 * High-precision SVG icons for GTIN / Product Identity Card.
 */
function BarcodeIcon({ className = '', size = 16 }) {
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
      <path d="M3 5v14" />
      <path d="M8 5v14" />
      <path d="M12 5v14" />
      <path d="M17 5v14" />
      <path d="M21 5v14" />
    </svg>
  );
}

function CheckIcon({ className = '', size = 12 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="3"
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <polyline points="20 6 9 17 4 12" />
    </svg>
  );
}

function AlertTriangleIcon({ className = '', size = 13 }) {
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

function ShieldCheckIcon({ className = '', size = 15 }) {
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

function InfoIcon({ className = '', size = 14 }) {
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
      <line x1="12" y1="16" x2="12" y2="12" />
      <line x1="12" y1="8" x2="12.01" y2="8" />
    </svg>
  );
}

function SearchIcon({ className = '', size = 13 }) {
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

function ChevronDownIcon({ className = '', size = 14 }) {
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
      <polyline points="6 9 12 15 18 9" />
    </svg>
  );
}

function ChevronUpIcon({ className = '', size = 14 }) {
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
      <polyline points="18 15 12 9 6 15" />
    </svg>
  );
}

/**
 * GTIN / Product Identity Card
 *
 * Displays:
 * 1. Resolved GTIN and barcode format
 * 2. Overall identity status (MATCH, PARTIAL_MATCH, MISMATCH, NOT_VERIFIABLE)
 * 3. Lookup status
 * 4. Product identity record (Brand, Product Name, Net Qty, Company)
 * 5. Field-level comparisons (Packaging Label vs GTIN Data)
 * 6. Neutral interpretation callout
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

  // Status Badge Configuration
  const identityConfigs = {
    MATCH: {
      label: 'GTIN MATCH',
      icon: <CheckIcon size={12} />,
      badgeClass: 'gtin-badge-match',
      boxClass: 'gtin-box-match',
      interpretation: 'Packaging declarations match the GTIN product data.',
    },
    PARTIAL_MATCH: {
      label: 'PARTIAL MATCH',
      icon: <span>≈</span>,
      badgeClass: 'gtin-badge-partial',
      boxClass: 'gtin-box-partial',
      interpretation:
        'Packaging declarations partially match the GTIN product data. No direct contradictions detected.',
    },
    MISMATCH: {
      label: 'IDENTITY MISMATCH',
      icon: <span>≠</span>,
      badgeClass: 'gtin-badge-mismatch',
      boxClass: 'gtin-box-mismatch',
      interpretation: 'Label declarations differ from the GTIN product data. Review recommended.',
    },
    NOT_VERIFIABLE: {
      label: 'GTIN NOT VERIFIED',
      icon: <span>—</span>,
      badgeClass: 'gtin-badge-unverified',
      boxClass: 'gtin-box-unverified',
      interpretation:
        lookupStatus === 'SERVICE_UNAVAILABLE'
          ? 'GTIN verification unavailable.'
          : 'GTIN product data could not be verified.',
    },
  };

  const lookupLabels = {
    FOUND: {
      text: 'GTIN Verified',
      icon: <CheckIcon size={12} />,
      class: 'lookup-pill-found',
    },
    NOT_FOUND: {
      text: 'GTIN NOT VERIFIED',
      icon: <SearchIcon size={12} />,
      class: 'lookup-pill-muted',
    },
    SERVICE_UNAVAILABLE: {
      text: 'GTIN verification unavailable.',
      icon: <InfoIcon size={12} />,
      class: 'lookup-pill-warn',
    },
    AMBIGUOUS_GTIN: {
      text: 'Multiple Barcodes Detected',
      icon: <AlertTriangleIcon size={12} />,
      class: 'lookup-pill-warn',
    },
    INVALID_GTIN: {
      text: 'Invalid Barcode / Check Digit',
      icon: <AlertTriangleIcon size={12} />,
      class: 'lookup-pill-fail',
    },
    NO_GTIN_DETECTED: {
      text: 'No Barcode Detected',
      icon: <SearchIcon size={12} />,
      class: 'lookup-pill-muted',
    },
  };

  const fieldLabels = {
    product_name: 'Product Title',
    brand: 'Brand Name',
    net_quantity: 'Net Quantity',
    manufacturer: 'Manufacturer',
  };

  const fieldStatusPills = {
    MATCH: { label: 'MATCH', icon: <CheckIcon size={10} />, class: 'pill-match' },
    PARTIAL_MATCH: { label: 'PARTIAL', icon: <span>≈</span>, class: 'pill-partial' },
    MISMATCH: { label: 'MISMATCH', icon: <span>≠</span>, class: 'pill-mismatch' },
    NOT_COMPARABLE: { label: 'N/A', icon: <span>—</span>, class: 'pill-na' },
  };

  const currentConfig = identityConfigs[identityStatus] || identityConfigs.NOT_VERIFIABLE;
  const currentLookup = lookupLabels[lookupStatus] || lookupLabels.NO_GTIN_DETECTED;

  return (
    <section className={`gtin-identity-card ${currentConfig.boxClass}`} aria-label="GTIN Product Identity">
      {/* 1. Header Bar */}
      <div className="gtin-card-header">
        <div className="gtin-header-left">
          <div className="gtin-card-icon-wrap">
            <BarcodeIcon size={16} className="gtin-card-icon" />
          </div>
          <div className="gtin-header-titles">
            <h3 className="gtin-card-title">GTIN / Product Identity</h3>
            <span className="gtin-sub-text">GTIN Product Identity</span>
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

        {lookupStatus !== 'FOUND' && (
          <div className={`gtin-lookup-pill ${currentLookup.class}`}>
            <span className="lookup-icon">{currentLookup.icon}</span>
            <span>{currentLookup.text}</span>
          </div>
        )}
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
              <strong className="record-val">
                {productRecord.product_name || productRecord.product_description || '—'}
              </strong>
            </div>
            <div className="gtin-record-item">
              <span className="record-lbl">Manufacturer</span>
              <strong className="record-val">{productRecord.company_name || '—'}</strong>
            </div>
            <div className="gtin-record-item">
              <span className="record-lbl">Net Quantity</span>
              <strong className="record-val">
                {productRecord.net_quantity
                  ? `${productRecord.net_quantity} ${productRecord.net_quantity_unit || ''}`.trim()
                  : '—'}
              </strong>
            </div>
          </div>
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
              Declaration vs GTIN Data Reconciliation ({comparisons.length})
            </span>
            <span className="collapse-arrow">
              {showComparisons ? <ChevronUpIcon size={14} /> : <ChevronDownIcon size={14} />}
            </span>
          </button>

          {showComparisons && (
            <div className="gtin-comparisons-table">
              <div className="comparisons-table-head">
                <span className="col-field">Field</span>
                <span className="col-label">Packaging Label</span>
                <span className="col-registry">GTIN Data</span>
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
          {identityStatus === 'MATCH' ? (
            <ShieldCheckIcon size={15} className="text-emerald-600" />
          ) : identityStatus === 'MISMATCH' ? (
            <AlertTriangleIcon size={15} className="text-red-600" />
          ) : (
            <InfoIcon size={15} className="text-slate-500" />
          )}
        </span>
        <div className="interpretation-text">
          <p>{currentConfig.interpretation}</p>
        </div>
      </div>
    </section>
  );
}
