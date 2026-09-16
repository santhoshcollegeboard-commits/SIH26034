import { useState, useRef } from 'react';
import { api } from '../services/api';
import QualityGateCard from '../components/QualityGateCard';
import DeclarationsTable from '../components/DeclarationsTable';
import RuleEvaluationsCard from '../components/RuleEvaluationsCard';
import { getDispositionTheme } from '../services/formatters';

export default function InspectorWorkflow({ onInspectionCompleted, onSwitchToReviewer }) {
  // Capture state
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [imageMeta, setImageMeta] = useState({ name: '', type: '', size: 0, width: 0, height: 0 });
  const [packageId, setPackageId] = useState('');
  const [isImported, setIsImported] = useState(false);
  const [isThirdParty, setIsThirdParty] = useState(false);

  // Workflow progress state
  const [stage, setStage] = useState('capture'); // 'capture' | 'processing' | 'evaluated' | 'failed_quality'
  const [loadingMsg, setLoadingMsg] = useState('');
  const [error, setError] = useState(null);

  // Backend response state
  const [extractionResponse, setExtractionResponse] = useState(null);
  const [recordedInspectionId, setRecordedInspectionId] = useState(null);

  const fileInputRef = useRef(null);
  const dropRef = useRef(null);

  function handleFileSelect(selectedFile) {
    if (!selectedFile) return;
    const allowed = ['image/jpeg', 'image/png', 'image/webp'];
    if (!allowed.includes(selectedFile.type)) {
      setError("Unsupported image format. Please select a JPEG, PNG, or WEBP image.");
      return;
    }

    const previewUrl = URL.createObjectURL(selectedFile);
    setFile(selectedFile);
    setPreview(previewUrl);
    setError(null);
    setExtractionResponse(null);
    setRecordedInspectionId(null);
    setStage('capture');

    // Read natural dimensions
    const img = new Image();
    img.onload = () => {
      setImageMeta({
        name: selectedFile.name,
        type: selectedFile.type,
        size: selectedFile.size,
        width: img.naturalWidth,
        height: img.naturalHeight,
      });
    };
    img.src = previewUrl;
  }

  function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dropRef.current?.classList.remove('drag-over');
    const droppedFile = e.dataTransfer.files?.[0];
    handleFileSelect(droppedFile);
  }

  function handleReset() {
    setFile(null);
    setPreview(null);
    setImageMeta({ name: '', type: '', size: 0, width: 0, height: 0 });
    setPackageId('');
    setError(null);
    setExtractionResponse(null);
    setRecordedInspectionId(null);
    setStage('capture');
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function handleStartInspection() {
    if (!file) {
      setError('Please select an image first.');
      return;
    }

    setStage('processing');
    setLoadingMsg('Running Image Quality Gate & AI Extraction...');
    setError(null);

    try {
      // 1. Call POST /api/extract
      const extractData = await api.extractAndEvaluate(file, isImported, isThirdParty);
      setExtractionResponse(extractData);

      // Check Quality Gate
      if (extractData.quality && !extractData.quality.is_acceptable) {
        setStage('failed_quality');
        return;
      }

      if (!extractData.success && !extractData.compliance) {
        setError(extractData.error || 'Inspection evaluation failed.');
        setStage('capture');
        return;
      }

      // 2. Automatically record in SQLite Evidence Ledger
      setLoadingMsg('Persisting inspection to Evidence Ledger...');
      const evidenceInput = {
        filename: imageMeta.name,
        media_type: imageMeta.type,
        file_size_bytes: imageMeta.size,
        image_width: imageMeta.width,
        image_height: imageMeta.height,
        quality_assessment: extractData.quality || null,
      };

      const ledgerRes = await api.recordInspection({
        packageId: packageId.trim() || null,
        evidence: evidenceInput,
        extraction: extractData.result,
        compliance: extractData.compliance,
        metadata: {
          captured_by_role: 'inspector',
          is_imported: isImported,
          is_packed_by_third_party: isThirdParty,
        },
      });

      const newId = ledgerRes.inspection?.inspection_id;
      setRecordedInspectionId(newId);
      setStage('evaluated');
    } catch (err) {
      setError(err.message || 'An unexpected error occurred during inspection.');
      setStage('capture');
    }
  }

  const compliance = extractionResponse?.compliance;
  const disposition = compliance?.overall_disposition;
  const dispositionTheme = disposition ? getDispositionTheme(disposition) : null;
  const isReviewRequired = disposition === 'REVIEW_REQUIRED';

  return (
    <div className="inspector-workflow-container" id="inspector-workflow">
      {/* Screen Header */}
      <div className="section-header">
        <h2 className="section-title">PackCheck Inspection</h2>
        <p className="section-sub">
          Capture or upload a clear image of the packaged commodity for compliance inspection pursuant to Legal Metrology Rules, 2011.
        </p>
      </div>

      {error && (
        <div className="error-banner mb-4" id="inspector-error-banner">
          <span className="error-icon">⚠️</span>
          <span>{error}</span>
        </div>
      )}

      {/* Screen 1: Capture Area */}
      <div className="card capture-card mb-4" id="capture-card">
        <div
          ref={dropRef}
          className={`drop-zone ${preview ? 'has-preview' : ''}`}
          onClick={() => !preview && fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={(e) => {
            e.preventDefault();
            dropRef.current?.classList.add('drag-over');
          }}
          onDragLeave={(e) => {
            e.preventDefault();
            dropRef.current?.classList.remove('drag-over');
          }}
          id="inspector-drop-zone"
        >
          {preview ? (
            <div className="preview-display">
              <img src={preview} alt="Package capture" className="image-preview" id="captured-image-preview" />
            </div>
          ) : (
            <div className="drop-placeholder">
              <div className="drop-icon">📦</div>
              <div className="drop-text">Drop a packaged commodity image here</div>
              <div className="drop-sub">or click to browse · JPEG, PNG, WEBP (Max 10MB)</div>
            </div>
          )}
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp"
          onChange={(e) => handleFileSelect(e.target.files?.[0])}
          style={{ display: 'none' }}
          id="inspector-file-input"
        />

        {/* Image Metadata Bar when selected */}
        {preview && (
          <div className="file-meta-bar mt-3">
            <div className="meta-item">
              <span className="meta-label">File:</span>
              <span className="meta-val font-mono">{imageMeta.name}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Format:</span>
              <span className="meta-val">{imageMeta.type}</span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Dimensions:</span>
              <span className="meta-val font-mono">
                {imageMeta.width && imageMeta.height ? `${imageMeta.width} × ${imageMeta.height} px` : 'Reading...'}
              </span>
            </div>
            <div className="meta-item">
              <span className="meta-label">Size:</span>
              <span className="meta-val font-mono">{(imageMeta.size / 1024).toFixed(1)} KB</span>
            </div>
          </div>
        )}

        {/* Inspection Inputs */}
        <div className="inspection-options-grid mt-4">
          <div className="form-group">
            <label className="input-label" htmlFor="input-pkg-id">Package Identifier (Optional):</label>
            <input
              id="input-pkg-id"
              type="text"
              className="form-control"
              value={packageId}
              onChange={(e) => setPackageId(e.target.value)}
              placeholder="e.g. PKG-2026-088"
              disabled={stage === 'processing'}
            />
          </div>

          <div className="form-toggles">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isImported}
                onChange={(e) => setIsImported(e.target.checked)}
                disabled={stage === 'processing'}
              />
              <span>Imported Commodity (requires importer details)</span>
            </label>

            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isThirdParty}
                onChange={(e) => setIsThirdParty(e.target.checked)}
                disabled={stage === 'processing'}
              />
              <span>Packed by Third-Party (requires packer details)</span>
            </label>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="action-buttons mt-4">
          {preview && (
            <button
              className="btn btn-secondary"
              onClick={handleReset}
              disabled={stage === 'processing'}
              id="btn-reset-capture"
            >
              Clear Image
            </button>
          )}
          {!preview && (
            <button
              className="btn btn-secondary"
              onClick={() => fileInputRef.current?.click()}
              id="btn-choose-file"
            >
              Choose Image
            </button>
          )}
          <button
            className="btn btn-primary"
            onClick={handleStartInspection}
            disabled={!file || stage === 'processing'}
            id="btn-start-inspection"
          >
            {stage === 'processing' ? (
              <span className="btn-loading">
                <span className="spinner" /> {loadingMsg}
              </span>
            ) : (
              '⚡ Start Inspection'
            )}
          </button>
        </div>
      </div>

      {/* Quality Gate Failure State */}
      {stage === 'failed_quality' && extractionResponse?.quality && (
        <div className="mb-4">
          <QualityGateCard
            quality={extractionResponse.quality}
            onRecapture={handleReset}
          />
        </div>
      )}

      {/* Evaluated Inspection Output */}
      {stage === 'evaluated' && extractionResponse && (
        <div className="evaluated-output-section" id="evaluated-output-section">
          {/* Quality Gate Status */}
          <div className="mb-4">
            <QualityGateCard quality={extractionResponse.quality} />
          </div>

          {/* Disposition Banner */}
          {dispositionTheme && (
            <div className={`disposition-banner ${dispositionTheme.bannerClass} mb-4`} id="inspection-disposition-banner">
              <div className="banner-left">
                <span className="banner-icon">{dispositionTheme.icon}</span>
                <div>
                  <div className="banner-label">STATUTORY COMPLIANCE OUTCOME</div>
                  <h3 className="banner-disposition">{dispositionTheme.label}</h3>
                </div>
              </div>
              <div className="banner-right">
                {recordedInspectionId && (
                  <div className="ledger-id-tag font-mono">
                    ID: {recordedInspectionId}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* If REVIEW_REQUIRED: Callout for human review */}
          {isReviewRequired && (
            <div className="review-prompt-card mb-4" id="review-required-prompt">
              <div className="prompt-header">
                <span className="prompt-icon">⚠️</span>
                <div>
                  <h4 className="prompt-title">Human Review Required</h4>
                  <p className="prompt-desc">
                    One or more mandatory declarations have observation uncertainty or borderline confidence. An authorized Reviewer must inspect the recorded evidence.
                  </p>
                </div>
              </div>
              <div className="prompt-actions">
                <button
                  className="btn btn-primary btn-sm"
                  onClick={() => onSwitchToReviewer && onSwitchToReviewer(recordedInspectionId)}
                  id="btn-goto-review"
                >
                  🕵️ Switch to Reviewer &amp; Resolve
                </button>
                {recordedInspectionId && (
                  <button
                    className="btn btn-secondary btn-sm"
                    onClick={() => onInspectionCompleted && onInspectionCompleted(recordedInspectionId)}
                  >
                    View Result Record
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Extracted Declarations Table */}
          <div className="mb-4">
            <DeclarationsTable
              declarations={extractionResponse.result}
              imageSrc={preview}
            />
          </div>

          {/* Rule Evaluations Table */}
          {compliance?.rule_evaluations && (
            <div className="mb-4">
              <RuleEvaluationsCard evaluations={compliance.rule_evaluations} />
            </div>
          )}

          {/* Completion Button */}
          <div className="completion-bar mt-4">
            <button className="btn btn-secondary" onClick={handleReset}>
              📸 Capture Another Package
            </button>
            {recordedInspectionId && (
              <button
                className="btn btn-primary"
                onClick={() => onInspectionCompleted && onInspectionCompleted(recordedInspectionId)}
                id="btn-view-official-result"
              >
                📄 View Official Result &amp; PDF Report →
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
