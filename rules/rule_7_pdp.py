"""Deterministic evaluator for Rule 7 of the Legal Metrology (Packaged Commodities) Rules, 2011.

Statutory Reference: Rule 7 — Principal display panel-its area, size and letter etc.
Primary Source: Notification G.S.R. 101(E), dated 7th March 2011 (Gazette of India)
Rule Version Identifier: LMR-2011-BASE-R07

Statutory Mandates:
1. Rule 7(1): Packages <= 5 cm³ capacity may bear PDP on card or tape firmly affixed.
2. Rule 7(2) & Table-I: Minimum height of numerals for net quantity (weight/volume):
   - Upto 200 g/ml: 1 mm (2 mm if blown/embossed/molded)
   - Above 200 g/ml upto 500 g/ml: 2 mm (4 mm if blown/embossed/molded)
   - Above 500 g/ml: 4 mm (6 mm if blown/embossed/molded)
3. Rule 7(2) & Table-II: Minimum height of numerals by PDP area (for length/area/count):
   - Upto 100 cm²: 1 mm (2 mm if blown)
   - 100 cm² to 500 cm²: 2 mm (4 mm if blown)
   - 500 cm² to 2500 cm²: 4 mm (6 mm if blown)
   - Above 2500 cm²: 6 mm (6 mm if blown)
4. Rule 7(3): Minimum letter height 1 mm (2 mm blown). Width >= 1/3 height.

Legal-Source Discipline:
- When physical calibration metadata (e.g. 'physical_mm_per_pixel' or measured height)
  is available, numeral height is deterministically validated against Table-I/II (PASS/FAIL).
- When physical calibration scale is absent, 2D digital image pixel counts cannot
  establish physical millimeter heights without calibration; outputs REVIEW_REQUIRED
  with exact statutory minimum requirement for inspector sign-off.
- Missing net quantity produces NOT_ASSESSABLE.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.compliance import ComplianceVerdict, RuleEvaluation
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

RULE_VERSION: str = "LMR-2011-BASE-R07"
STATUTORY_SOURCE: str = (
    "The Legal Metrology (Packaged Commodities) Rules, 2011, Rule 7 (Notification G.S.R. 101(E))"
)

# Regex to parse numeric value and metric unit from net quantity declaration
RE_QUANTITY_PARSE = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kg|kilograms?|gms?|grams?|g|mg|l|litres?|liters?|ltrs?|ml|millilitres?|milliliters?)\b",
    re.IGNORECASE,
)


def _get_table_1_min_height_mm(value_str: str, is_blown_or_embossed: bool = False) -> Tuple[Optional[float], Optional[str]]:
    """Determine statutory Table-I minimum numeral height in mm based on net quantity.

    Returns:
        (min_height_mm, normalized_qty_description) or (None, None) if unparseable.
    """
    match = RE_QUANTITY_PARSE.search(value_str)
    if not match:
        return None, None

    num_val = float(match.group(1))
    unit = match.group(2).lower()

    # Normalize to grams (g) or milliliters (ml)
    if unit in ("kg", "kilogram", "kilograms", "l", "litre", "litres", "liter", "liters", "ltrs"):
        normalized_amount = num_val * 1000.0
    elif unit in ("mg",):
        normalized_amount = num_val / 1000.0
    else:  # g, gms, grams, ml, millilitres, etc.
        normalized_amount = num_val

    # Table-I thresholds
    if normalized_amount <= 200.0:
        min_height = 2.0 if is_blown_or_embossed else 1.0
    elif normalized_amount <= 500.0:
        min_height = 4.0 if is_blown_or_embossed else 2.0
    else:
        min_height = 6.0 if is_blown_or_embossed else 4.0

    qty_desc = f"{num_val:g} {unit}"
    return min_height, qty_desc


def eval_numeral_height_table_1(
    net_quantity: ExtractedField,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> RuleEvaluation:
    """Evaluate Rule 7(2) Table-I minimum numeral height for net quantity."""
    rule_id = "LMR-2011-R07-02-NUMERAL-HEIGHT"
    rule_name = "Minimum Height of Numerals in Declaration (Table-I)"
    meta = package_metadata or {}
    is_blown = bool(meta.get("is_blown_or_embossed", False))

    if net_quantity.status == "not_found" or not net_quantity.value:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.NOT_ASSESSABLE,
            explanation=(
                "Cannot evaluate Rule 7(2) Table-I numeral height: Net quantity declaration is missing."
            ),
            observed_value=None,
            expected_requirement="Minimum numeral height per Table-I based on net quantity (Rule 7(2)).",
            source_region=None,
        )

    if net_quantity.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=(
                "Net quantity declaration is unreadable or obscured; physical inspector verification "
                "required to check numeral height against Rule 7(2) Table-I."
            ),
            observed_value=None,
            expected_requirement="Minimum numeral height per Table-I (Rule 7(2)).",
            source_region=net_quantity.source_region,
        )

    min_height_mm, qty_desc = _get_table_1_min_height_mm(net_quantity.value, is_blown)
    if min_height_mm is None:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=(
                f"Net quantity '{net_quantity.value}' is non-standard or count-based; "
                "inspector review required under Table-I / Table-II to determine applicable numeral height."
            ),
            observed_value=net_quantity.value,
            expected_requirement="Standard net weight/volume for Table-I evaluation (Rule 7(2)).",
            source_region=net_quantity.source_region,
        )

    expected_req = (
        f"Minimum {min_height_mm:.0f} mm numeral height per Rule 7(2) Table-I for {qty_desc} "
        f"({'blown/embossed' if is_blown else 'normal case'})."
    )

    # 1. Deterministic evaluation if physical scale/calibration is provided in metadata
    measured_height_mm = meta.get("measured_numeral_height_mm")
    mm_per_pixel = meta.get("physical_mm_per_pixel")

    if measured_height_mm is not None:
        actual_height_mm = float(measured_height_mm)
    elif mm_per_pixel is not None and net_quantity.source_region is not None:
        # Estimate numeral height from bounding box height * calibration scale
        actual_height_mm = float(net_quantity.source_region.height) * float(mm_per_pixel)
    else:
        actual_height_mm = None

    if actual_height_mm is not None:
        if actual_height_mm >= min_height_mm:
            return RuleEvaluation(
                rule_id=rule_id,
                rule_version=RULE_VERSION,
                rule_name=rule_name,
                status=ComplianceVerdict.PASS,
                explanation=(
                    f"Measured numeral height ({actual_height_mm:.2f} mm) satisfies Rule 7(2) Table-I "
                    f"minimum requirement ({min_height_mm:.0f} mm) for net quantity of {qty_desc}."
                ),
                observed_value=f"{actual_height_mm:.2f} mm (net qty: {net_quantity.value})",
                expected_requirement=expected_req,
                source_region=net_quantity.source_region,
            )
        else:
            return RuleEvaluation(
                rule_id=rule_id,
                rule_version=RULE_VERSION,
                rule_name=rule_name,
                status=ComplianceVerdict.FAIL,
                explanation=(
                    f"Statutory violation under Rule 7(2) Table-I: Measured numeral height "
                    f"({actual_height_mm:.2f} mm) is less than the mandatory minimum ({min_height_mm:.0f} mm) "
                    f"for net quantity of {qty_desc}."
                ),
                observed_value=f"{actual_height_mm:.2f} mm (net qty: {net_quantity.value})",
                expected_requirement=expected_req,
                source_region=net_quantity.source_region,
            )

    # 2. Without physical calibration metadata, 2D pixel height cannot safely determine physical mm
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation=(
            f"Statutory threshold under Rule 7(2) Table-I for net quantity '{qty_desc}' is minimum "
            f"{min_height_mm:.0f} mm numeral height. Physical calibration scale not provided in image metadata; "
            f"inspector review required to measure print height on package."
        ),
        observed_value=net_quantity.value,
        expected_requirement=expected_req,
        source_region=net_quantity.source_region,
    )


def eval_pdp_area_and_exemption(
    package_metadata: Optional[Dict[str, Any]] = None,
) -> RuleEvaluation:
    """Evaluate Rule 7(1) small package exemption and Rule 7(2) Table-II area threshold."""
    rule_id = "LMR-2011-R07-01-PDP-AREA"
    rule_name = "Principal Display Panel Area & Dimensions (Rule 7)"
    meta = package_metadata or {}

    capacity_cm3 = meta.get("capacity_cubic_cm")
    pdp_area_cm2 = meta.get("pdp_area_sq_cm")

    if capacity_cm3 is not None and float(capacity_cm3) <= 5.0:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=(
                f"Package capacity ({capacity_cm3} cm³) is 5 cm³ or less; eligible for card or tape "
                "PDP placement under Rule 7(1)."
            ),
            observed_value=f"{capacity_cm3} cm³",
            expected_requirement="Capacity <= 5 cm³ qualifies for Rule 7(1) card/tape PDP.",
            source_region=None,
        )

    if pdp_area_cm2 is not None:
        area = float(pdp_area_cm2)
        if area <= 100.0:
            min_h = 1.0
        elif area <= 500.0:
            min_h = 2.0
        elif area <= 2500.0:
            min_h = 4.0
        else:
            min_h = 6.0

        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=(
                f"Principal display panel area ({area:.1f} cm²) recorded; Table-II baseline minimum "
                f"numeral height is {min_h:.0f} mm."
            ),
            observed_value=f"{area:.1f} cm²",
            expected_requirement="Principal display panel area determination under Rule 7(2) Table-II.",
            source_region=None,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation=(
            "Principal display panel physical dimensions and area require physical measurement or "
            "packaging specification metadata to verify Rule 7(2) Table-II area thresholds."
        ),
        observed_value=None,
        expected_requirement="Principal display panel area determination under Rule 7(2) Table-II.",
        source_region=None,
    )


def evaluate_rule_7(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> List[RuleEvaluation]:
    """Deterministically evaluate ExtractionResult against Rule 7 requirements.

    Args:
        extraction: Structured ExtractionResult containing ExtractedField observations.
        package_metadata: Optional package metadata (e.g. 'physical_mm_per_pixel', 'capacity_cubic_cm').

    Returns:
        List of RuleEvaluation records for Rule 7.
    """
    meta = package_metadata or {}
    return [
        eval_numeral_height_table_1(extraction.net_quantity, meta),
        eval_pdp_area_and_exemption(meta),
    ]
