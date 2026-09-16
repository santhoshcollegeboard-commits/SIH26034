import { useState, useRef } from 'react';
import { NOT_AVAILABLE, formatSourceRegion } from '../services/formatters';

/**
 * Visual bounding box inspection modal/overlay on package image.
 * Never estimates or fabricates coordinates.
 */
export default function BoundingBoxOverlay({ imageSrc, fieldName, label, sourceRegion, confidence, onClose }) {
  const [naturalSize, setNaturalSize] = useState({ width: 0, height: 0 });
  const imgRef = useRef(null);

  const hasCoords =
    sourceRegion &&
    typeof sourceRegion === 'object' &&
    sourceRegion.x !== undefined &&
    sourceRegion.y !== undefined &&
    sourceRegion.width !== undefined &&
    sourceRegion.height !== undefined &&
    sourceRegion.width > 0 &&
    sourceRegion.height > 0;

  function handleImageLoad(e) {
    setNaturalSize({
      width: e.target.naturalWidth || 1,
      height: e.target.naturalHeight || 1,
    });
  }

  // Calculate percentage positions if coordinates are valid
  const boxStyle = hasCoords && naturalSize.width > 0 && naturalSize.height > 0
    ? {
        left: `${(sourceRegion.x / naturalSize.width) * 100}%`,
        top: `${(sourceRegion.y / naturalSize.height) * 100}%`,
        width: `${(sourceRegion.width / naturalSize.width) * 100}%`,
        height: `${(sourceRegion.height / naturalSize.height) * 100}%`,
      }
    : null;

  return (
    <div className="modal-backdrop" onClick={onClose} id="bbox-modal-backdrop">
      <div className="modal-content bbox-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <h3 className="modal-title">Source Region Evidence</h3>
            <span className="modal-subtitle">{label || fieldName}</span>
          </div>
          <button className="btn-close" onClick={onClose} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="bbox-metadata-bar">
          <div className="bbox-meta-item">
            <span className="meta-label">Coordinates:</span>
            <span className="meta-val font-mono">{formatSourceRegion(sourceRegion)}</span>
          </div>
          {confidence && (
            <div className="bbox-meta-item">
              <span className="meta-label">Confidence:</span>
              <span className="meta-val">{confidence}</span>
            </div>
          )}
        </div>

        <div className="bbox-image-container">
          {imageSrc ? (
            <div className="bbox-image-wrapper">
              <img
                ref={imgRef}
                src={imageSrc}
                alt={`Evidence for ${label || fieldName}`}
                className="bbox-target-image"
                onLoad={handleImageLoad}
              />
              {boxStyle && (
                <div className="bbox-highlight-rect" style={boxStyle}>
                  <div className="bbox-tag">{label || fieldName}</div>
                </div>
              )}
            </div>
          ) : (
            <div className="bbox-no-image">
              <span>Image preview not available for bounding box overlay.</span>
            </div>
          )}

          {!hasCoords && (
            <div className="bbox-unavailable-notice">
              <span className="notice-icon">ℹ</span>
              <span>Source region: {NOT_AVAILABLE}</span>
            </div>
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={onClose}>
            Close Evidence Inspector
          </button>
        </div>
      </div>
    </div>
  );
}
