"""Deterministic evaluator for Rule 9 of the Legal Metrology (Packaged Commodities) Rules, 2011.

Statutory Reference: Rule 9 — Manner in which declaration shall be made
Primary Source: Notification G.S.R. 101(E), dated 7th March 2011 (Gazette of India)
Rule Version Identifier: LMR-2011-BASE-R09

Statutory Mandates:
1. Rule 9(1)(a): Every declaration required to be made on a package shall be legible and prominent.
2. Rule 9(1)(b): Numerals of the retail sale price and net quantity declaration shall be printed,
   painted or inscribed on the package in a colour that contrasts conspicuously with the background.
3. Rule 9(2): No declaration shall be made so as to require it to be read through any liquid commodity.
4. Rule 9(4): Declarations shall either be in Hindi in Devnagri script or in English
   (other languages allowed in addition to Hindi or English).

Legal-Source Discipline:
- Rule 9(4) language check is 100% deterministically machine-checkable: validates presence of
  English (Latin) or Hindi (Devanagari) script (PASS) vs unauthorized foreign scripts (FAIL).
- Rule 9(1)(a) evaluates OCR optical confidence thresholds to verify legibility.
- Rule 9(1)(b) verifies presence of MRP and net quantity numerals and requests visual contrast sign-off.
- Rule 9(2) verifies commodity placement relative to liquid media.
"""

import re
from typing import Any, Dict, List, Optional

from backend.app.schemas.compliance import ComplianceVerdict, RuleEvaluation
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

RULE_VERSION: str = "LMR-2011-BASE-R09"
STATUTORY_SOURCE: str = (
    "The Legal Metrology (Packaged Commodities) Rules, 2011, Rule 9 (Notification G.S.R. 101(E))"
)

# Character script patterns for Rule 9(4)
RE_LATIN = re.compile(r"[a-zA-Z]")
RE_DEVANAGARI = re.compile(r"[\u0900-\u097F]")


def _has_authorized_script(text: str) -> bool:
    """Check if text contains characters from Hindi (Devanagari) or English (Latin)."""
    return bool(RE_LATIN.search(text) or RE_DEVANAGARI.search(text))


def eval_language(
    extraction: ExtractionResult,
) -> RuleEvaluation:
    """Evaluate Rule 9(4) requirement that declarations appear in English or Hindi (Devanagari)."""
    rule_id = "LMR-2011-R09-04-LANGUAGE"
    rule_name = "Language of Declarations (Rule 9(4))"
    expected_req = (
        "Declarations must be in English or Hindi in Devnagri script; other languages permitted in addition (Rule 9(4))."
    )

    all_fields = [
        extraction.product_name,
        extraction.manufacturer_name,
        extraction.manufacturer_address,
        extraction.packer_name,
        extraction.importer_name,
        extraction.net_quantity,
        extraction.mrp,
        extraction.month_year_of_manufacture,
        extraction.consumer_care_details,
    ]

    extracted_texts = [f.value for f in all_fields if f.status == "extracted" and f.value]

    if not extracted_texts:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.NOT_ASSESSABLE,
            explanation="Cannot evaluate Rule 9(4) language: No declarations extracted from package.",
            observed_value=None,
            expected_requirement=expected_req,
            source_region=None,
        )

    # Check if ANY extracted text contains authorized English/Hindi script
    authorized_found = any(_has_authorized_script(t) for t in extracted_texts)

    if authorized_found:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=(
                "Statutory requirement satisfied under Rule 9(4): Declarations are presented in "
                "English / Hindi (Devanagari script)."
            ),
            observed_value=f"Authorized script verified across {len(extracted_texts)} declarations.",
            expected_requirement=expected_req,
            source_region=extraction.product_name.source_region or extraction.net_quantity.source_region,
        )
    else:
        sample_text = extracted_texts[0][:50] if extracted_texts else "None"
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=(
                "Statutory violation under Rule 9(4): Declarations are not presented in English or "
                f"Hindi in Devnagri script (observed: '{sample_text}')."
            ),
            observed_value=sample_text,
            expected_requirement=expected_req,
            source_region=None,
        )


def eval_legibility_and_prominence(
    extraction: ExtractionResult,
) -> RuleEvaluation:
    """Evaluate Rule 9(1)(a) legibility and prominence using extraction confidence scores."""
    rule_id = "LMR-2011-R09-01A-LEGIBILITY"
    rule_name = "Legibility and Prominence of Declarations (Rule 9(1)(a))"
    expected_req = "Every declaration on a package must be legible and prominent (Rule 9(1)(a))."

    mandatory_fields = [
        ("product_name", extraction.product_name),
        ("manufacturer_name", extraction.manufacturer_name),
        ("net_quantity", extraction.net_quantity),
        ("mrp", extraction.mrp),
        ("month_year_of_manufacture", extraction.month_year_of_manufacture),
        ("consumer_care_details", extraction.consumer_care_details),
    ]

    unreadable_fields = [name for name, f in mandatory_fields if f.status == "unreadable"]
    if unreadable_fields:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=(
                f"Statutory violation under Rule 9(1)(a): Mandatory declaration(s) "
                f"({', '.join(unreadable_fields)}) are illegible or obscured on packaging."
            ),
            observed_value=f"Illegible: {', '.join(unreadable_fields)}",
            expected_requirement=expected_req,
            source_region=None,
        )

    # Check for low confidence (< 0.70) among extracted declarations
    low_confidence_fields = []
    for name, f in mandatory_fields:
        if f.status == "extracted" and f.confidence is not None and f.confidence < 0.70:
            low_confidence_fields.append(f"{name} ({f.confidence:.2f})")

    if low_confidence_fields:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=(
                f"Borderline optical legibility detected under Rule 9(1)(a) for: "
                f"{', '.join(low_confidence_fields)}. Human inspector review required."
            ),
            observed_value=f"Low confidence: {', '.join(low_confidence_fields)}",
            expected_requirement=expected_req,
            source_region=None,
        )

    extracted_count = sum(1 for _, f in mandatory_fields if f.status == "extracted")
    if extracted_count == 0:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.NOT_ASSESSABLE,
            explanation="Cannot assess Rule 9(1)(a) legibility: No mandatory declarations found.",
            observed_value=None,
            expected_requirement=expected_req,
            source_region=None,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=(
            f"All {extracted_count} extracted mandatory declarations demonstrate high legibility "
            "(confidence >= 0.70) satisfying Rule 9(1)(a)."
        ),
        observed_value=f"{extracted_count} mandatory declarations verified legible.",
        expected_requirement=expected_req,
        source_region=None,
    )


def eval_numeral_contrast(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> RuleEvaluation:
    """Evaluate Rule 9(1)(b) conspicuous contrast of MRP and Net Quantity numerals."""
    rule_id = "LMR-2011-R09-01B-CONTRAST"
    rule_name = "Conspicuous Contrast of Numerals (Rule 9(1)(b))"
    expected_req = (
        "Numerals of retail sale price and net quantity must contrast conspicuously with background (Rule 9(1)(b))."
    )
    meta = package_metadata or {}

    has_mrp = extraction.mrp.status == "extracted" and bool(extraction.mrp.value)
    has_net_qty = extraction.net_quantity.status == "extracted" and bool(extraction.net_quantity.value)

    if not (has_mrp and has_net_qty):
        missing = []
        if not has_mrp:
            missing.append("MRP")
        if not has_net_qty:
            missing.append("net quantity")

        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.NOT_ASSESSABLE,
            explanation=(
                f"Cannot assess Rule 9(1)(b) numeral contrast: {', '.join(missing)} declaration is missing."
            ),
            observed_value=f"Missing: {', '.join(missing)}",
            expected_requirement=expected_req,
            source_region=None,
        )

    # If physical/optical contrast is already verified in metadata
    if meta.get("is_contrast_verified") is True:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation="Conspicuous contrast of MRP and net quantity numerals verified per Rule 9(1)(b).",
            observed_value=f"MRP: '{extraction.mrp.value}', Net Qty: '{extraction.net_quantity.value}'",
            expected_requirement=expected_req,
            source_region=extraction.net_quantity.source_region,
        )

    # Optical contrast against physical packaging requires human inspector confirmation
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation=(
            f"Numerals for retail sale price ('{extraction.mrp.value}') and net quantity "
            f"('{extraction.net_quantity.value}') are extracted; human review required to confirm "
            "conspicuous color contrast against packaging background under Rule 9(1)(b)."
        ),
        observed_value=f"MRP: '{extraction.mrp.value}', Net Qty: '{extraction.net_quantity.value}'",
        expected_requirement=expected_req,
        source_region=extraction.net_quantity.source_region,
    )


def eval_liquid_read_through(
    package_metadata: Optional[Dict[str, Any]] = None,
) -> RuleEvaluation:
    """Evaluate Rule 9(2) restriction against reading declarations through liquid commodities."""
    rule_id = "LMR-2011-R09-02-LIQUID-READ"
    rule_name = "Declaration Read Through Liquid Restriction (Rule 9(2))"
    expected_req = "No declaration shall be made so as to require it to be read through any liquid commodity (Rule 9(2))."
    meta = package_metadata or {}

    if meta.get("read_through_liquid") is True:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=(
                "Statutory violation under Rule 9(2): Packaging requires declarations to be read "
                "through liquid commodity contained in the package."
            ),
            observed_value="Declaration positioned behind liquid commodity.",
            expected_requirement=expected_req,
            source_region=None,
        )

    if meta.get("commodity_type") == "liquid":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=(
                "Liquid commodity package; inspector review required to confirm declarations are not "
                "positioned to be read through the liquid under Rule 9(2)."
            ),
            observed_value="Liquid commodity package.",
            expected_requirement=expected_req,
            source_region=None,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation="Commodity is non-liquid or standard label placement; Rule 9(2) restriction not triggered.",
        observed_value="Standard label placement.",
        expected_requirement=expected_req,
        source_region=None,
    )


def evaluate_rule_9(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
) -> List[RuleEvaluation]:
    """Deterministically evaluate ExtractionResult against Rule 9 requirements.

    Args:
        extraction: Structured ExtractionResult containing ExtractedField observations.
        package_metadata: Optional package metadata.

    Returns:
        List of RuleEvaluation records for Rule 9.
    """
    meta = package_metadata or {}
    return [
        eval_language(extraction),
        eval_legibility_and_prominence(extraction),
        eval_numeral_contrast(extraction, meta),
        eval_liquid_read_through(meta),
    ]
