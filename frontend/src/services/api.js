/**
 * API service for PackCheck frontend communicating with FastAPI backend.
 *
 * Communicates strictly with backend endpoints:
 * - /health
 * - /api/extract
 * - /api/ledger/inspections
 * - /api/ledger/inspections/{id}
 * - /api/ledger/inspections/{id}/review
 * - /api/review/items
 * - /api/review/submit
 * - /api/result/{id}
 * - /api/result/{id}/pdf
 */

const API_BASE = '';

/**
 * Handle API responses with safe error messages (no stack traces or internal secrets).
 */
async function handleResponse(res, customErrorMsg) {
  if (!res.ok) {
    let errorDetail = customErrorMsg || 'Request failed';
    try {
      const data = await res.json();
      if (data.detail) {
        errorDetail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
      } else if (data.error) {
        errorDetail = data.error;
      }
    } catch {
      // Non-JSON error response
    }
    throw new Error(errorDetail);
  }
  return res.json();
}

export const api = {
  /**
   * Health check endpoint confirming service status.
   */
  async checkHealth() {
    try {
      const res = await fetch(`${API_BASE}/health`);
      if (res.ok) {
        const data = await res.json();
        return data.status === 'ok';
      }
      return false;
    } catch {
      return false;
    }
  },

  /**
   * Post package image for Quality Gate, OCR extraction, and Rule 6 compliance evaluation.
   */
  async extractAndEvaluate(imageFile, isImported = null, isPackedByThirdParty = null) {
    const formData = new FormData();
    formData.append('image', imageFile);
    if (isImported !== null) {
      formData.append('is_imported', String(isImported));
    }
    if (isPackedByThirdParty !== null) {
      formData.append('is_packed_by_third_party', String(isPackedByThirdParty));
    }

    const res = await fetch(`${API_BASE}/api/extract`, {
      method: 'POST',
      body: formData,
    });

    return handleResponse(res, 'Extraction and compliance check failed.');
  },

  /**
   * Record an inspection in the Evidence Ledger.
   */
  async recordInspection({ packageId, evidence, extraction, compliance, metadata }) {
    const res = await fetch(`${API_BASE}/api/ledger/inspections`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        package_id: packageId || null,
        evidence: evidence || null,
        extraction,
        compliance,
        metadata: metadata || {},
      }),
    });

    return handleResponse(res, 'Failed to record inspection in Evidence Ledger.');
  },

  /**
   * Retrieve an inspection and its complete decision trail from the Evidence Ledger.
   */
  async getInspectionTrail(inspectionId) {
    const res = await fetch(`${API_BASE}/api/ledger/inspections/${encodeURIComponent(inspectionId)}`);
    return handleResponse(res, `Inspection ${inspectionId} not found.`);
  },

  /**
   * List recorded inspections from the Evidence Ledger.
   */
  async listInspections(limit = 50, offset = 0) {
    const res = await fetch(`${API_BASE}/api/ledger/inspections?limit=${limit}&offset=${offset}`);
    return handleResponse(res, 'Failed to list inspections.');
  },

  /**
   * Surface items requiring human inspection and resolution.
   */
  async getReviewItems({ extraction, inspection, packageMetadata, rules }) {
    const res = await fetch(`${API_BASE}/api/review/items`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        extraction,
        inspection,
        package_metadata: packageMetadata || null,
        rules: rules || null,
      }),
    });

    return handleResponse(res, 'Failed to retrieve review items.');
  },

  /**
   * Submit human review resolutions and obtain updated deterministic verdicts from review service.
   */
  async submitReview({ originalExtraction, corrections, packageMetadata, rules }) {
    const res = await fetch(`${API_BASE}/api/review/submit`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        original_extraction: originalExtraction,
        corrections,
        package_metadata: packageMetadata || null,
        rules: rules || null,
      }),
    });

    return handleResponse(res, 'Failed to submit human review.');
  },

  /**
   * Append reviewer resolutions and post-review re-evaluations to an existing ledger inspection.
   */
  async appendReviewToLedger(inspectionId, { corrections, updatedExtraction, newCompliance, provenance }) {
    const res = await fetch(`${API_BASE}/api/ledger/inspections/${encodeURIComponent(inspectionId)}/review`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        corrections,
        updated_extraction: updatedExtraction,
        new_compliance: newCompliance,
        provenance: provenance || null,
      }),
    });

    return handleResponse(res, 'Failed to append review resolution to Evidence Ledger.');
  },

  /**
   * Retrieve structured inspection result report from the presentation layer.
   */
  async getResultReport(inspectionId) {
    const res = await fetch(`${API_BASE}/api/result/${encodeURIComponent(inspectionId)}`);
    return handleResponse(res, `Inspection report for ${inspectionId} not found.`);
  },

  /**
   * Get direct URL for streaming/downloading PDF report.
   */
  getPdfUrl(inspectionId) {
    return `${API_BASE}/api/result/${encodeURIComponent(inspectionId)}/pdf`;
  },
};
