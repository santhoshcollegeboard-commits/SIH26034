"""Unit tests for MultiPanelAggregator service."""

import pytest

from backend.app.schemas.compliance import OverallVerdict, RuleStatus
from backend.app.schemas.extraction import (
    CandidateField,
    ExtractedField,
    ExtractionResult,
    SourceRegion,
)
from backend.app.services.aggregation import (
    MultiPanelAggregator,
    are_declarations_consistent,
)
from backend.app.services.rules.engine import DeterministicRuleEngine


def _make_field(
    val: str | None,
    status: str = "extracted",
    conf: float = 0.9,
    region: tuple = (10, 10, 100, 30),
) -> ExtractedField:
    return ExtractedField(
        value=val,
        confidence=conf if val else None,
        source_region=SourceRegion(x=region[0], y=region[1], width=region[2], height=region[3])
        if val
        else None,
        status=status,
    )


def test_semantic_consistency_checks():
    """Verify consistency and conflict detection logic for various fields."""
    # Net quantity consistency
    assert are_declarations_consistent("net_quantity", "500 g", "500g")
    assert are_declarations_consistent("net_quantity", "Net Wt: 500 g", "500 g")
    assert not are_declarations_consistent("net_quantity", "500 g", "250 g")
    assert not are_declarations_consistent("net_quantity", "500 g", "500 ml")

    # MRP consistency
    assert are_declarations_consistent("mrp", "₹ 245.00 (Inclusive of all taxes)", "MRP ₹245.00")
    assert not are_declarations_consistent("mrp", "₹ 150.00 (Inclusive of all taxes)", "₹ 250.00")

    # Date consistency
    assert are_declarations_consistent("month_year_of_manufacture", "08/2026", "Aug 2026")
    assert not are_declarations_consistent("month_year_of_manufacture", "08/2026", "11/2026")

    # Country of origin
    assert are_declarations_consistent("country_of_origin", "India", "Made in India")
    assert not are_declarations_consistent("country_of_origin", "India", "China")


def test_complementary_panels_aggregation():
    """Panel 1 has front declarations, Panel 2 has rear declarations."""
    front_panel = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Black Tea"),
        net_quantity=_make_field("500 g"),
    )

    back_panel = ExtractionResult(
        manufacturer_name=_make_field("Himalayan Highlands Tea Estates"),
        manufacturer_address=_make_field("Plot 42, Tea Park Road, Dibrugarh, Assam - 786001"),
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes)"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Toll-Free: 1800-209-8899"),
        country_of_origin=_make_field("India"),
    )

    unified = MultiPanelAggregator.aggregate(
        extractions=[front_panel, back_panel],
        panel_labels=["Front Panel", "Back Panel"],
    )

    # Front panel declarations present
    assert unified.product_name.status == "extracted"
    assert unified.product_name.value == "Assam Gold"
    assert unified.product_name.source_panel_label == "Front Panel"
    assert unified.product_name.source_image_index == 0

    assert unified.net_quantity.status == "extracted"
    assert unified.net_quantity.value == "500 g"
    assert unified.net_quantity.source_panel_label == "Front Panel"

    # Back panel declarations present
    assert unified.manufacturer_name.status == "extracted"
    assert unified.manufacturer_name.source_panel_label == "Back Panel"
    assert unified.manufacturer_name.source_image_index == 1

    assert unified.mrp.status == "extracted"
    assert "245.00" in unified.mrp.value
    assert unified.mrp.source_panel_label == "Back Panel"

    assert unified.consumer_care_details.status == "extracted"
    assert "1800-209-8899" in unified.consumer_care_details.value


def test_duplicate_fields_selects_best_candidate():
    """When both panels have the same field, highest confidence / more complete is chosen."""
    panel1 = ExtractionResult(
        product_name=_make_field("Assam Gold", conf=0.85),
        mrp=_make_field("₹ 245", conf=0.7),
    )
    panel2 = ExtractionResult(
        product_name=_make_field("Assam Gold CTC Tea", conf=0.95),
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes)", conf=0.96),
    )

    unified = MultiPanelAggregator.aggregate([panel1, panel2], ["Front", "Back"])

    assert unified.product_name.status == "extracted"
    assert unified.product_name.value == "Assam Gold CTC Tea"
    assert unified.product_name.confidence == 0.95
    assert unified.product_name.source_panel_label == "Back"

    assert unified.mrp.status == "extracted"
    assert "(Inclusive of all taxes)" in unified.mrp.value
    assert unified.mrp.confidence == 0.96
    assert len(unified.mrp.all_candidates) == 2


def test_conflicting_fields_flagged_as_conflict():
    """Contradictory values across panels must set status='conflict'."""
    panel1 = ExtractionResult(
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 100 (Inclusive of all taxes)"),
    )
    panel2 = ExtractionResult(
        net_quantity=_make_field("200 g"),
        mrp=_make_field("₹ 250 (Inclusive of all taxes)"),
    )

    unified = MultiPanelAggregator.aggregate([panel1, panel2], ["Front", "Back"])

    assert unified.net_quantity.status == "conflict"
    assert "CONFLICT" in unified.net_quantity.value
    assert "500 g" in unified.net_quantity.conflict_details
    assert "200 g" in unified.net_quantity.conflict_details

    assert unified.mrp.status == "conflict"
    assert "CONFLICT" in unified.mrp.value


@pytest.mark.asyncio
async def test_rule_engine_flags_conflict_for_review():
    """Deterministic rule engine must evaluate conflict status as NOT_VERIFIABLE."""
    panel1 = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Tea"),
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 100 (Inclusive of all taxes)"),
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("Plot 4, Industrial Area, Pune - 411018"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Phone: 1800-209-8899"),
    )
    panel2 = ExtractionResult(
        mrp=_make_field("₹ 250 (Inclusive of all taxes)"),  # Conflicting price!
    )

    unified = MultiPanelAggregator.aggregate([panel1, panel2], ["Front", "Back"])
    engine = DeterministicRuleEngine()
    result = await engine.evaluate_compliance({}, unified)

    # Contradiction on MRP should result in FLAGGED_FOR_REVIEW
    mrp_eval = next(e for e in result.evaluations if e.rule_id == "LM-PC-06-1-E")
    assert mrp_eval.status == RuleStatus.NOT_VERIFIABLE
    assert "Conflicting declarations" in mrp_eval.message
    assert result.overall_verdict == OverallVerdict.FLAGGED_FOR_REVIEW


def test_unreadable_on_one_panel_extracted_on_another():
    """If one panel is unreadable but another is clearly readable, use extracted."""
    panel1 = ExtractionResult(
        consumer_care_details=_make_field(None, status="unreadable"),
    )
    panel2 = ExtractionResult(
        consumer_care_details=_make_field("Email: care@company.com", status="extracted"),
    )

    unified = MultiPanelAggregator.aggregate([panel1, panel2], ["Front", "Back"])

    assert unified.consumer_care_details.status == "extracted"
    assert unified.consumer_care_details.value == "Email: care@company.com"
    assert unified.consumer_care_details.source_panel_label == "Back"
