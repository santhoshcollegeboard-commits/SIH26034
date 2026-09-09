"""Comprehensive unit tests for the Deterministic Legal Metrology Rule Engine.

All tests are 100% deterministic and mock-free. Zero LLM/API calls.
"""

import pytest

from backend.app.schemas.compliance import OverallVerdict, RuleStatus
from backend.app.schemas.extraction import ExtractedField, ExtractionResult, SourceRegion
from backend.app.services.rules.engine import DeterministicRuleEngine
from backend.app.services.rules.evaluators import (
    evaluate_consumer_care,
    evaluate_country_of_origin,
    evaluate_manufacturer_details,
    evaluate_manufacturing_date,
    evaluate_mrp_declaration,
    evaluate_product_name,
    evaluate_standard_metric_units,
    evaluate_unit_sale_price,
)


@pytest.fixture
def rule_engine() -> DeterministicRuleEngine:
    return DeterministicRuleEngine()


def _make_field(
    value: str | None,
    status: str = "extracted",
    confidence: float = 0.95,
    region: tuple[int, int, int, int] = (10, 10, 100, 30),
) -> ExtractedField:
    """Helper to build an ExtractedField."""
    return ExtractedField(
        value=value,
        confidence=confidence if value else None,
        source_region=SourceRegion(x=region[0], y=region[1], width=region[2], height=region[3])
        if value
        else None,
        status=status,
    )


def _make_fully_compliant_extraction() -> ExtractionResult:
    """A benchmark fully-compliant packaged commodity label."""
    return ExtractionResult(
        product_name=_make_field("Assam Gold Premium"),
        common_or_generic_name=_make_field("CTC Black Leaf Tea"),
        manufacturer_name=_make_field("Himalayan Highlands Tea Estates Pvt. Ltd."),
        manufacturer_address=_make_field("Plot 42, Tea Park Road, Dibrugarh, Assam - 786001"),
        packer_name=_make_field("PackCheck Agro Products LLP"),
        importer_name=_make_field(None, status="not_found"),
        country_of_origin=_make_field("India"),
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes) | USP: ₹ 0.49 per g"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Toll-Free: 1800-209-8899 | Email: care@assamgoldtea.in"),
    )


# =========================================================================
# 1. Standard Metric Unit Formatting Tests (Rules 11-13 & Second Schedule)
# =========================================================================


@pytest.mark.parametrize("legal_unit", ["1 kg", "5 kg", "500 ml", "1 l", "1 L", "250 g", "10 N", "50 units", "100 pcs"])
def test_legal_metric_units_pass(legal_unit: str):
    """Legal standard metric units must pass Rule 11 verification."""
    extraction = ExtractionResult(net_quantity=_make_field(legal_unit))
    ev = evaluate_standard_metric_units(extraction, {})
    assert ev.status == RuleStatus.PASS, f"Expected '{legal_unit}' to pass, got {ev.status}: {ev.message}"


@pytest.mark.parametrize("bad_unit", ["500 gms", "2 kgs", "1 ltr", "500 mls", "1 cc", "2 kilos", "500 gm", "2 litres"])
def test_prohibited_units_fail(bad_unit: str):
    """Prohibited/deprecated unit abbreviations must fail Rule 11."""
    extraction = ExtractionResult(net_quantity=_make_field(bad_unit))
    ev = evaluate_standard_metric_units(extraction, {})
    assert ev.status == RuleStatus.FAIL, f"Expected '{bad_unit}' to fail, got {ev.status}: {ev.message}"
    assert "prohibited" in ev.message.lower()


def test_bare_numeric_quantity_fails():
    """Bare numbers without unit of measure must fail Rule 11."""
    extraction = ExtractionResult(net_quantity=_make_field("75"))
    ev = evaluate_standard_metric_units(extraction, {})
    assert ev.status == RuleStatus.FAIL
    assert "lacking any statutory unit" in ev.message


# =========================================================================
# 2. Manufacturer / Packer / Importer Validation (Rule 6(1)(b))
# =========================================================================


def test_manufacturer_name_and_address_passes():
    """Name + Address is the complete statutory declaration -> PASS."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("12 Industrial Area, Pune 411018"),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "Manufacturer: Apex Foods Ltd" in ev.message


def test_manufacturer_name_without_address_is_not_verifiable():
    """Name alone without complete address must not falsely PASS -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field(None, status="not_found"),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "complete address was not detected" in ev.message


def test_manufacturer_unreadable_address_is_not_verifiable():
    """Unreadable address must be flagged for inspector review -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("Plot...", status="unreadable"),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE


def test_manufacturer_missing_all_identity_is_not_verifiable():
    """All identity fields absent on this view -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field(None, status="not_found"),
        manufacturer_address=_make_field(None, status="not_found"),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE


def test_clearly_incomplete_address_is_not_verifiable():
    """Single-word or short address like 'Delhi' must yield NOT_VERIFIABLE, not PASS."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("Delhi"),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "incomplete or truncated" in ev.message


def test_truncated_address_with_ellipsis_is_not_verifiable():
    """Address with OCR truncation markers must yield NOT_VERIFIABLE, not PASS."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("Plot No. 44, Industrial Area..."),
    )
    ev = evaluate_manufacturer_details(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "incomplete or truncated" in ev.message


# =========================================================================
# 3. Manufacturing Date Format Tests (Rule 6(1)(d))
# =========================================================================


@pytest.mark.parametrize("valid_date", ["08/2026", "08-2026", "08.2026", "Aug 2026", "August 2026", "08/26", "08.26"])
def test_valid_date_formats_pass(valid_date: str):
    """Recognized date formats including slash, dash, dot, and words must pass."""
    extraction = ExtractionResult(month_year_of_manufacture=_make_field(valid_date))
    ev = evaluate_manufacturing_date(extraction, {})
    assert ev.status == RuleStatus.PASS, f"Expected '{valid_date}' to pass, got {ev.status}"


def test_unreadable_date_is_not_verifiable():
    extraction = ExtractionResult(month_year_of_manufacture=_make_field("08/...", status="unreadable"))
    ev = evaluate_manufacturing_date(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE


# =========================================================================
# 4. Country of Origin Tests (Rule 6(1)(b) Proviso & Rule 6(10))
# =========================================================================


def test_imported_commodity_with_origin_passes():
    """Imported commodity with clear country of origin declaration -> PASS."""
    extraction = ExtractionResult(
        importer_name=_make_field("Global Tech India Pvt Ltd"),
        country_of_origin=_make_field("Vietnam"),
    )
    ev = evaluate_country_of_origin(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "Vietnam" in ev.message


def test_imported_commodity_without_visible_origin_is_not_verifiable():
    """Imported commodity whose origin is not on this panel -> NOT_VERIFIABLE (never FAIL on single image)."""
    extraction = ExtractionResult(
        importer_name=_make_field("Global Tech India Pvt Ltd"),
        country_of_origin=_make_field(None, status="not_found"),
    )
    ev = evaluate_country_of_origin(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "not detected on this image view" in ev.message


def test_domestic_commodity_origin_is_not_applicable():
    """Domestic commodity without importer declaration -> NOT_APPLICABLE for import origin rule."""
    extraction = ExtractionResult(
        manufacturer_name=_make_field("Local Foods Mumbai"),
        importer_name=_make_field(None, status="not_found"),
    )
    ev = evaluate_country_of_origin(extraction, {})
    assert ev.status == RuleStatus.NOT_APPLICABLE


# =========================================================================
# 5. Consumer Care Validation Tests (Rule 6(1)(f))
# =========================================================================


def test_consumer_care_with_phone_passes():
    extraction = ExtractionResult(consumer_care_details=_make_field("Toll-free: 1800-209-8899"))
    ev = evaluate_consumer_care(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "phone/toll-free" in ev.message


def test_consumer_care_with_email_passes():
    extraction = ExtractionResult(consumer_care_details=_make_field("Email us at support@brand.in"))
    ev = evaluate_consumer_care(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "email" in ev.message


def test_consumer_care_keyword_without_contact_is_not_verifiable():
    """Bare marketing text like 'Customer Care' without phone/email -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(consumer_care_details=_make_field("For feedback write to Customer Care Cell"))
    ev = evaluate_consumer_care(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "no legible telephone number" in ev.message


def test_consumer_care_missing_is_not_verifiable():
    extraction = ExtractionResult(consumer_care_details=_make_field(None, status="not_found"))
    ev = evaluate_consumer_care(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE


# =========================================================================
# 6. Unit Sale Price (USP) Tests (Rule 6(1)(h) 2021 Second Amendment)
# =========================================================================


def test_small_package_below_10g_exempt_from_usp():
    """Packages <= 10 g or <= 10 ml are exempt from USP under Third Proviso -> NOT_APPLICABLE."""
    extraction = ExtractionResult(
        net_quantity=_make_field("5 g"),
        mrp=_make_field("₹ 5.00 (Inclusive of all taxes)"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.NOT_APPLICABLE
    assert "<= 10 g / 10 ml" in ev.message


def test_usp_medium_weight_package_passes():
    """Medium weight package (250 g) with USP declared per g / 100g -> PASS."""
    extraction = ExtractionResult(
        net_quantity=_make_field("250 g"),
        mrp=_make_field("₹ 100.00 (Inclusive of all taxes) | ₹ 0.40 per g"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.PASS


def test_usp_large_weight_package_passes():
    """Large weight package (5 kg) with USP declared per kg -> PASS."""
    extraction = ExtractionResult(
        net_quantity=_make_field("5 kg"),
        mrp=_make_field("₹ 1200.00 (Inclusive of all taxes) | ₹ 240.00 per kg"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.PASS


def test_usp_volume_package_passes():
    """Volume package (750 ml) with USP declared per 100 ml -> PASS."""
    extraction = ExtractionResult(
        net_quantity=_make_field("750 ml"),
        mrp=_make_field("₹ 150.00 (Inclusive of all taxes) | ₹ 20.00 / 100 ml"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.PASS


def test_usp_package_sold_by_number_passes():
    """Package sold by number (10 N) with USP declared per piece -> PASS."""
    extraction = ExtractionResult(
        net_quantity=_make_field("10 N"),
        mrp=_make_field("₹ 50.00 (Inclusive of all taxes) | ₹ 5.00 per piece"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.PASS


def test_usp_missing_on_single_image_is_not_verifiable():
    """When USP is required but not visible on this image -> NOT_VERIFIABLE (not FAIL)."""
    extraction = ExtractionResult(
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 150.00 (Inclusive of all taxes)"),
    )
    ev = evaluate_unit_sale_price(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "was not detected on this image panel" in ev.message


# =========================================================================
# 7. Product Generic Identity Tests (Rule 6(1)(a))
# =========================================================================


def test_generic_name_explicitly_present_passes():
    extraction = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Black Tea"),
    )
    ev = evaluate_product_name(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "CTC Black Tea" in ev.message


def test_brand_only_without_generic_name_is_not_verifiable():
    """Brand name without generic identity verification -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field(None, status="not_found"),
    )
    ev = evaluate_product_name(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "generic or common commodity identity could not be verified" in ev.message


def test_brand_only_oreo_without_generic_is_not_verifiable():
    """Brand-only example (e.g. Oreo) without generic identity must yield NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        product_name=_make_field("Oreo"),
        common_or_generic_name=_make_field(None, status="not_found"),
    )
    ev = evaluate_product_name(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "generic or common commodity identity could not be verified" in ev.message


def test_brand_oreo_with_explicit_generic_biscuits_passes():
    """Brand (Oreo) with explicit generic commodity name (Chocolate Sandwich Biscuits) must PASS."""
    extraction = ExtractionResult(
        product_name=_make_field("Oreo"),
        common_or_generic_name=_make_field("Chocolate Sandwich Biscuits"),
    )
    ev = evaluate_product_name(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "Chocolate Sandwich Biscuits" in ev.message


def test_generic_name_identical_to_brand_is_not_verifiable():
    """Extracted generic name identical to brand must not falsely pass -> NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        product_name=_make_field("Oreo"),
        common_or_generic_name=_make_field("Oreo"),
    )
    ev = evaluate_product_name(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "identical to the brand name" in ev.message


# =========================================================================
# 7B. Maximum Retail Price & Tax Disclaimer Tests (Rule 6(1)(e))
# =========================================================================


@pytest.mark.parametrize(
    "valid_mrp",
    [
        "MRP ₹ 150.00 (inclusive of all taxes)",
        "MRP Rs. 50.00 incl. of all taxes",
        "₹ 99.00 (Inclusive of all taxes)",
        "MRP Rs 250 inclusive of taxes",
    ],
)
def test_valid_mrp_with_tax_wording_passes(valid_mrp: str):
    """Valid MRP with tax disclaimer must PASS."""
    extraction = ExtractionResult(
        mrp=_make_field(valid_mrp),
    )
    ev = evaluate_mrp_declaration(extraction, {})
    assert ev.status == RuleStatus.PASS
    assert "complies with statutory formatting" in ev.message


def test_mrp_without_tax_wording_fails():
    """MRP with price amount but missing tax disclaimer must FAIL."""
    extraction = ExtractionResult(
        mrp=_make_field("MRP ₹ 150.00"),
    )
    ev = evaluate_mrp_declaration(extraction, {})
    assert ev.status == RuleStatus.FAIL
    assert "missing the mandatory 'inclusive of all taxes'" in ev.message


@pytest.mark.parametrize(
    "incomplete_mrp,confidence",
    [
        ("MRP ₹ 150 ...", 0.95),
        ("MRP ₹", 0.95),
        ("MRP ₹ 150 (incl.", 0.95),
        ("MRP ₹ 150", 0.4),
    ],
)
def test_mrp_with_incomplete_ocr_evidence_is_not_verifiable(incomplete_mrp: str, confidence: float):
    """MRP present but incomplete or uncertain OCR evidence must yield NOT_VERIFIABLE."""
    extraction = ExtractionResult(
        mrp=_make_field(incomplete_mrp, confidence=confidence),
    )
    ev = evaluate_mrp_declaration(extraction, {})
    assert ev.status == RuleStatus.NOT_VERIFIABLE
    assert "incomplete, truncated, or uncertain" in ev.message


# =========================================================================
# 8. Full End-to-End Engine Verdict Tests
# =========================================================================


@pytest.mark.asyncio
async def test_compliant_benchmark_yields_pass(rule_engine: DeterministicRuleEngine):
    """Fully compliant benchmark with verified generic name, address, and USP passes."""
    extraction = _make_fully_compliant_extraction()
    compliance = await rule_engine.evaluate_compliance({}, extraction)
    assert compliance.overall_verdict == OverallVerdict.PASS
    assert compliance.failed_count == 0
    assert compliance.review_count == 0


@pytest.mark.asyncio
async def test_prohibited_unit_yields_overall_fail(rule_engine: DeterministicRuleEngine):
    """Prohibited unit symbol (e.g. 500 gms) forces overall FAIL."""
    extraction = _make_fully_compliant_extraction()
    extraction.net_quantity = _make_field("500 gms")

    compliance = await rule_engine.evaluate_compliance({}, extraction)
    assert compliance.overall_verdict == OverallVerdict.FAIL
    assert compliance.failed_count >= 1


@pytest.mark.asyncio
async def test_missing_tax_disclaimer_yields_overall_fail(rule_engine: DeterministicRuleEngine):
    """Retail price missing 'inclusive of all taxes' forces overall FAIL."""
    extraction = _make_fully_compliant_extraction()
    extraction.mrp = _make_field("₹ 245.00")  # Missing tax disclaimer

    compliance = await rule_engine.evaluate_compliance({}, extraction)
    assert compliance.overall_verdict == OverallVerdict.FAIL
    assert compliance.failed_count >= 1


@pytest.mark.asyncio
async def test_missing_address_yields_flagged_for_review(rule_engine: DeterministicRuleEngine):
    """Missing address on single panel must flag for review, not pass or fail."""
    extraction = _make_fully_compliant_extraction()
    extraction.manufacturer_address = _make_field(None, status="not_found")

    compliance = await rule_engine.evaluate_compliance({}, extraction)
    assert compliance.overall_verdict == OverallVerdict.FLAGGED_FOR_REVIEW
    assert compliance.review_count >= 1
    assert compliance.failed_count == 0
