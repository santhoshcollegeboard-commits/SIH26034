import React from 'react';

/**
 * Mobile preview screen shown once an image is captured or selected.
 * Displays package image, file details, and primary "Verify Package" CTA.
 */
export default function ImagePreview({
  file,
  previewUrl,
  onVerify,
  onReset,
  loading = false,
}) {
  const formatFileSize = (bytes) => {
    if (!bytes) return '';
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  return (
    <div className="preview-screen">
      {/* Visual Frame */}
      <div className="preview-card">
        <div className="preview-image-wrapper">
          <img
            src={previewUrl}
            alt="Captured package preview"
            className="preview-img"
          />
        </div>

        <div className="preview-meta-row">
          <div className="meta-left">
            <span className="file-name" title={file?.name}>
              {file?.name || 'package_image.jpg'}
            </span>
            <span className="file-size">{formatFileSize(file?.size)}</span>
          </div>
          <span className="format-tag">{file?.type?.split('/')[1]?.toUpperCase()}</span>
        </div>
      </div>

      {/* Guidelines Pill */}
      <div className="guideline-callout">
        <span className="guideline-icon">ℹ</span>
        <p className="guideline-text">
          Ensure declarations like MRP, Net Qty, and Manufacturer Address are clearly legible.
        </p>
      </div>

      {/* Action Buttons */}
      <div className="preview-actions-footer">
        <button
          type="button"
          className="btn-primary btn-large"
          onClick={onVerify}
          disabled={loading}
          id="btn-start-verification"
        >
          <span className="btn-icon">⚡</span>
          <span>Verify Package</span>
        </button>

        <button
          type="button"
          className="btn-ghost"
          onClick={onReset}
          disabled={loading}
          id="btn-choose-another"
        >
          <span>Retake / Choose Another</span>
        </button>
      </div>
    </div>
  );
}
