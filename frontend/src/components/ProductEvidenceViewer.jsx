import React, { useState } from 'react';

/**
 * ProductEvidenceViewer
 * 
 * Displays the verified product evidence image for the identified packaged commodity.
 * Data-driven and GTIN-based. Completely generic across all products.
 * 
 * Strict constraints:
 * - Single evidence image per product.
 * - Zero prototype / temporary wording.
 * - Zero product-specific hardcoding (e.g. no if-gtin checks).
 */
export default function ProductEvidenceViewer({ productEvidence }) {
  const [imageError, setImageError] = useState(false);

  const evidenceImageUrl = productEvidence?.evidence_image;
  const productName = productEvidence?.product_name;
  const gtin = productEvidence?.gtin;

  const hasEvidence = Boolean(evidenceImageUrl) && !imageError;

  return (
    <div className="product-evidence-card">
      <div className="product-evidence-header">
        <div className="evidence-header-left">
          <span className="evidence-header-icon">📷</span>
          <div>
            <h4 className="evidence-header-title">Product Evidence</h4>
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
              <span className="empty-icon">📋</span>
            </div>
            <h5 className="empty-title">Evidence image not available for this product.</h5>
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
