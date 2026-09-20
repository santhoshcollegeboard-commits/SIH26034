import React, { useState } from 'react';

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
 * ProductEvidenceViewer
 * 
 * Displays verified product evidence imagery for the identified commodity.
 * Generic across all products; data-driven from backend evidence service.
 */
export default function ProductEvidenceViewer({ productEvidence }) {
  const [imageError, setImageError] = useState(false);

  const evidenceImageUrl = productEvidence?.evidence_image;
  const productName = productEvidence?.product_name;
  const gtin = productEvidence?.gtin;

  const hasEvidence = Boolean(evidenceImageUrl) && !imageError;

  return (
    <div className="product-evidence-card" aria-label="Product Packaging Evidence">
      <div className="product-evidence-header">
        <div className="evidence-header-left">
          <div className="evidence-icon-wrap">
            <CameraIcon size={16} className="evidence-header-icon" />
          </div>
          <div>
            <h4 className="evidence-header-title">Product Evidence Localization</h4>
            <span className="evidence-header-sub">
              {productName || (gtin ? `GTIN: ${gtin}` : 'Packaged Commodity')}
            </span>
          </div>
        </div>
        {gtin && (
          <span className="evidence-gtin-badge">GTIN {gtin}</span>
        )}
      </div>

      <div className="product-evidence-body">
        {hasEvidence ? (
          <div className="evidence-image-viewport">
            <img
              src={evidenceImageUrl}
              alt={productName ? `${productName} Evidence` : 'Product packaging declarations evidence'}
              className="evidence-main-img"
              onError={() => setImageError(true)}
            />
          </div>
        ) : (
          <div className="evidence-empty-box">
            <div className="empty-icon-circle">
              <FileTextIcon size={18} className="empty-icon" />
            </div>
            <h5 className="empty-title">Evidence image not available for this commodity.</h5>
            <p className="empty-desc">
              {gtin
                ? `Standard verified evidence imagery is not currently indexed for GTIN ${gtin}.`
                : 'No evidence image is currently available for the inspected package.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
