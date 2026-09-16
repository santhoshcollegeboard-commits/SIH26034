"""Deterministic evaluator for Rule 8 of the Legal Metrology (Packaged Commodities) Rules, 2011.

Statutory Reference: Rule 8 — Declaration where to appear
Primary Source: Notification G.S.R. 101(E), dated 7th March 2011 (Gazette of India)
Rule Version Identifier: LMR-2011-BASE-R08

Statutory Mandates:
1. Rule 8(1): Every declaration required to be made under these rules shall appear on the principal display panel.
2. Rule 8(1) Proviso: The area surrounding the quantity declaration shall be free from printed information:
   (a) above and below by a space equal to at least the height of the numeral in the declaration, and
   (b) to the left and right by a space at least twice the height of numeral in the declaration.
3. Rule 8(2): Returnable beverage bottle crown cap retail sale price exceptions.

Legal-Source Discipline:
- Detects provable bounding box overlaps where other text declarations encroach into the
  mandatory net quantity free space zone (FAIL).
- Where no overlapping declaration is detected from OCR, requires human inspector review
  to confirm background artwork, logos, or unextracted graphics are clear (REVIEW_REQUIRED).
- Confirms mandatory declarations are present on the presented display panel image.
"""

from typing import Any, Dict, List, Optional

from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict, RuleEvaluation
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

RULE_VERSION: str = "LMR-2011-BASE-R08"
STATUTORY_SOURCE: str = (
    "The Legal Metrology (Packaged Commodities) Rules, 2011, Rule 8 (Notification G.S.R. 101(E))"
)


def _regions_overlap(r1_x1: int, r1_y1: int, r1_x2: int, r1_y2: int, r2: SourceRegion) -> bool:
    """Check if rectangle [r1_x1, r1_y1, r1_x2, r1_y2] intersects bounding box r2."""
    r2_x1 = r2.x
    r2_y1 = r2.y
    r2_x2 = r2.x + r2.width
    r2_y2 = r2.y + r2.height

    return not (r1_x2 <= r2_x1 or r1_x1 >= r2_x2 or r1_y2 <= r2_y1 or r1_y1 >= r2_y2)


def eval_pdp_location(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> RuleEvaluation:
    """Evaluate Rule 8(1) requirement that declarations appear on the Principal Display Panel."""
    rule_id = "LMR-2011-R08-01-PDP-LOCATION"
    rule_name = "Declaration Appearance on Principal Display Panel (Rule 8(1))"
    meta = package_metadata or {}

    # Check presence of primary mandatory consumer declarations
    has_product = extraction.product_name.status == "extracted" and bool(extraction.product_name.value)
    has_quantity = extraction.net_quantity.status == "extracted" and bool(extraction.net_quantity.value)
    has_mrp = extraction.mrp.status == "extracted" and bool(extraction.mrp.value)

    if not (has_product and has_quantity and has_mrp):
        missing_items = []
        if not has_product:
            missing_items.append("product name")
        if not has_quantity:
            missing_items.append("net quantity")
        if not has_mrp:
            missing_items.append("retail sale price (MRP)")

        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=(
                f"Statutory violation under Rule 8(1): Mandatory declarations ({', '.join(missing_items)}) "
                "do not appear on the captured principal display panel."
            ),
            observed_value=f"Missing: {', '.join(missing_items)}",
            expected_requirement="All mandatory declarations must appear on the principal display panel (Rule 8(1)).",
            source_region=None,
        )

    # If metadata explicitly confirms panel is designated PDP
    if meta.get("is_principal_display_panel") is True:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=(
                "Mandatory declarations (product name, net quantity, and MRP) appear on the verified "
                "principal display panel in accordance with Rule 8(1)."
            ),
            observed_value="Product name, net quantity, and MRP co-located on PDP.",
            expected_requirement="All mandatory declarations must appear on the principal display panel (Rule 8(1)).",
            source_region=extraction.net_quantity.source_region,
        )

    # Otherwise, declarations appear on the presented panel, but panel classification requires human sign-off
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation=(
            "Key mandatory declarations (product name, net quantity, and MRP) appear grouped on the presented "
            "panel; inspector verification required to confirm panel constitutes statutory Principal Display Panel "
            "per Rule 2(h) and Rule 8(1)."
        ),
        observed_value="Product name, net quantity, and MRP present on captured panel.",
        expected_requirement="All mandatory declarations must appear on the principal display panel (Rule 8(1)).",
        source_region=extraction.net_quantity.source_region,
    )


def eval_net_quantity_free_space(
    extraction: ExtractionResult,
) -> RuleEvaluation:
    """Evaluate Rule 8(1) Proviso surrounding free space exclusion zone around net quantity."""
    rule_id = "LMR-2011-R08-01-FREE-SPACE"
    rule_name = "Net Quantity Surrounding Free Space (Rule 8(1) Proviso)"
    expected_req = (
        "Area surrounding quantity declaration must be free from printed information by at least 1x height "
        "vertically and 2x height horizontally (Rule 8(1) Proviso)."
    )

    q_field = extraction.net_quantity
    if q_field.status != "extracted" or not q_field.value or q_field.source_region is None:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.NOT_ASSESSABLE,
            explanation=(
                "Cannot evaluate Rule 8(1) Proviso free space: Net quantity bounding box (SourceRegion) is not available."
            ),
            observed_value=None,
            expected_requirement=expected_req,
            source_region=None,
        )

    q_box = q_field.source_region
    h = q_box.height

    # Calculate statutory exclusion zone coordinates
    ex_x1 = q_box.x - (2 * h)
    ex_y1 = q_box.y - h
    ex_x2 = q_box.x + q_box.width + (2 * h)
    ex_y2 = q_box.y + q_box.height + h

    # Check all other extracted fields for encroachment
    other_fields = [
        ("product_name", extraction.product_name),
        ("manufacturer_name", extraction.manufacturer_name),
        ("manufacturer_address", extraction.manufacturer_address),
        ("packer_name", extraction.packer_name),
        ("importer_name", extraction.importer_name),
        ("mrp", extraction.mrp),
        ("month_year_of_manufacture", extraction.month_year_of_manufacture),
        ("consumer_care_details", extraction.consumer_care_details),
    ]

    for field_name, other_field in other_fields:
        if (
            other_field.status == "extracted"
            and other_field.value
            and other_field.source_region is not None
        ):
            if _regions_overlap(ex_x1, ex_y1, ex_x2, ex_y2, other_field.source_region):
                return RuleEvaluation(
                    rule_id=rule_id,
                    rule_version=RULE_VERSION,
                    rule_name=rule_name,
                    status=ComplianceVerdict.FAIL,
                    explanation=(
                        f"Statutory violation under Rule 8(1) Proviso: Extracted declaration '{field_name}' "
                        f"encroaches into the mandatory free space surrounding net quantity (exclusion zone: "
                        f"{h}px vertically, {2*h}px horizontally)."
                    ),
                    observed_value=f"Encroached by '{field_name}' ({other_field.value})",
                    expected_requirement=expected_req,
                    source_region=other_field.source_region,
                )

    # If no other extracted declaration overlaps, inspector must still verify background artwork/graphics
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation=(
            f"No overlapping text declarations detected in the net quantity exclusion zone ({h}px vertically, "
            f"{2*h}px horizontally). Human inspector review required to verify background artwork/graphics "
            "are clear of printed information under Rule 8(1) Proviso."
        ),
        observed_value=f"Net quantity '{q_field.value}' exclusion zone clear of extracted text.",
        expected_requirement=expected_req,
        source_region=q_box,
    )


def evaluate_rule_8(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> List[RuleEvaluation]:
    """Deterministically evaluate ExtractionResult against Rule 8 requirements.

    Args:
        extraction: Structured ExtractionResult containing ExtractedField observations.
        package_metadata: Optional package metadata.

    Returns:
        List of RuleEvaluation records for Rule 8.
    """
    meta = package_metadata or {}
    return [
        eval_pdp_location(extraction, meta),
        eval_net_quantity_free_space(extraction),
    ]
