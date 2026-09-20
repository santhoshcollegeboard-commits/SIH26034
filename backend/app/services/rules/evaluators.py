"""Deterministic statutory rule evaluators for Legal Metrology compliance.

Regulatory Basis:
- The Legal Metrology Act, 2009 (Act No. 1 of 2010), Sections 18, 36, 52
- The Legal Metrology (Packaged Commodities) Rules, 2011 (GSR 202(E))
- The Legal Metrology (Packaged Commodities) Amendment Rules, 2017 (GSR 629(E))
- The Legal Metrology (Packaged Commodities) (Second Amendment) Rules, 2021 (GSR 779(E), effective 1 Dec 2022)
- Ministry of Consumer Affairs, Food and Public Distribution, Government of India
- Rules 6, 9, 11, 12, 13 and Second Schedule
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from backend.app.schemas.compliance import RuleEvaluation, RuleSeverity, RuleStatus
from backend.app.schemas.extraction import ExtractedField, ExtractionResult, SourceRegion


# --- Regex Patterns for Metric Units and Declarations ---

# Standard approved metric units under Legal Metrology Rules (Rules 11-13 & Second Schedule)
LEGAL_METRIC_UNITS_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?)\s*(?:kg\b|g\b|mg\b|l\b|L\b|ml\b|mL\b|m\b|cm\b|mm\b|N\b|U\b|units?\b|pcs?\b|pieces?\b|nos?\b|numbers?\b)"
)

# Prohibited / Non-standard unit abbreviations explicitly deprecated or prohibited by LM rules
# Note: uses strict word boundaries (\b) to avoid false-matching legal units (e.g., '1 kg', '500 ml')
PROHIBITED_UNITS_PATTERN = re.compile(
    r"\b(?:\d+(?:\.\d+)?)\s*(?:gms\b|gm\b|kilos\b|kilo\b|kgs\b|ltrs?\b|litres?\b|liters?\b|lts\b|mls\b|cc\b)",
    re.IGNORECASE,
)

# Bare number without unit (e.g., "75", "500", "Net Weight: 100")
BARE_NUMBER_PATTERN = re.compile(
    r"^\s*(?:net\s*(?:weight|wt|qty|quantity)?\s*:?\s*)?(\d+(?:\.\d+)?)\s*$",
    re.IGNORECASE,
)

# Tax-inclusive disclaimer variants: "inclusive of all taxes", "incl. of all taxes", "incl of taxes"
TAX_INCLUSIVE_PATTERN = re.compile(
    r"(?:incl(?:usive)?\.?\s*(?:of)?\s*(?:all\s*)?taxes)",
    re.IGNORECASE,
)

# Currency prefixes: ₹, Rs, Rs., INR
CURRENCY_PREFIX_PATTERN = re.compile(r"(?:₹|rs\.?|inr)\s*\d+", re.IGNORECASE)

# Date of manufacture / packing patterns (supports 08/2026, 08-2026, 08.2026, Aug 2026, 08/26, 08.26)
DATE_PATTERN = re.compile(
    r"\b(?:0?[1-9]|1[0-2])[\/\-\.\s](?:20\d{2}|\d{2})\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,\.\/\-]+(?:20\d{2}|\d{2})\b",
    re.IGNORECASE,
)

# Consumer care contact patterns (phone number, email, or physical address details)
CONTACT_PHONE_PATTERN = re.compile(
    r"(?:\+?91[\-\s]?)?(?:1800[\-\s]?\d{3}[\-\s]?\d{3,4}|\d{3,5}[\-\s]?\d{6,8}|\b\d{10}\b)"
)
CONTACT_EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
CONTACT_ADDRESS_PATTERN = re.compile(
    r"(?:p\.?o\.?\s*box|plot\s*(?:no\.?|#)?\s*\d+|road|street|lane|nagar|sector|industrial\s*area|pin\s*(?:code)?\s*[:\-]?\s*\d{6}|\b\d{6}\b)",
    re.IGNORECASE,
)


def _get_field_text(field: Optional[ExtractedField]) -> Optional[str]:
    """Safely extract stripped text if field is extracted and non-empty."""
    if not field or not field.value or field.status != "extracted":
        return None
    val = field.value.strip()
    return val if val else None


def _get_region(field: Optional[ExtractedField]) -> Optional[SourceRegion]:
    """Extract source bounding region from field if available."""
    return field.source_region if field else None


def _check_conflict(
    field: Optional[ExtractedField],
    rule_id: str,
    rule_ref: str,
    name: str,
    expected_condition: str,
    severity: RuleSeverity = RuleSeverity.CRITICAL,
) -> Optional[RuleEvaluation]:
    """If field has conflict status, return a NOT_VERIFIABLE RuleEvaluation."""
    if field and field.status == "conflict":
        details = field.conflict_details or field.value or "Conflicting declarations across panels"
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=severity,
            message=f"Conflicting declarations detected across package panels: {details}; inspector review required.",
            extracted_value=field.value,
            expected_condition=expected_condition,
            source_region=_get_region(field),
        )
    return None


def evaluate_product_name(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(a) — Common / Generic Product Identity.

    Statutory citation:
        Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The common or generic names of the commodity contained in the package
        and in case of packages with more than one product, the name and number
        or quantity of each product shall be mentioned on the package."
    """
    rule_id = "LM-PC-06-1-A"
    rule_ref = "Rule 6(1)(a), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Product Name / Generic Identity Declaration"

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        getattr(result, "common_or_generic_name", None),
        rule_id,
        rule_ref,
        name,
        "Common or generic commodity identity clearly declared.",
    ) or _check_conflict(
        result.product_name,
        rule_id,
        rule_ref,
        name,
        "Common or generic commodity identity clearly declared.",
    )
    if conflict_ev:
        return conflict_ev

    # Prefer explicitly extracted generic / common name
    generic_val = _get_field_text(getattr(result, "common_or_generic_name", None))
    brand_val = _get_field_text(result.product_name)

    # 1. Unreadable text region
    if (result.product_name and result.product_name.status == "unreadable") or (
        getattr(result, "common_or_generic_name", None)
        and result.common_or_generic_name.status == "unreadable"
    ):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Product name text region is present on the label but is unreadable; requires human verification.",
            extracted_value=brand_val or generic_val,
            expected_condition="Generic or common name of the commodity must be legible on the principal display panel.",
            source_region=_get_region(result.product_name),
        )

    # 2. Both absent
    if not generic_val and not brand_val:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Product name was not detected on this package view; inspect other packaging faces.",
            extracted_value=None,
            expected_condition="Generic or common name of the commodity must be clearly declared.",
            source_region=None,
        )

    # 3. Explicit generic / common name is verified
    # Must be non-empty and if brand is also present, cannot be a mere duplicate of the brand/trademark
    if generic_val and len(generic_val) >= 2:
        if brand_val and generic_val.strip().lower() == brand_val.strip().lower():
            return RuleEvaluation(
                rule_id=rule_id,
                rule_reference=rule_ref,
                rule_name=name,
                status=RuleStatus.NOT_VERIFIABLE,
                severity=RuleSeverity.MAJOR,
                message=f"Extracted generic identity ('{generic_val}') is identical to the brand name ('{brand_val}'); common/generic identity requires human verification.",
                extracted_value=generic_val,
                expected_condition="Common or generic commodity identity distinct from trademark brand under Rule 6(1)(a).",
                source_region=_get_region(getattr(result, "common_or_generic_name", None))
                or _get_region(result.product_name),
            )
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.CRITICAL,
            message=f"Common/generic commodity identity declared: '{generic_val}'.",
            extracted_value=generic_val,
            expected_condition="Common or generic commodity identity clearly declared.",
            source_region=_get_region(getattr(result, "common_or_generic_name", None))
            or _get_region(result.product_name),
        )

    # 4. Only brand / trade name detected without confirmed generic identity
    # Does not make arbitrary semantic guesses; flags for review
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.MAJOR,
        message=f"Brand/trade name detected ('{brand_val}'), but generic or common commodity identity could not be verified from this panel; human verification required.",
        extracted_value=brand_val,
        expected_condition="Common or generic commodity identity (Rule 6(1)(a)) distinct from trademark brand.",
        source_region=_get_region(result.product_name),
    )


def evaluate_manufacturer_details(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(b) — Manufacturer / Packer / Importer Details.

    Statutory citation:
        Rule 6(1)(b), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The name and complete address of the manufacturer, or where the manufacturer
        is not the packer, the name and complete address of the manufacturer and packer,
        or in case of imported packages, the name and complete address of the importer."
    """
    rule_id = "LM-PC-06-1-B"
    rule_ref = "Rule 6(1)(b), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Manufacturer / Packer / Importer Declaration"

    # 0. Check multi-panel conflicts
    for f in [
        result.manufacturer_name,
        result.manufacturer_address,
        result.packer_name,
        result.importer_name,
    ]:
        conflict_ev = _check_conflict(
            f,
            rule_id,
            rule_ref,
            name,
            "Name and complete address of manufacturer/packer/importer must be declared.",
        )
        if conflict_ev:
            return conflict_ev

    mfg_name = _get_field_text(result.manufacturer_name)
    mfg_addr = _get_field_text(result.manufacturer_address)
    packer_name = _get_field_text(result.packer_name)
    importer_name = _get_field_text(result.importer_name)

    # Check unreadable conditions
    if any(
        f.status == "unreadable"
        for f in [
            result.manufacturer_name,
            result.manufacturer_address,
            result.packer_name,
            result.importer_name,
        ]
        if f is not None
    ):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Manufacturer/packer/importer text region is unreadable; requires human verification.",
            extracted_value=mfg_name or packer_name or importer_name,
            expected_condition="Name and complete address of manufacturer, packer, or importer must be legible.",
            source_region=_get_region(result.manufacturer_name)
            or _get_region(result.packer_name),
        )

    # 1. Full compliance: Name AND address present
    has_identity = bool(mfg_name or packer_name or importer_name)
    has_address = bool(mfg_addr)

    # Incomplete address evidence detection (without external geocoding)
    # A complete address under Rule 6(1)(b) must specify more than a bare single token
    # or truncated fragment. Incomplete evidence must yield NOT_VERIFIABLE.
    is_incomplete_address = False
    if has_address:
        addr_clean = mfg_addr.strip()
        if (
            len(addr_clean) < 10
            or " " not in addr_clean
            or "..." in addr_clean
            or "…" in addr_clean
            or addr_clean.endswith("..")
            or (
                result.manufacturer_address
                and result.manufacturer_address.confidence is not None
                and result.manufacturer_address.confidence < 0.5
            )
        ):
            is_incomplete_address = True

    if has_identity and has_address and not is_incomplete_address:
        parts = []
        if mfg_name:
            parts.append(f"Manufacturer: {mfg_name}")
        if packer_name:
            parts.append(f"Packer: {packer_name}")
        if importer_name:
            parts.append(f"Importer: {importer_name}")
        parts.append(f"Address: {mfg_addr}")
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.CRITICAL,
            message="; ".join(parts) + ".",
            extracted_value=mfg_name or packer_name or importer_name,
            expected_condition="Name and complete address of manufacturer and/or packer must be declared.",
            source_region=_get_region(result.manufacturer_name)
            or _get_region(result.manufacturer_address),
        )

    # 2. Name is declared, but address is missing or incomplete on this image view
    if has_identity and (not has_address or is_incomplete_address):
        declared_identity = mfg_name or packer_name or importer_name
        msg = (
            f"Identity declared ('{declared_identity}'), but complete address evidence is incomplete or truncated ('{mfg_addr}'); requires human verification."
            if is_incomplete_address
            else f"Identity declared ('{declared_identity}'), but complete address was not detected on this image panel; inspect rear/side panels."
        )
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.MAJOR,
            message=msg,
            extracted_value=declared_identity,
            expected_condition="Both name and complete address must be mentioned on the package.",
            source_region=_get_region(result.manufacturer_name)
            or _get_region(result.packer_name)
            or _get_region(result.manufacturer_address),
        )

    # 3. Neither manufacturer, packer, nor importer found
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.CRITICAL,
        message="Manufacturer, packer, or importer details not detected on this packaging view.",
        extracted_value=None,
        expected_condition="Name and complete address of manufacturer/packer/importer must be declared.",
        source_region=None,
    )


def evaluate_country_of_origin(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(b) Proviso & Rule 6(10) — Country of Origin for Imports.

    Statutory citation:
        Rule 6(1)(b) Proviso and Rule 6(10), Legal Metrology (Packaged Commodities) Rules, 2011:
        "Provided that for imported packages, the name of the country of origin or
        manufacture or assembly shall be mentioned on the package."
    """
    rule_id = "LM-PC-06-1-B-ORIGIN"
    rule_ref = "Rule 6(1)(b) Proviso & Rule 6(10), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Country of Origin (Imported Commodities)"

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        getattr(result, "country_of_origin", None),
        rule_id,
        rule_ref,
        name,
        "Country of origin must be stated for imported commodities.",
    ) or _check_conflict(
        result.importer_name,
        rule_id,
        rule_ref,
        name,
        "Country of origin must be stated for imported commodities.",
    )
    if conflict_ev:
        return conflict_ev

    importer_name = _get_field_text(result.importer_name)
    origin_field_val = _get_field_text(getattr(result, "country_of_origin", None))
    mfg_addr = _get_field_text(result.manufacturer_address) or ""

    is_imported = (
        bool(importer_name)
        or metadata.get("is_imported", False)
        or "imported" in mfg_addr.lower()
    )

    # Search for explicit origin in dedicated field, address, or metadata
    origin_candidates = [
        origin_field_val,
        metadata.get("country_of_origin"),
    ]
    origin_declared = None
    for cand in origin_candidates:
        if cand and len(cand.strip()) >= 2:
            origin_declared = cand.strip()
            break

    if not origin_declared:
        for kw in ["country of origin", "made in", "product of", "imported from"]:
            if kw in mfg_addr.lower():
                origin_declared = mfg_addr
                break

    # Case 1: Package is known/inferred to be imported
    if is_imported:
        if origin_declared:
            return RuleEvaluation(
                rule_id=rule_id,
                rule_reference=rule_ref,
                rule_name=name,
                status=RuleStatus.PASS,
                severity=RuleSeverity.CRITICAL,
                message=f"Country of origin declared for imported commodity: '{origin_declared}'.",
                extracted_value=origin_declared,
                expected_condition="Country of origin must be stated for imported commodities.",
                source_region=_get_region(getattr(result, "country_of_origin", None))
                or _get_region(result.importer_name),
            )
        # Imported status known, but origin not visible on this image -> NOT_VERIFIABLE (never FAIL on single image)
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Package declares an importer or is imported, but Country of Origin was not detected on this image view; inspect other panels.",
            extracted_value=importer_name,
            expected_condition="Every imported package must clearly state the country of origin or manufacture.",
            source_region=_get_region(result.importer_name),
        )

    # Case 2: Origin declared on domestic goods (many domestic goods state 'India')
    if origin_declared:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.MINOR,
            message=f"Country of origin declared: '{origin_declared}'.",
            extracted_value=origin_declared,
            expected_condition="Country of origin declared on package.",
            source_region=_get_region(getattr(result, "country_of_origin", None)),
        )

    # Case 3: Domestic commodity with no importer
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_APPLICABLE,
        severity=RuleSeverity.MINOR,
        message="Package does not declare an importer on this panel; Country of Origin rule applies specifically to imported goods.",
        extracted_value=None,
        expected_condition="Country of origin is mandatory for imported packaged commodities.",
        source_region=None,
    )


def evaluate_net_quantity_presence(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(c) — Net Quantity Declaration Presence.

    Statutory citation:
        Rule 6(1)(c), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The net quantity, in terms of the standard unit of weight or measure,
        of the commodity contained in the package or where the commodity is sold
        by number, the number of the commodity contained in the package shall be mentioned."
    """
    rule_id = "LM-PC-06-1-C"
    rule_ref = "Rule 6(1)(c), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Net Quantity Declaration Presence"

    field = result.net_quantity

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        field,
        rule_id,
        rule_ref,
        name,
        "Net quantity declaration is mandatory on all packaged commodities.",
    )
    if conflict_ev:
        return conflict_ev

    val = _get_field_text(field)

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Net quantity region detected on label but is unreadable; human review required.",
            extracted_value=field.value,
            expected_condition="Net quantity must be legible on the principal display panel.",
            source_region=_get_region(field),
        )

    if not val or field.status == "not_found":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Net quantity declaration was not found on this packaging view.",
            extracted_value=None,
            expected_condition="Net quantity declaration is mandatory on all packaged commodities.",
            source_region=None,
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.PASS,
        severity=RuleSeverity.CRITICAL,
        message=f"Net quantity declared: '{val}'.",
        extracted_value=val,
        expected_condition="Net quantity must be declared on the package.",
        source_region=_get_region(field),
    )


def evaluate_standard_metric_units(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rules 11, 12, 13 & Second Schedule — Metric Units & Symbol Formatting.

    Statutory citation:
        Rules 11, 12, 13 and Second Schedule, Legal Metrology (Packaged Commodities) Rules, 2011:
        "No packaging shall use non-standard units or prohibited abbreviations.
        Only standard metric units (e.g. g, kg, ml, l, cm, m, N) shall be used."
    """
    rule_id = "LM-PC-11-UNITS"
    rule_ref = "Rules 11, 12, 13 and Second Schedule, Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Standard Units & Quantity Formatting"

    field = result.net_quantity

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        field,
        rule_id,
        rule_ref,
        name,
        "Net quantity must declare standard SI units (e.g., 'g', 'kg', 'ml', 'l').",
    )
    if conflict_ev:
        return conflict_ev

    val = _get_field_text(field)

    if not val or field.status in ("not_found", "unreadable"):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Cannot verify unit format because net quantity is not readable on this panel.",
            extracted_value=None,
            expected_condition="Net quantity must declare standard SI units (e.g., 'g', 'kg', 'ml', 'l').",
            source_region=None,
        )

    # Check 1: Bare number without any unit (e.g. "75" or "Net Weight: 75")
    if BARE_NUMBER_PATTERN.match(val):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.CRITICAL,
            message=f"Net quantity '{val}' is a bare numeric quantity lacking any statutory unit of measure (e.g. 'g', 'kg', 'ml').",
            extracted_value=val,
            expected_condition="Numeric value must be accompanied by standard legal unit (e.g. '75 g').",
            source_region=_get_region(field),
        )

    # Check 2: Deprecated / prohibited abbreviations (e.g. 'gms', 'gm', 'kilos', 'kgs', 'ltr', 'litres', 'mls', 'cc')
    prohibited_match = PROHIBITED_UNITS_PATTERN.search(val)
    if prohibited_match:
        bad_token = prohibited_match.group(0)
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.MAJOR,
            message=f"Net quantity '{val}' uses prohibited/non-standard unit symbol '{bad_token}'. Legal Metrology requires approved SI symbols ('g', 'kg', 'ml', 'l').",
            extracted_value=val,
            expected_condition="Standard SI metric units without plural abbreviations (e.g. 'g' instead of 'gms').",
            source_region=_get_region(field),
        )

    # Check 3: Standard approved metric unit presence
    if LEGAL_METRIC_UNITS_PATTERN.search(val):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.CRITICAL,
            message=f"Net quantity '{val}' complies with Legal Metrology standard metric unit formatting.",
            extracted_value=val,
            expected_condition="Standard legal metric unit of weight/volume/number properly formatted.",
            source_region=_get_region(field),
        )

    # If unit cannot be confidently parsed from text
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.MAJOR,
        message=f"Net quantity format '{val}' requires manual verification to confirm legal compliance.",
        extracted_value=val,
        expected_condition="Standard unit of weight, measure, or count under Second Schedule.",
        source_region=_get_region(field),
    )


def evaluate_manufacturing_date(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(d) — Month and Year of Manufacture / Packaging.

    Statutory citation:
        Rule 6(1)(d), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The month and year in which the commodity is manufactured or pre-packed
        or imported shall be mentioned on the package."
    """
    rule_id = "LM-PC-06-1-D"
    rule_ref = "Rule 6(1)(d), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Month & Year of Manufacture / Packaging"

    field = result.month_year_of_manufacture

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        field,
        rule_id,
        rule_ref,
        name,
        "Mandatory declaration of manufacturing or packaging month and year.",
        severity=RuleSeverity.MAJOR,
    )
    if conflict_ev:
        return conflict_ev

    val = _get_field_text(field)

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.MAJOR,
            message="Manufacturing/packaging date text region is unreadable on this image; human review required.",
            extracted_value=field.value,
            expected_condition="Month and year of manufacture or packing must be clearly legible.",
            source_region=_get_region(field),
        )

    if not val or field.status == "not_found":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.MAJOR,
            message="Month and year of manufacture was not detected on this packaging view.",
            extracted_value=None,
            expected_condition="Mandatory declaration of manufacturing or packaging month and year.",
            source_region=None,
        )

    if DATE_PATTERN.search(val):
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.MAJOR,
            message=f"Manufacturing / packaging date properly declared: '{val}'.",
            extracted_value=val,
            expected_condition="Month and year in standard date format (e.g., MM/YYYY, MM.YYYY, Month YYYY).",
            source_region=_get_region(field),
        )

    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.MINOR,
        message=f"Manufacturing date text '{val}' requires human verification to confirm date format.",
        extracted_value=val,
        expected_condition="Month and year of manufacture or pre-packing.",
        source_region=_get_region(field),
    )


def evaluate_mrp_declaration(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(e) — Maximum Retail Price & Tax Disclaimer.

    Statutory citation:
        Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The retail sale price of the package shall be clearly indicated in the
        form: 'Maximum or Max. Retail Price Rs / ₹ ... inclusive of all taxes' or
        'MRP Rs / ₹ ... incl. of all taxes'."
    """
    rule_id = "LM-PC-06-1-E"
    rule_ref = "Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Maximum Retail Price (MRP) & Tax Disclaimer"

    field = result.mrp

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        field,
        rule_id,
        rule_ref,
        name,
        "Maximum Retail Price inclusive of all taxes must be declared.",
    )
    if conflict_ev:
        return conflict_ev

    val = _get_field_text(field)

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="MRP text region detected but is unreadable; human inspection required.",
            extracted_value=field.value,
            expected_condition="MRP must be clearly legible and state 'inclusive of all taxes'.",
            source_region=_get_region(field),
        )

    if not val or field.status == "not_found":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="MRP declaration was not detected on this packaging view.",
            extracted_value=None,
            expected_condition="Maximum Retail Price inclusive of all taxes must be declared.",
            source_region=None,
        )

    has_tax_wording = bool(TAX_INCLUSIVE_PATTERN.search(val))
    has_digits = bool(re.search(r"\d", val))
    is_truncated = bool(
        "..." in val
        or "…" in val
        or val.strip().endswith("..")
        or (
            not has_tax_wording
            and re.search(r"\b(?:incl|inclusive|tax|taxes|of|\()\s*[\.\-]?\s*$", val, re.IGNORECASE)
        )
    )
    is_low_confidence = bool(field.confidence is not None and field.confidence < 0.5)

    # Incomplete OCR evidence: price is cut off, has truncation markers, lacks digits, or has low confidence
    if not has_digits or is_truncated or is_low_confidence:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message=f"MRP text evidence is incomplete, truncated, or uncertain ('{val}'); requires human verification.",
            extracted_value=val,
            expected_condition="Maximum Retail Price inclusive of all taxes must be legibly and completely declared.",
            source_region=_get_region(field),
        )

    # If price is declared but completely lacks tax disclaimer
    if not has_tax_wording:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.FAIL,
            severity=RuleSeverity.CRITICAL,
            message=f"Retail price '{val}' is missing the mandatory 'inclusive of all taxes' or 'incl. of all taxes' disclaimer required by Rule 6(1)(e).",
            extracted_value=val,
            expected_condition="MRP declaration must state 'inclusive of all taxes' or 'incl. of all taxes'.",
            source_region=_get_region(field),
        )

    # Valid compliance with MRP and tax disclaimer
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.PASS,
        severity=RuleSeverity.CRITICAL,
        message=f"MRP complies with statutory formatting and tax disclaimer: '{val}'.",
        extracted_value=val,
        expected_condition="MRP declared in rupees and includes 'inclusive of all taxes'.",
        source_region=_get_region(field),
    )


def evaluate_consumer_care(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(f) — Consumer Care Contact Details.

    Statutory citation:
        Rule 6(1)(f), Legal Metrology (Packaged Commodities) Rules, 2011:
        "The name, address, telephone number, and e-mail address of the person
        who can be or the office which can be contacted, in case of consumer
        complaints shall be mentioned on the package."
    """
    rule_id = "LM-PC-06-1-F"
    rule_ref = "Rule 6(1)(f), Legal Metrology (Packaged Commodities) Rules, 2011"
    name = "Consumer Care Grievance Redressal Details"

    field = result.consumer_care_details

    # 0. Check multi-panel conflicts
    conflict_ev = _check_conflict(
        field,
        rule_id,
        rule_ref,
        name,
        "Mandatory contact info (toll-free/phone/email/address) for consumer grievances.",
    )
    if conflict_ev:
        return conflict_ev

    val = _get_field_text(field)

    if field.status == "unreadable":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Consumer care details region detected but is unreadable; requires human verification.",
            extracted_value=field.value,
            expected_condition="Consumer helpline telephone and email address must be legible.",
            source_region=_get_region(field),
        )

    if not val or field.status == "not_found":
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.CRITICAL,
            message="Consumer care details not detected on this panel; verify side/rear packaging panels.",
            extracted_value=None,
            expected_condition="Mandatory contact info (toll-free/phone/email/address) for consumer grievances.",
            source_region=None,
        )

    has_phone = bool(CONTACT_PHONE_PATTERN.search(val))
    has_email = bool(CONTACT_EMAIL_PATTERN.search(val))
    has_address = bool(CONTACT_ADDRESS_PATTERN.search(val))

    # Statutory compliance requires genuine contact channels (phone or email or physical cell address)
    if has_phone or has_email or (has_address and len(val) >= 15):
        contact_types = []
        if has_phone:
            contact_types.append("phone/toll-free")
        if has_email:
            contact_types.append("email")
        if has_address:
            contact_types.append("address")
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.CRITICAL,
            message=f"Consumer care contact details verified ({', '.join(contact_types)}): '{val}'.",
            extracted_value=val,
            expected_condition="Consumer care phone/toll-free or email address declared on package.",
            source_region=_get_region(field),
        )

    # Keywords present without any actual phone number or email address
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.MAJOR,
        message=f"Consumer care text region detected ('{val}'), but no legible telephone number, email address, or grievance cell address was found; human verification required.",
        extracted_value=val,
        expected_condition="Legible telephone number, email address, or postal address for consumer complaints.",
        source_region=_get_region(field),
    )


def evaluate_unit_sale_price(
    result: ExtractionResult, metadata: Dict[str, Any]
) -> RuleEvaluation:
    """Evaluate Rule 6(1)(h) (2021 Second Amendment, effective 1 Dec 2022) — Unit Sale Price.

    Statutory citation:
        Rule 6(1)(h), Legal Metrology (Packaged Commodities) (Second Amendment) Rules, 2021:
        "The unit sale price in rupees, rounded off to the nearest two decimal places,
        shall be declared on every pre-packaged commodity in the following manner, namely:—
        (i) per gram where net quantity is less than one kilogram and per kilogram where net quantity is more than one kilogram;
        (ii) per milliliter where net quantity is less than one liter and per liter where net quantity is more than one liter;
        (iii) per number or unit if sold by number;
        Provided that for packages containing commodity less than or equal to one kilogram or one liter,
        the unit sale price may be declared per 100 gram or 100 milliliter;
        Provided also that it is not required to declare unit sale price for packages containing
        commodity less than or equal to ten gram or ten milliliter."
    """
    rule_id = "LM-PC-06-1-H-USP"
    rule_ref = "Rule 6(1)(h), Legal Metrology (Packaged Commodities) (Second Amendment) Rules, 2021"
    name = "Unit Sale Price (USP) Declaration"

    # 0. Check multi-panel conflicts on net_quantity
    conflict_ev = _check_conflict(
        result.net_quantity,
        rule_id,
        rule_ref,
        name,
        "USP is mandatory on pre-packaged commodities (> 10 g / 10 ml).",
        severity=RuleSeverity.MAJOR,
    )
    if conflict_ev:
        return conflict_ev

    net_qty_str = _get_field_text(result.net_quantity)

    # Check if net quantity is available
    if not net_qty_str:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_VERIFIABLE,
            severity=RuleSeverity.MINOR,
            message="Cannot determine Unit Sale Price requirement because net quantity was not extracted.",
            extracted_value=None,
            expected_condition="USP is mandatory on pre-packaged commodities (> 10 g / 10 ml).",
            source_region=None,
        )

    # Parse numeric quantity to check for <= 10 g or <= 10 ml exemption (Third Proviso)
    match_g = re.search(r"(\d+(?:\.\d+)?)\s*g\b", net_qty_str, re.IGNORECASE)
    match_ml = re.search(r"(\d+(?:\.\d+)?)\s*ml\b", net_qty_str, re.IGNORECASE)
    match_mg = re.search(r"(\d+(?:\.\d+)?)\s*mg\b", net_qty_str, re.IGNORECASE)

    is_exempt_small = False
    if match_g and float(match_g.group(1)) <= 10.0:
        is_exempt_small = True
    elif match_ml and float(match_ml.group(1)) <= 10.0:
        is_exempt_small = True
    elif match_mg:
        is_exempt_small = True

    if is_exempt_small:
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.NOT_APPLICABLE,
            severity=RuleSeverity.MINOR,
            message=f"Net quantity '{net_qty_str}' is <= 10 g / 10 ml; exempt from Unit Sale Price declaration under Third Proviso to Rule 6(1)(h).",
            extracted_value=net_qty_str,
            expected_condition="Commodities <= 10 g or <= 10 ml are exempt from USP.",
            source_region=_get_region(result.net_quantity),
        )

    # Search for USP in MRP field, metadata, or other packaging text
    mrp_text = _get_field_text(result.mrp) or ""
    metadata_usp = metadata.get("unit_sale_price") or metadata.get("unit_sale_price_declared")

    usp_pattern = re.compile(
        r"(?:unit\s*sale\s*price|usp|₹?\s*\d+(?:\.\d+)?\s*(?:per|\/)\s*(?:100\s*g|g|kg|100\s*ml|ml|l|piece|pcs|unit|N|U|number|metre|meter))\b",
        re.IGNORECASE,
    )
    mrp_usp_match = usp_pattern.search(mrp_text)

    if mrp_usp_match or metadata_usp:
        matched_str = mrp_usp_match.group(0) if mrp_usp_match else str(metadata_usp)
        return RuleEvaluation(
            rule_id=rule_id,
            rule_reference=rule_ref,
            rule_name=name,
            status=RuleStatus.PASS,
            severity=RuleSeverity.MAJOR,
            message=f"Unit Sale Price verified: '{matched_str}'.",
            extracted_value=matched_str,
            expected_condition="Unit Sale Price in rupees per g/100g, kg, ml/100ml, L, or number under Rule 6(1)(h).",
            source_region=_get_region(result.mrp),
        )

    # USP is required, but was not detected on this single visual image view
    # In accordance with single-image uncertainty, do not declare statutory FAIL; flag for review
    return RuleEvaluation(
        rule_id=rule_id,
        rule_reference=rule_ref,
        rule_name=name,
        status=RuleStatus.NOT_VERIFIABLE,
        severity=RuleSeverity.MAJOR,
        message=f"Unit Sale Price (USP) was not detected on this image panel for net quantity '{net_qty_str}'; inspect other packaging faces (e.g. barcode / side panel).",
        extracted_value=net_qty_str,
        expected_condition="Unit Sale Price per unit (e.g. ₹ X.XX per g or kg) must be declared on packages exceeding 10 g / 10 ml.",
        source_region=_get_region(result.net_quantity),
    )
