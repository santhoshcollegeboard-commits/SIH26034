"""Deterministic evaluator for Rule 6 of the Legal Metrology (Packaged Commodities) Rules, 2011.

Specification: docs/legal/rule_6_mapping.md
Primary Source: Notification G.S.R. 101(E), dated 7th March 2011 (Gazette of India)
Rule Version Identifier: LMR-2011-BASE-R06

Architecture Principle:
- Pure deterministic logic: evaluated solely on extracted observations.
- Never calls external AI, LLMs, or APIs.
- AI extracts; rules decide; humans resolve uncertainty.
- Strict canonical four-state disposition: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE.
"""

import re
from typing import Any, Dict, List, Optional

from backend.app.schemas.compliance import ComplianceVerdict, RuleEvaluation
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

RULE_VERSION: str = "LMR-2011-BASE-R06"
STATUTORY_SOURCE: str = (
    "The Legal Metrology (Packaged Commodities) Rules, 2011 (Notification G.S.R. 101(E))"
)
CONFIDENCE_THRESHOLD: float = 0.70

# Metric units allowed under Legal Metrology Rules (Rule 6(1)(c))
RE_METRIC_UNIT = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(kg|kilograms?|gms?|grams?|g|mg|l|litres?|liters?|ltrs?|ml|millilitres?|milliliters?|kl|m|metres?|meters?|cm|mm|sq\.?\s*m|sq\.?\s*cm|n|numbers?|units?|u|pcs|pieces?)\b",
    re.IGNORECASE,
)

# Explicit non-metric units that constitute statutory violations if un-accompanied
RE_NON_METRIC_UNIT = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*(lbs?|pounds?|oz|ounces?|fl\.?\s*oz|fluid\s*ounces?|feet|ft|inches?|in|yards?|yds?)\b",
    re.IGNORECASE,
)

# Price indicators and currency formats (Rule 6(1)(e))
RE_PRICE_INDICATOR = re.compile(r"(?i)(?:mrp|₹|rs\.?|inr|rupees?)")
RE_PRICE_AMOUNT = re.compile(r"(?:\d+(?:\.\d{1,2})?)")

# Month and Year representations per Explanation I (Rule 6(1)(d))
RE_DATE_WORDS = re.compile(
    r"(?i)\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b.*?\b(?:19\d\d|20\d\d|\d{2})\b"
)
RE_DATE_NUMERALS = re.compile(
    r"\b(?:0?[1-9]|1[0-2])[\/\.-](?:19\d\d|20\d\d|\d{2})\b|\b(?:19\d\d|20\d\d)[\/\.-](?:0?[1-9]|1[0-2])\b"
)

# Consumer care contact identifiers (Rule 6(2))
RE_PHONE = re.compile(r"(?:\+?91|1800|0?\d{2,4})[- ]?\d{2,4}[- ]?\d{3,4}|(?:\+?91|1800|0?\d{2,4})[- ]?\d{6,10}|\b\d{10}\b")
RE_EMAIL = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
RE_ADDRESS_KEYWORDS = re.compile(
    r"(?i)\b(care|executive|helpline|consumer|cell|officer|manager|address|feedback|complaint|pincode|pin|road|street|nagar|floor|post\s*box)\b"
)


def _eval_field_presence(
    field: ExtractedField,
    rule_id: str,
    rule_name: str,
    expected_requirement: str,
    missing_explanation: str,
    unreadable_explanation: str,
    success_prefix: str,
) -> RuleEvaluation:
    """Evaluate standard text presence and confidence for a mandatory declaration."""
    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=unreadable_explanation,
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "not_found" or not field.value or not field.value.strip():
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=missing_explanation,
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    # Status is extracted with non-empty value
    if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=(
                f"{rule_name} was extracted ('{field.value}'), but extraction confidence "
                f"({field.confidence:.2f}) is below reliability threshold ({CONFIDENCE_THRESHOLD}). Review required."
            ),
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=f"{success_prefix}: '{field.value}'.",
        observed_value=field.value,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_manufacturer_name(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(a) — Name of the manufacturer."""
    return _eval_field_presence(
        field=field,
        rule_id="LMR-2011-R06-01A-MFR-NAME",
        rule_name="Manufacturer Name Declaration",
        expected_requirement="Name of the manufacturer must be plainly and conspicuously declared (Rule 6(1)(a)).",
        missing_explanation="Statutory violation under Rule 6(1)(a): Mandatory manufacturer name is missing from the package.",
        unreadable_explanation="Manufacturer name region detected but text is unreadable. Human inspector verification required.",
        success_prefix="Manufacturer name declared",
    )


def eval_manufacturer_address(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(a) — Address of the manufacturer."""
    return _eval_field_presence(
        field=field,
        rule_id="LMR-2011-R06-01A-MFR-ADDR",
        rule_name="Manufacturer Address Declaration",
        expected_requirement="Complete address of the manufacturer must be plainly declared (Rule 6(1)(a)).",
        missing_explanation="Statutory violation under Rule 6(1)(a): Mandatory manufacturer address is missing from the package.",
        unreadable_explanation="Manufacturer address region detected but text is unreadable. Human inspector verification required.",
        success_prefix="Manufacturer address declared",
    )


def eval_product_name(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(b) — Common or generic name of commodity."""
    return _eval_field_presence(
        field=field,
        rule_id="LMR-2011-R06-01B-PROD-NAME",
        rule_name="Common or Generic Commodity Name",
        expected_requirement="Common or generic name of the commodity contained in the package must be declared (Rule 6(1)(b)).",
        missing_explanation="Statutory violation under Rule 6(1)(b): Common or generic commodity name is missing from the package.",
        unreadable_explanation="Product name region detected but text is unreadable. Human inspector verification required.",
        success_prefix="Generic commodity name declared",
    )


def eval_net_quantity(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(c) — Net quantity in standard metric units."""
    rule_id = "LMR-2011-R06-01C-NET-QTY"
    rule_name = "Net Quantity Declaration & Standard Units"
    expected_requirement = (
        "Net quantity must be declared in standard metric units of weight, measure, or count (Rule 6(1)(c))."
    )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="Net quantity region detected but unreadable. Review required to verify declared quantity and unit.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "not_found" or not field.value or not field.value.strip():
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation under Rule 6(1)(c): Mandatory net quantity declaration is missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    text = field.value.strip()

    # Check for forbidden non-metric units declared without metric equivalent
    has_non_metric = bool(RE_NON_METRIC_UNIT.search(text))
    has_metric = bool(RE_METRIC_UNIT.search(text))

    if has_non_metric and not has_metric:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=f"Statutory violation under Rule 6(1)(c): Declared net quantity '{text}' uses non-standard non-metric units.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if not has_metric:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=f"Statutory violation under Rule 6(1)(c): Declared net quantity '{text}' does not specify a recognized standard metric unit (g, kg, ml, l, m, N, etc.).",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"Net quantity '{text}' contains standard metric unit, but extraction confidence ({field.confidence:.2f}) is below threshold ({CONFIDENCE_THRESHOLD}). Review required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=f"Net quantity declared in standard metric unit: '{text}'.",
        observed_value=text,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_mfg_date(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(d) — Month and year of manufacture or pre-packing."""
    rule_id = "LMR-2011-R06-01D-MFG-DATE"
    rule_name = "Month and Year of Manufacture / Pre-packing"
    expected_requirement = (
        "Month and year of manufacture or pre-packing expressed in words, numerals, or both (Rule 6(1)(d), Explanation I)."
    )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="Manufacture/packing date region detected but text is unreadable. Review required to verify date format.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "not_found" or not field.value or not field.value.strip():
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation under Rule 6(1)(d): Month and year of manufacture or pre-packing is missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    text = field.value.strip()
    matches_words = bool(RE_DATE_WORDS.search(text))
    matches_numerals = bool(RE_DATE_NUMERALS.search(text))

    if not (matches_words or matches_numerals):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=f"Statutory violation under Rule 6(1)(d): Declared date '{text}' does not clearly express a valid month and year.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"Date format is valid ('{text}'), but extraction confidence ({field.confidence:.2f}) is below threshold ({CONFIDENCE_THRESHOLD}). Review required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=f"Month and year declared in valid format: '{text}'.",
        observed_value=text,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_mrp(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(1)(e) — Retail sale price (MRP)."""
    rule_id = "LMR-2011-R06-01E-MRP"
    rule_name = "Retail Sale Price (MRP) Declaration"
    expected_requirement = (
        "Maximum Retail Price must be declared with price prefix (MRP / ₹ / Rs.) and numeric amount (Rule 6(1)(e))."
    )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="MRP declaration region detected but text is unreadable. Review required to verify declared price.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "not_found" or not field.value or not field.value.strip():
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation under Rule 6(1)(e): Maximum Retail Price (MRP) declaration is missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    text = field.value.strip()
    has_amount = bool(RE_PRICE_AMOUNT.search(text))
    has_indicator = bool(RE_PRICE_INDICATOR.search(text))

    if not has_amount:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation=f"Statutory violation under Rule 6(1)(e): Declared price text '{text}' lacks a valid numeric amount.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if not has_indicator:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"Numeric amount detected in '{text}', but standard price prefix (MRP / ₹ / Rs.) is ambiguous. Inspector verification required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"MRP declared ('{text}'), but extraction confidence ({field.confidence:.2f}) is below threshold ({CONFIDENCE_THRESHOLD}). Review required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=f"Retail sale price declared: '{text}'.",
        observed_value=text,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_consumer_care(field: ExtractedField) -> RuleEvaluation:
    """Evaluate Rule 6(2) — Consumer complaint contact details."""
    rule_id = "LMR-2011-R06-02-CONSUMER-CARE"
    rule_name = "Consumer Complaint Details"
    expected_requirement = (
        "Name, address, telephone number, and e-mail address (if available) of person/office to be contacted for consumer complaints (Rule 6(2))."
    )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="Consumer care region detected but text is unreadable. Review required to verify contact details.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "not_found" or not field.value or not field.value.strip():
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation under Rule 6(2): Mandatory consumer complaint contact facility is missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    text = field.value.strip()
    has_phone = bool(RE_PHONE.search(text))
    has_email = bool(RE_EMAIL.search(text))
    has_addr_word = bool(RE_ADDRESS_KEYWORDS.search(text))

    if not (has_phone or has_email or has_addr_word):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"Consumer care text ('{text}') does not contain recognizable phone, email, or address keywords. Inspector review required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation=f"Consumer care details declared ('{text}'), but confidence ({field.confidence:.2f}) is low. Review required.",
            observed_value=text,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation=f"Consumer care facility declared: '{text}'.",
        observed_value=text,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_packer(field: ExtractedField, package_metadata: Optional[Dict[str, Any]] = None) -> RuleEvaluation:
    """Evaluate Rule 6(1)(a) — Packer declaration (conditional)."""
    rule_id = "LMR-2011-R06-01A-PACKER"
    rule_name = "Packer Name Declaration (Conditional)"
    expected_requirement = (
        "Where manufacturer is not the packer, name and address of the packer must be declared (Rule 6(1)(a))."
    )
    meta = package_metadata or {}

    if field.status == "extracted" and field.value and field.value.strip():
        if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
            return RuleEvaluation(
                rule_id=rule_id,
                rule_version=RULE_VERSION,
                rule_name=rule_name,
                status=ComplianceVerdict.REVIEW_REQUIRED,
                explanation=f"Packer declared ('{field.value}'), but extraction confidence ({field.confidence:.2f}) is low. Review required.",
                observed_value=field.value,
                expected_requirement=expected_requirement,
                source_region=field.source_region,
            )
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=f"Packer declared: '{field.value}'.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="Packer declaration region detected but text is unreadable. Review required.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    # field is not_found or empty
    if meta.get("is_packed_by_third_party") is True:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation: Package is recorded as third-party packed, but mandatory packer details are missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    # Default under Rule 6(1)(a) Explanation I: manufacturer is presumed to be packer
    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation="Separate packer not declared; manufacturer is presumed to be the packer under Rule 6(1)(a) Explanation I.",
        observed_value=None,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_importer(field: ExtractedField, package_metadata: Optional[Dict[str, Any]] = None) -> RuleEvaluation:
    """Evaluate Rule 6(1)(a) — Importer declaration (conditional)."""
    rule_id = "LMR-2011-R06-01A-IMPORTER"
    rule_name = "Importer Name Declaration (Conditional)"
    expected_requirement = (
        "For imported packages, the name and address of the importer must be declared (Rule 6(1)(a))."
    )
    meta = package_metadata or {}

    if field.status == "extracted" and field.value and field.value.strip():
        if field.confidence is not None and field.confidence < CONFIDENCE_THRESHOLD:
            return RuleEvaluation(
                rule_id=rule_id,
                rule_version=RULE_VERSION,
                rule_name=rule_name,
                status=ComplianceVerdict.REVIEW_REQUIRED,
                explanation=f"Importer declared ('{field.value}'), but extraction confidence ({field.confidence:.2f}) is low. Review required.",
                observed_value=field.value,
                expected_requirement=expected_requirement,
                source_region=field.source_region,
            )
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.PASS,
            explanation=f"Importer declared: '{field.value}'.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.REVIEW_REQUIRED,
            explanation="Importer declaration region detected but text is unreadable. Review required.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    # field is not_found or empty
    if meta.get("is_imported") is True:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_version=RULE_VERSION,
            rule_name=rule_name,
            status=ComplianceVerdict.FAIL,
            explanation="Statutory violation under Rule 6(1)(a): Package is recorded as imported commodity, but importer details are missing.",
            observed_value=field.value,
            expected_requirement=expected_requirement,
            source_region=field.source_region,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_version=RULE_VERSION,
        rule_name=rule_name,
        status=ComplianceVerdict.PASS,
        explanation="Commodity is domestic/unspecified; importer declaration not applicable under Rule 6(1)(a).",
        observed_value=None,
        expected_requirement=expected_requirement,
        source_region=field.source_region,
    )


def eval_dimensions_clause() -> RuleEvaluation:
    """Evaluate Rule 6(1)(f) — Dimensions of individual pieces (unassessable from image)."""
    return RuleEvaluation(
        rule_id="LMR-2011-R06-01F-DIMENSIONS",
        rule_version=RULE_VERSION,
        rule_name="Dimensions of Commodity Pieces (Where Relevant)",
        status=ComplianceVerdict.NOT_ASSESSABLE,
        explanation=(
            "Piece dimensions cannot be assessed: commodity dimensional relevance requires "
            "product category classification not available from optical package image evidence."
        ),
        observed_value=None,
        expected_requirement="Dimensions of piece(s) where size is relevant (Rule 6(1)(f)).",
        source_region=None,
    )


def evaluate_rule_6(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
    include_unassessable: bool = False,
) -> List[RuleEvaluation]:
    """Deterministically evaluate an ExtractionResult against Rule 6 requirements.

    Args:
        extraction: Structured ExtractionResult containing ExtractedField observations.
        package_metadata: Optional dictionary with metadata (e.g. 'is_imported', 'is_packed_by_third_party').
        include_unassessable: Whether to include clauses mapped as NOT_ASSESSABLE in rule_6_mapping.md.

    Returns:
        List of RuleEvaluation records with deterministic statutory reasoning.
    """
    meta = package_metadata or {}

    evaluations: List[RuleEvaluation] = [
        eval_manufacturer_name(extraction.manufacturer_name),
        eval_manufacturer_address(extraction.manufacturer_address),
        eval_packer(extraction.packer_name, meta),
        eval_importer(extraction.importer_name, meta),
        eval_product_name(extraction.product_name),
        eval_net_quantity(extraction.net_quantity),
        eval_mfg_date(extraction.month_year_of_manufacture),
        eval_mrp(extraction.mrp),
        eval_consumer_care(extraction.consumer_care_details),
    ]

    if include_unassessable:
        evaluations.append(eval_dimensions_clause())

    return evaluations


def aggregate_disposition(evaluations: List[RuleEvaluation]) -> ComplianceVerdict:
    """Aggregate individual RuleEvaluations into the canonical overall disposition.

    Aggregation logic (Task 5):
    - Any clear applicable FAIL -> overall FAIL
    - Otherwise unresolved REVIEW_REQUIRED -> overall REVIEW_REQUIRED
    - Otherwise if all evaluations are NOT_ASSESSABLE (or list is empty) -> NOT_ASSESSABLE
    - Otherwise -> PASS
    """
    if not evaluations:
        return ComplianceVerdict.NOT_ASSESSABLE

    statuses = [e.status for e in evaluations]

    if ComplianceVerdict.FAIL in statuses:
        return ComplianceVerdict.FAIL

    if ComplianceVerdict.REVIEW_REQUIRED in statuses:
        return ComplianceVerdict.REVIEW_REQUIRED

    # If all items are NOT_ASSESSABLE, cannot determine compliance
    if all(s == ComplianceVerdict.NOT_ASSESSABLE for s in statuses):
        return ComplianceVerdict.NOT_ASSESSABLE

    return ComplianceVerdict.PASS
