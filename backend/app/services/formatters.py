"""Centralized missing-data and display policy formatters.

Enforces a single missing-data rendering policy across the Result API and PDF Report:
1. Missing / null scalar values -> "Not available in recorded evidence"
2. Missing extracted declaration -> Value: "Not available in recorded evidence", Status: "Not recorded"
3. Missing confidence -> "Not available in recorded evidence" (never assumed 0 or 1)
4. Missing source region -> "Not available in recorded evidence" (never estimated coordinates)
5. Missing quality assessment -> "Not available in recorded evidence"
6. Missing rule fields -> "Not available in recorded evidence"
7. Missing human review -> "No human review actions recorded."
8. Empty collections:
   - Evidence -> "No evidence records available."
   - Observations -> "No observations recorded."
   - Rule evaluations -> "No rule evaluations recorded."
   - Review actions -> "No human review actions recorded."
9. Explicitly not-applicable data -> "Not applicable"
10. Preserves canonical statuses (PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE).
"""

from typing import Any, List, Optional

# Canonical display constants
NOT_AVAILABLE_MESSAGE = "Not available in recorded evidence"
NOT_APPLICABLE_MESSAGE = "Not applicable"
NOT_RECORDED_MESSAGE = "Not recorded"

EMPTY_EVIDENCE_MESSAGE = "No evidence records available."
EMPTY_OBSERVATIONS_MESSAGE = "No observations recorded."
EMPTY_RULE_EVALUATIONS_MESSAGE = "No rule evaluations recorded."
EMPTY_REVIEW_ACTIONS_MESSAGE = "No human review actions recorded."

# Expected standard packaging declaration fields
MANDATORY_DECLARATION_FIELDS: List[str] = [
    "product_name",
    "manufacturer_name",
    "manufacturer_address",
    "packer_name",
    "importer_name",
    "net_quantity",
    "mrp",
    "month_year_of_manufacture",
    "consumer_care_details",
]


def format_missing_value(
    value: Optional[Any],
    is_applicable: bool = True,
    fallback: str = NOT_AVAILABLE_MESSAGE,
) -> str:
    """Format a scalar value according to the missing-data policy.

    - Returns 'Not applicable' if is_applicable is False or value explicitly indicates N/A.
    - Returns 'Not available in recorded evidence' if value is None, empty, or blank string.
    - Never returns raw None, null, undefined, blank strings, or N/A.
    - Preserves canonical compliance verdicts (PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE).
    """
    if not is_applicable:
        return NOT_APPLICABLE_MESSAGE

    if value is None:
        return fallback

    s = str(value).strip()
    if not s or s.lower() in ("none", "null", "undefined", "n/a"):
        return fallback

    if s.lower() in ("not_applicable", "not applicable", "n.a.", "na"):
        return NOT_APPLICABLE_MESSAGE

    return s


def format_confidence(confidence: Optional[Any], is_applicable: bool = True) -> str:
    """Format an extraction confidence score.

    - If unavailable, returns 'Not available in recorded evidence'.
    - Never converts missing confidence to 0, 1, or an assumed value.
    """
    if not is_applicable:
        return NOT_APPLICABLE_MESSAGE

    if confidence is None:
        return NOT_AVAILABLE_MESSAGE

    if isinstance(confidence, str):
        s = confidence.strip()
        if not s or s.lower() in ("none", "null", "undefined", "n/a"):
            return NOT_AVAILABLE_MESSAGE
        if s.lower() in ("not_applicable", "not applicable"):
            return NOT_APPLICABLE_MESSAGE
        if s == NOT_AVAILABLE_MESSAGE:
            return NOT_AVAILABLE_MESSAGE
        try:
            val = float(s)
            return f"{val:.2f}"
        except ValueError:
            return s

    try:
        val = float(confidence)
        return f"{val:.2f}"
    except (ValueError, TypeError):
        return NOT_AVAILABLE_MESSAGE


def format_source_region(source_region: Optional[Any], is_applicable: bool = True) -> str:
    """Format source bounding box region.

    - If unavailable, returns 'Not available in recorded evidence'.
    - Never creates or estimates coordinates.
    """
    if not is_applicable:
        return NOT_APPLICABLE_MESSAGE

    if source_region is None:
        return NOT_AVAILABLE_MESSAGE

    if isinstance(source_region, str):
        s = source_region.strip()
        if not s or s.lower() in ("none", "null", "undefined", "n/a"):
            return NOT_AVAILABLE_MESSAGE
        if s.lower() in ("not_applicable", "not applicable"):
            return NOT_APPLICABLE_MESSAGE
        return s

    if isinstance(source_region, dict):
        if not source_region:
            return NOT_AVAILABLE_MESSAGE
        x = source_region.get("x")
        y = source_region.get("y")
        w = source_region.get("width")
        h = source_region.get("height")
        if x is None or y is None or w is None or h is None:
            return NOT_AVAILABLE_MESSAGE
        return f"[{x}, {y}, {w}x{h}]"

    if hasattr(source_region, "x") and hasattr(source_region, "y"):
        return f"[{source_region.x}, {source_region.y}, {source_region.width}x{source_region.height}]"

    s = str(source_region).strip()
    return s if s else NOT_AVAILABLE_MESSAGE


def format_quality_summary(quality: Optional[Any]) -> str:
    """Format quality gate assessment summary."""
    if quality is None:
        return NOT_AVAILABLE_MESSAGE

    # QualityAssessment instance
    if hasattr(quality, "overall_score") and hasattr(quality, "is_acceptable"):
        status_str = "PASS (Acceptable)" if quality.is_acceptable else "REJECTED (Insufficient)"
        return f"{status_str} — Score: {quality.overall_score:.2f} / 1.00"

    if isinstance(quality, dict):
        if not quality or "overall_score" not in quality:
            return NOT_AVAILABLE_MESSAGE
        is_acc = quality.get("is_acceptable", False)
        status_str = "PASS (Acceptable)" if is_acc else "REJECTED (Insufficient)"
        return f"{status_str} — Score: {float(quality['overall_score']):.2f} / 1.00"

    if isinstance(quality, str):
        s = quality.strip()
        if not s or s.lower() in ("none", "null", "undefined", "n/a"):
            return NOT_AVAILABLE_MESSAGE
        return s

    return NOT_AVAILABLE_MESSAGE


def clean_presentation_dict(data: Any) -> Any:
    """Recursively sanitize presentation dictionaries to ensure no raw null/None/undefined/N/A."""
    if isinstance(data, dict):
        cleaned = {}
        for k, v in data.items():
            if v is None:
                if k == "evidence":
                    cleaned[k] = NOT_AVAILABLE_MESSAGE
                elif k == "quality":
                    cleaned[k] = NOT_AVAILABLE_MESSAGE
                elif k in ("source_region", "source_region_before", "source_region_after"):
                    cleaned[k] = NOT_AVAILABLE_MESSAGE
                elif k in ("confidence", "original_confidence"):
                    cleaned[k] = NOT_AVAILABLE_MESSAGE
                elif k == "review_actions":
                    cleaned[k] = []
                elif k == "observations":
                    cleaned[k] = []
                elif k == "rule_evaluations":
                    cleaned[k] = []
                else:
                    cleaned[k] = NOT_AVAILABLE_MESSAGE
            elif isinstance(v, str):
                cleaned[k] = format_missing_value(v)
            elif isinstance(v, (dict, list)):
                cleaned[k] = clean_presentation_dict(v)
            else:
                cleaned[k] = v
        return cleaned
    elif isinstance(data, list):
        return [clean_presentation_dict(item) for item in data]
    elif data is None:
        return NOT_AVAILABLE_MESSAGE
    elif isinstance(data, str):
        return format_missing_value(data)
    return data
