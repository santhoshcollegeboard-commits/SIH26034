/**
 * Centralized missing-data and presentation formatting policy for PackCheck frontend.
 *
 * Strictly enforces:
 * 1. Missing scalar values -> "Not available in recorded evidence"
 * 2. Missing extracted declarations -> Value: "Not available in recorded evidence", Status: "Not recorded"
 * 3. Missing confidence -> "Not available in recorded evidence" (never 0 or 1)
 * 4. Missing source region -> "Not available in recorded evidence" (never estimated coordinates)
 * 5. Missing quality assessment -> "Not available in recorded evidence"
 * 6. Missing rule fields -> "Not available in recorded evidence"
 * 7. Empty review actions -> "No human review actions recorded."
 * 8. Empty collections:
 *    - Evidence -> "No evidence records available."
 *    - Observations -> "No observations recorded."
 *    - Rule evaluations -> "No rule evaluations recorded."
 *    - Review actions -> "No human review actions recorded."
 * 9. Explicitly not-applicable data -> "Not applicable"
 * 10. Canonical dispositions preserved: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE
 *
 * Never renders raw null, undefined, None, blank strings, or N/A.
 */

export const NOT_AVAILABLE = 'Not available in recorded evidence';
export const NOT_RECORDED = 'Not recorded';
export const NOT_APPLICABLE = 'Not applicable';

export const EMPTY_EVIDENCE = 'No evidence records available.';
export const EMPTY_OBSERVATIONS = 'No observations recorded.';
export const EMPTY_RULES = 'No rule evaluations recorded.';
export const EMPTY_REVIEWS = 'No human review actions recorded.';
export const EMPTY_HISTORY = 'No inspections recorded.';

export const MANDATORY_DECLARATIONS = [
  { key: 'product_name', label: 'Product Name' },
  { key: 'manufacturer_name', label: 'Manufacturer Name' },
  { key: 'manufacturer_address', label: 'Manufacturer Address' },
  { key: 'packer_name', label: 'Packer Name' },
  { key: 'importer_name', label: 'Importer Name' },
  { key: 'net_quantity', label: 'Net Quantity' },
  { key: 'mrp', label: 'MRP' },
  { key: 'month_year_of_manufacture', label: 'Manufacturing Date (Month/Year)' },
  { key: 'consumer_care_details', label: 'Consumer Care Details' },
];

export const FIELD_LABELS = MANDATORY_DECLARATIONS.reduce((acc, curr) => {
  acc[curr.key] = curr.label;
  return acc;
}, {});

/**
 * Format any scalar value according to the missing-data policy.
 */
export function formatMissingValue(value, isApplicable = true, fallback = NOT_AVAILABLE) {
  if (!isApplicable) return NOT_APPLICABLE;
  if (value === null || value === undefined) return fallback;

  const s = String(value).trim();
  if (!s || ['none', 'null', 'undefined', 'n/a'].includes(s.toLowerCase())) {
    return fallback;
  }

  if (['not_applicable', 'not applicable', 'n.a.', 'na'].includes(s.toLowerCase())) {
    return NOT_APPLICABLE;
  }

  return s;
}

/**
 * Format an extraction confidence score.
 */
export function formatConfidence(confidence, isApplicable = true) {
  if (!isApplicable) return NOT_APPLICABLE;
  if (confidence === null || confidence === undefined) return NOT_AVAILABLE;

  if (typeof confidence === 'string') {
    const s = confidence.trim();
    if (!s || ['none', 'null', 'undefined', 'n/a'].includes(s.toLowerCase())) {
      return NOT_AVAILABLE;
    }
    if (s === NOT_AVAILABLE || s === NOT_APPLICABLE) return s;
    const parsed = parseFloat(s);
    if (!isNaN(parsed)) {
      return `${(parsed * 100).toFixed(0)}%`;
    }
    return s;
  }

  const val = parseFloat(confidence);
  if (isNaN(val)) return NOT_AVAILABLE;
  return `${(val * 100).toFixed(0)}%`;
}

/**
 * Format bounding box coordinates into string or fallback.
 */
export function formatSourceRegion(sourceRegion, isApplicable = true) {
  if (!isApplicable) return NOT_APPLICABLE;
  if (!sourceRegion) return NOT_AVAILABLE;

  if (typeof sourceRegion === 'string') {
    const s = sourceRegion.trim();
    if (!s || ['none', 'null', 'undefined', 'n/a'].includes(s.toLowerCase())) {
      return NOT_AVAILABLE;
    }
    return s;
  }

  const { x, y, width, height } = sourceRegion;
  if (x === undefined || y === undefined || width === undefined || height === undefined) {
    return NOT_AVAILABLE;
  }

  return `[x:${x}, y:${y}, ${width}×${height}px]`;
}

/**
 * Format quality gate assessment summary.
 */
export function formatQualitySummary(quality) {
  if (!quality) return NOT_AVAILABLE;
  const isAcceptable = quality.is_acceptable;
  const score = quality.overall_score !== undefined ? Number(quality.overall_score).toFixed(2) : null;
  const statusStr = isAcceptable ? 'PASS (Acceptable)' : 'REJECTED (Insufficient)';
  return score !== null ? `${statusStr} — Score: ${score} / 1.00` : statusStr;
}

/**
 * Get CSS theme styling classes/colors for canonical compliance dispositions.
 */
export function getDispositionTheme(disposition) {
  const d = String(disposition || '').toUpperCase();
  switch (d) {
    case 'PASS':
      return {
        badgeClass: 'badge-pass',
        bannerClass: 'banner-pass',
        label: 'PASS',
        color: 'var(--accent-emerald)',
        icon: '✓',
      };
    case 'FAIL':
      return {
        badgeClass: 'badge-fail',
        bannerClass: 'banner-fail',
        label: 'FAIL',
        color: 'var(--accent-red)',
        icon: '✗',
      };
    case 'REVIEW_REQUIRED':
      return {
        badgeClass: 'badge-review',
        bannerClass: 'banner-review',
        label: 'REVIEW REQUIRED',
        color: 'var(--accent-amber)',
        icon: '⚠',
      };
    case 'NOT_ASSESSABLE':
    default:
      return {
        badgeClass: 'badge-not-assessable',
        bannerClass: 'banner-not-assessable',
        label: 'NOT ASSESSABLE',
        color: 'var(--text-muted)',
        icon: '○',
      };
  }
}
