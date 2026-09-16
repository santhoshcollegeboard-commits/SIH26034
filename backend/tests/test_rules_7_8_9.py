"""Comprehensive test suite for Rules 7, 8, and 9 of the Legal Metrology (Packaged Commodities) Rules, 2011.

Covers:
1. Rule 7: Principal Display Panel Area & Numeral Height (Table-I & Table-II)
2. Rule 8: Location of Declarations & Surrounding Free Space (Rule 8(1) Proviso)
3. Rule 9: Manner of Declarations (Language, Legibility, Contrast, Liquid Read-Through)
4. Integration & Multi-Rule Aggregation with DeterministicRuleEngine
"""

# pyrefly: ignore [missing-import]
import pytest

from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.services.rule_engine_service import DeterministicRuleEngine
from rules.rule_7_pdp import evaluate_rule_7
from rules.rule_8_placement import evaluate_rule_8
from rules.rule_9_manner import evaluate_rule_9


# --------------------------------------------------------------------------
# Test Extraction Fixtures
# --------------------------------------------------------------------------

def _make_sample_extraction(
    product_name: str = "Premium Atta",
    net_quantity: str = "5 kg",
    mrp: str = "₹250.00",
    q_bbox: SourceRegion = SourceRegion(x=200, y=200, width=100, height=20),
    mrp_bbox: SourceRegion = SourceRegion(x=200, y=300, width=100, height=20),
    prod_bbox: SourceRegion = SourceRegion(x=200, y=100, width=200, height=30),
) -> ExtractionResult:
    """Helper to build standard extraction observations for Rules 7-9."""
    return ExtractionResult(
        product_name=ExtractedField(
            value=product_name,
            confidence=0.95,
            source_region=prod_bbox,
            status="extracted" if product_name else "not_found",
        ),
        manufacturer_name=ExtractedField(
            value="Heritage Millers Pvt Ltd",
            confidence=0.92,
            source_region=SourceRegion(x=50, y=500, width=200, height=25),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Sector 12, Industrial Area, Ahmedabad, Gujarat - 380015",
            confidence=0.90,
            source_region=SourceRegion(x=50, y=530, width=350, height=25),
            status="extracted",
        ),
        packer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        importer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        net_quantity=ExtractedField(
            value=net_quantity,
            confidence=0.98,
            source_region=q_bbox,
            status="extracted" if net_quantity else "not_found",
        ),
        mrp=ExtractedField(
            value=mrp,
            confidence=0.95,
            source_region=mrp_bbox,
            status="extracted" if mrp else "not_found",
        ),
        month_year_of_manufacture=ExtractedField(
            value="09/2026",
            confidence=0.92,
            source_region=SourceRegion(x=50, y=600, width=120, height=20),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="care@heritagemillers.com 1800 123 4567",
            confidence=0.94,
            source_region=SourceRegion(x=50, y=630, width=300, height=25),
            status="extracted",
        ),
    )


# --------------------------------------------------------------------------
# 1. Rule 7 Tests (Principal Display Panel & Numeral Height)
# --------------------------------------------------------------------------

def test_rule_7_table_1_numeral_height_pass_with_calibration():
    """Numeral height >= statutory Table-I requirement yields PASS when calibration is provided."""
    # Net quantity 5 kg (> 500g): Table-I normal requirement is 4 mm
    extraction = _make_sample_extraction(net_quantity="5 kg")
    evaluations = evaluate_rule_7(
        extraction,
        package_metadata={"measured_numeral_height_mm": 5.0},
    )
    height_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-02-NUMERAL-HEIGHT")
    assert height_eval.status == ComplianceVerdict.PASS
    assert "satisfies Rule 7(2) Table-I" in height_eval.explanation


def test_rule_7_table_1_numeral_height_fail_with_calibration():
    """Numeral height < statutory Table-I requirement yields FAIL when calibration is provided."""
    # Net quantity 5 kg (> 500g): Table-I normal requirement is 4 mm; observed is only 2.5 mm
    extraction = _make_sample_extraction(net_quantity="5 kg")
    evaluations = evaluate_rule_7(
        extraction,
        package_metadata={"measured_numeral_height_mm": 2.5},
    )
    height_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-02-NUMERAL-HEIGHT")
    assert height_eval.status == ComplianceVerdict.FAIL
    assert "Statutory violation under Rule 7(2) Table-I" in height_eval.explanation


def test_rule_7_table_1_without_calibration_yields_review_required():
    """Without physical scale calibration, engine preserves uncertainty via REVIEW_REQUIRED."""
    extraction = _make_sample_extraction(net_quantity="500 g")
    evaluations = evaluate_rule_7(extraction, package_metadata={})
    height_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-02-NUMERAL-HEIGHT")
    assert height_eval.status == ComplianceVerdict.REVIEW_REQUIRED
    assert "Physical calibration scale not provided" in height_eval.explanation
    assert "Minimum 2 mm" in height_eval.expected_requirement


def test_rule_7_blown_container_higher_threshold():
    """Containers with blown/embossed numerals use higher Table-I thresholds."""
    # For <= 200g: normal is 1mm, blown/embossed is 2mm
    extraction = _make_sample_extraction(net_quantity="100 g")
    evaluations = evaluate_rule_7(
        extraction,
        package_metadata={"is_blown_or_embossed": True, "measured_numeral_height_mm": 1.5},
    )
    height_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-02-NUMERAL-HEIGHT")
    # 1.5mm < 2mm required for blown container -> FAIL
    assert height_eval.status == ComplianceVerdict.FAIL
    assert "minimum (2 mm)" in height_eval.explanation


def test_rule_7_missing_net_quantity_not_assessable():
    """Missing net quantity declaration renders Rule 7 numeral height NOT_ASSESSABLE."""
    extraction = _make_sample_extraction(net_quantity="")
    evaluations = evaluate_rule_7(extraction)
    height_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-02-NUMERAL-HEIGHT")
    assert height_eval.status == ComplianceVerdict.NOT_ASSESSABLE


def test_rule_7_small_capacity_exemption():
    """Package with capacity <= 5 cm³ qualifies for Rule 7(1) card/tape PDP exemption."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_7(
        extraction,
        package_metadata={"capacity_cubic_cm": 4.5},
    )
    area_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R07-01-PDP-AREA")
    assert area_eval.status == ComplianceVerdict.PASS
    assert "Rule 7(1)" in area_eval.explanation


# --------------------------------------------------------------------------
# 2. Rule 8 Tests (Placement & Free Space Around Net Quantity)
# --------------------------------------------------------------------------

def test_rule_8_pdp_location_review_required_without_panel_flag():
    """Mandatory declarations co-located on panel require inspector PDP confirmation."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_8(extraction, package_metadata={})
    pdp_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-PDP-LOCATION")
    assert pdp_eval.status == ComplianceVerdict.REVIEW_REQUIRED


def test_rule_8_pdp_location_pass_with_verified_flag():
    """When metadata confirms panel is PDP, Rule 8(1) location yields PASS."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_8(
        extraction,
        package_metadata={"is_principal_display_panel": True},
    )
    pdp_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-PDP-LOCATION")
    assert pdp_eval.status == ComplianceVerdict.PASS


def test_rule_8_pdp_location_fail_when_mandatory_missing():
    """Missing product name or net quantity on display panel yields Rule 8(1) FAIL."""
    extraction = _make_sample_extraction(product_name="", net_quantity="")
    evaluations = evaluate_rule_8(extraction)
    pdp_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-PDP-LOCATION")
    assert pdp_eval.status == ComplianceVerdict.FAIL
    assert "Statutory violation under Rule 8(1)" in pdp_eval.explanation


def test_rule_8_free_space_encroachment_detected_fail():
    """Extracted text bounding box encroaching into net quantity free space yields FAIL."""
    # Net quantity at (x=200, y=200, w=100, h=20)
    # Vertical exclusion zone: [y - h, y + 2h] = [180, 240]
    # Place MRP directly underneath at y=210 (encroachment into [180, 240])
    q_box = SourceRegion(x=200, y=200, width=100, height=20)
    encroaching_mrp = SourceRegion(x=210, y=210, width=80, height=15)

    extraction = _make_sample_extraction(q_bbox=q_box, mrp_bbox=encroaching_mrp)
    evaluations = evaluate_rule_8(extraction)

    free_space_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-FREE-SPACE")
    assert free_space_eval.status == ComplianceVerdict.FAIL
    assert "encroaches into the mandatory free space" in free_space_eval.explanation
    assert "mrp" in free_space_eval.explanation


def test_rule_8_free_space_clear_yields_review_required():
    """When no text box encroaches, inspector must verify background artwork is clear."""
    # Net quantity at (200, 200, 100, 20). MRP far away at (200, 350, 100, 20).
    q_box = SourceRegion(x=200, y=200, width=100, height=20)
    far_mrp = SourceRegion(x=200, y=350, width=100, height=20)

    extraction = _make_sample_extraction(q_bbox=q_box, mrp_bbox=far_mrp)
    evaluations = evaluate_rule_8(extraction)

    free_space_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-FREE-SPACE")
    assert free_space_eval.status == ComplianceVerdict.REVIEW_REQUIRED
    assert "Human inspector review required to verify background artwork" in free_space_eval.explanation


def test_rule_8_free_space_missing_bbox_not_assessable():
    """Missing net quantity bounding box renders free space evaluation NOT_ASSESSABLE."""
    extraction = _make_sample_extraction()
    extraction.net_quantity.source_region = None

    evaluations = evaluate_rule_8(extraction)
    free_space_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R08-01-FREE-SPACE")
    assert free_space_eval.status == ComplianceVerdict.NOT_ASSESSABLE


# --------------------------------------------------------------------------
# 3. Rule 9 Tests (Language, Legibility, Contrast, Liquid Restrictions)
# --------------------------------------------------------------------------

def test_rule_9_language_english_pass():
    """Declarations presented in English satisfy Rule 9(4)."""
    extraction = _make_sample_extraction(product_name="Wheat Flour")
    evaluations = evaluate_rule_9(extraction)
    lang_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-04-LANGUAGE")
    assert lang_eval.status == ComplianceVerdict.PASS
    assert "English / Hindi" in lang_eval.explanation


def test_rule_9_language_hindi_devanagari_pass():
    """Declarations presented in Hindi (Devanagari script) satisfy Rule 9(4)."""
    extraction = _make_sample_extraction(
        product_name="गेहूं का आटा",
        net_quantity="५ किग्रा",
    )
    evaluations = evaluate_rule_9(extraction)
    lang_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-04-LANGUAGE")
    assert lang_eval.status == ComplianceVerdict.PASS


def test_rule_9_language_unauthorized_script_fail():
    """Declarations exclusively in non-English, non-Devanagari scripts yield FAIL."""
    # Exclusively Arabic script with no English or Hindi characters
    extraction = _make_sample_extraction(
        product_name="طحين القمح الكامل",
        net_quantity="٥ كغ",
    )
    # Strip English from other fields
    extraction.manufacturer_name.value = "شركة المواد الغذائية"
    extraction.manufacturer_address.value = "صندوق بريد ۱۲۳"
    extraction.mrp.value = "۵۰"
    extraction.consumer_care_details.value = "هاتف ۱۲۳"

    evaluations = evaluate_rule_9(extraction)
    lang_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-04-LANGUAGE")
    assert lang_eval.status == ComplianceVerdict.FAIL
    assert "Statutory violation under Rule 9(4)" in lang_eval.explanation


def test_rule_9_legibility_high_confidence_pass():
    """High OCR optical confidence across all mandatory fields fulfills Rule 9(1)(a)."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_9(extraction)
    leg_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-01A-LEGIBILITY")
    assert leg_eval.status == ComplianceVerdict.PASS


def test_rule_9_legibility_low_confidence_review_required():
    """Low optical confidence (< 0.70) triggers human review under Rule 9(1)(a)."""
    extraction = _make_sample_extraction()
    extraction.mrp.confidence = 0.58  # Borderline confidence

    evaluations = evaluate_rule_9(extraction)
    leg_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-01A-LEGIBILITY")
    assert leg_eval.status == ComplianceVerdict.REVIEW_REQUIRED
    assert "Borderline optical legibility detected" in leg_eval.explanation


def test_rule_9_legibility_unreadable_field_fail():
    """Unreadable mandatory declaration constitutes a statutory violation under Rule 9(1)(a)."""
    extraction = _make_sample_extraction()
    extraction.net_quantity.status = "unreadable"

    evaluations = evaluate_rule_9(extraction)
    leg_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-01A-LEGIBILITY")
    assert leg_eval.status == ComplianceVerdict.FAIL
    assert "illegible or obscured" in leg_eval.explanation


def test_rule_9_contrast_review_required():
    """Extracted numerals require human review to verify conspicuous background contrast."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_9(extraction, package_metadata={})
    contrast_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-01B-CONTRAST")
    assert contrast_eval.status == ComplianceVerdict.REVIEW_REQUIRED


def test_rule_9_liquid_read_through_fail():
    """Label positioned behind liquid commodity yields FAIL under Rule 9(2)."""
    extraction = _make_sample_extraction()
    evaluations = evaluate_rule_9(
        extraction,
        package_metadata={"read_through_liquid": True},
    )
    liq_eval = next(e for e in evaluations if e.rule_id == "LMR-2011-R09-02-LIQUID-READ")
    assert liq_eval.status == ComplianceVerdict.FAIL
    assert "Statutory violation under Rule 9(2)" in liq_eval.explanation


# --------------------------------------------------------------------------
# 4. Multi-Rule Engine Integration Tests
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_rule_engine_evaluate_all_rules_aggregation():
    """DeterministicRuleEngine.evaluate_all evaluates Rules 6, 7, 8, and 9 together."""
    extraction = _make_sample_extraction()
    engine = DeterministicRuleEngine()

    result = await engine.evaluate_all(
        extraction,
        package_metadata={
            "is_principal_display_panel": True,
            "measured_numeral_height_mm": 5.0,
            "is_contrast_verified": True,
        },
    )

    rule_ids = [e.rule_id for e in result.rule_evaluations]

    # Verify presence of all rule families
    assert any(rid.startswith("LMR-2011-R06") for rid in rule_ids)
    assert any(rid.startswith("LMR-2011-R07") for rid in rule_ids)
    assert any(rid.startswith("LMR-2011-R08") for rid in rule_ids)
    assert any(rid.startswith("LMR-2011-R09") for rid in rule_ids)

    # 9 (Rule 6) + 2 (Rule 7) + 2 (Rule 8) + 4 (Rule 9) = 17 total evaluations
    assert len(result.rule_evaluations) == 17
    assert result.overall_disposition in (
        ComplianceVerdict.PASS,
        ComplianceVerdict.REVIEW_REQUIRED,
    )


@pytest.mark.asyncio
async def test_rule_engine_selective_rule_evaluation():
    """DeterministicRuleEngine.evaluate supports targeting specific rule subsets."""
    extraction = _make_sample_extraction()
    engine = DeterministicRuleEngine()

    # Target only Rule 7 and Rule 8
    result_7_8 = await engine.evaluate(extraction, rules=[7, 8])
    rule_ids = [e.rule_id for e in result_7_8.rule_evaluations]

    assert len(rule_ids) == 4  # 2 from Rule 7, 2 from Rule 8
    assert all(rid.startswith("LMR-2011-R07") or rid.startswith("LMR-2011-R08") for rid in rule_ids)
