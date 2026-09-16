"""Tests for deterministic Rule 6 compliance evaluator and DeterministicRuleEngine.

Specification: docs/legal/rule_6_mapping.md
Authoritative Baseline: LMR-2011-BASE-R06

Verifies:
1. Clearly compliant package -> PASS
2. Missing mandatory declaration -> FAIL
3. Non-metric unit -> FAIL
4. Unreadable observation -> REVIEW_REQUIRED
5. Low-confidence observation (<0.70) -> REVIEW_REQUIRED
6. Rule and version traceability preservation
7. Multiple rule aggregation behavior
8. Complete independence from external AI providers
"""

from unittest.mock import patch
# pyrefly: ignore [missing-import]
import pytest

from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult, SourceRegion
from backend.app.services.rule_engine_service import DeterministicRuleEngine
from rules.rule_6_declarations import (
    CONFIDENCE_THRESHOLD,
    RULE_VERSION,
    aggregate_disposition,
    evaluate_rule_6,
)


def _make_compliant_extraction() -> ExtractionResult:
    """Build a fully compliant ExtractionResult where all Rule 6 declarations are valid."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Organic Whole Wheat Atta",
            confidence=0.98,
            source_region=SourceRegion(x=50, y=50, width=200, height=40),
            status="extracted",
        ),
        manufacturer_name=ExtractedField(
            value="Heritage Foods India Pvt Ltd",
            confidence=0.95,
            source_region=SourceRegion(x=50, y=120, width=300, height=35),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Plot 42, Industrial Area, Sector 8, Gandhinagar, Gujarat - 382028",
            confidence=0.92,
            source_region=SourceRegion(x=50, y=160, width=400, height=50),
            status="extracted",
        ),
        packer_name=ExtractedField(
            value=None, confidence=None, source_region=None, status="not_found"
        ),
        importer_name=ExtractedField(
            value=None, confidence=None, source_region=None, status="not_found"
        ),
        net_quantity=ExtractedField(
            value="5 kg",
            confidence=0.97,
            source_region=SourceRegion(x=100, y=300, width=120, height=40),
            status="extracted",
        ),
        mrp=ExtractedField(
            value="MRP ₹275.00 (incl. of all taxes)",
            confidence=0.94,
            source_region=SourceRegion(x=150, y=350, width=220, height=40),
            status="extracted",
        ),
        month_year_of_manufacture=ExtractedField(
            value="08/2026",
            confidence=0.91,
            source_region=SourceRegion(x=80, y=400, width=140, height=30),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="Consumer Care: 1800-425-9999, care@heritagefoods.in",
            confidence=0.93,
            source_region=SourceRegion(x=50, y=450, width=350, height=35),
            status="extracted",
        ),
    )


@pytest.mark.asyncio
async def test_compliant_package_yields_overall_pass():
    """A package with all mandatory Rule 6 declarations valid must yield overall PASS."""
    extraction = _make_compliant_extraction()
    engine = DeterministicRuleEngine()

    result = await engine.evaluate(extraction, package_id="TEST-PKG-001")

    assert result.overall_disposition == ComplianceVerdict.PASS
    assert len(result.rule_evaluations) == 9
    assert all(e.status == ComplianceVerdict.PASS for e in result.rule_evaluations)
    assert "PASS" in result.summary


@pytest.mark.asyncio
async def test_missing_mandatory_mrp_yields_fail():
    """Missing MRP (Rule 6(1)(e)) must yield statutory FAIL."""
    extraction = _make_compliant_extraction()
    extraction.mrp = ExtractedField(
        value=None, confidence=None, source_region=None, status="not_found"
    )

    engine = DeterministicRuleEngine()
    result = await engine.evaluate(extraction)

    assert result.overall_disposition == ComplianceVerdict.FAIL
    mrp_eval = next(
        e for e in result.rule_evaluations if e.rule_id == "LMR-2011-R06-01E-MRP"
    )
    assert mrp_eval.status == ComplianceVerdict.FAIL
    assert "missing" in mrp_eval.explanation.lower()
    assert mrp_eval.rule_version == RULE_VERSION


@pytest.mark.asyncio
async def test_missing_manufacturer_address_yields_fail():
    """Missing manufacturer address (Rule 6(1)(a)) must yield statutory FAIL."""
    extraction = _make_compliant_extraction()
    extraction.manufacturer_address = ExtractedField(
        value="", confidence=None, source_region=None, status="not_found"
    )

    engine = DeterministicRuleEngine()
    result = await engine.evaluate(extraction)

    assert result.overall_disposition == ComplianceVerdict.FAIL
    addr_eval = next(
        e for e in result.rule_evaluations if e.rule_id == "LMR-2011-R06-01A-MFR-ADDR"
    )
    assert addr_eval.status == ComplianceVerdict.FAIL
    assert "missing" in addr_eval.explanation.lower()


@pytest.mark.asyncio
async def test_non_metric_unit_yields_fail():
    """Declaring net quantity in non-metric units alone (e.g. '2 lbs') must yield FAIL."""
    extraction = _make_compliant_extraction()
    extraction.net_quantity = ExtractedField(
        value="Net Wt. 2 lbs", confidence=0.96, status="extracted"
    )

    engine = DeterministicRuleEngine()
    result = await engine.evaluate(extraction)

    assert result.overall_disposition == ComplianceVerdict.FAIL
    qty_eval = next(
        e for e in result.rule_evaluations if e.rule_id == "LMR-2011-R06-01C-NET-QTY"
    )
    assert qty_eval.status == ComplianceVerdict.FAIL
    assert "non-metric" in qty_eval.explanation.lower()


@pytest.mark.asyncio
async def test_unreadable_mfg_date_yields_review_required():
    """Unreadable manufacturing date must trigger REVIEW_REQUIRED without failing."""
    extraction = _make_compliant_extraction()
    extraction.month_year_of_manufacture = ExtractedField(
        value=None,
        confidence=None,
        source_region=SourceRegion(x=80, y=400, width=140, height=30),
        status="unreadable",
    )

    engine = DeterministicRuleEngine()
    result = await engine.evaluate(extraction)

    # Must NOT silently fail or pass; must escalate to human reviewer
    assert result.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED
    date_eval = next(
        e for e in result.rule_evaluations if e.rule_id == "LMR-2011-R06-01D-MFG-DATE"
    )
    assert date_eval.status == ComplianceVerdict.REVIEW_REQUIRED
    assert "unreadable" in date_eval.explanation.lower()


@pytest.mark.asyncio
async def test_low_confidence_mrp_yields_review_required():
    """Low extraction confidence (<0.70) on valid MRP must trigger REVIEW_REQUIRED."""
    extraction = _make_compliant_extraction()
    extraction.mrp = ExtractedField(
        value="MRP Rs. 150.00",
        confidence=0.52,  # Below 0.70 threshold
        source_region=SourceRegion(x=150, y=350, width=220, height=40),
        status="extracted",
    )

    engine = DeterministicRuleEngine()
    result = await engine.evaluate(extraction)

    assert result.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED
    mrp_eval = next(
        e for e in result.rule_evaluations if e.rule_id == "LMR-2011-R06-01E-MRP"
    )
    assert mrp_eval.status == ComplianceVerdict.REVIEW_REQUIRED
    assert "confidence" in mrp_eval.explanation.lower()


@pytest.mark.asyncio
async def test_rule_traceability_preserved_across_all_evaluations():
    """Every RuleEvaluation must contain rule_id, rule_version, and statutory reasoning."""
    extraction = _make_compliant_extraction()
    evaluations = evaluate_rule_6(extraction)

    for eval_item in evaluations:
        assert eval_item.rule_id.startswith("LMR-2011-R06-")
        assert eval_item.rule_version == "LMR-2011-BASE-R06"
        assert len(eval_item.rule_name) > 0
        assert len(eval_item.explanation) > 0
        assert len(eval_item.expected_requirement) > 0
        assert eval_item.status in (
            ComplianceVerdict.PASS,
            ComplianceVerdict.FAIL,
            ComplianceVerdict.REVIEW_REQUIRED,
            ComplianceVerdict.NOT_ASSESSABLE,
        )


@pytest.mark.asyncio
async def test_conditional_importer_handling():
    """Imported commodity without importer name must FAIL; domestic commodity passes."""
    extraction = _make_compliant_extraction()

    engine = DeterministicRuleEngine()

    # Case A: Domestic package -> Importer not required -> PASS
    result_domestic = await engine.evaluate(
        extraction, package_metadata={"is_imported": False}
    )
    importer_eval_dom = next(
        e
        for e in result_domestic.rule_evaluations
        if e.rule_id == "LMR-2011-R06-01A-IMPORTER"
    )
    assert importer_eval_dom.status == ComplianceVerdict.PASS

    # Case B: Imported package without importer declared -> FAIL
    result_imported = await engine.evaluate(
        extraction, package_metadata={"is_imported": True}
    )
    importer_eval_imp = next(
        e
        for e in result_imported.rule_evaluations
        if e.rule_id == "LMR-2011-R06-01A-IMPORTER"
    )
    assert importer_eval_imp.status == ComplianceVerdict.FAIL
    assert result_imported.overall_disposition == ComplianceVerdict.FAIL


@pytest.mark.asyncio
async def test_not_assessable_clause_evaluation():
    """Evaluating unassessable clause yields NOT_ASSESSABLE as mapped in rule_6_mapping.md."""
    extraction = _make_compliant_extraction()

    evaluations = evaluate_rule_6(extraction, include_unassessable=True)
    dim_eval = next(
        e for e in evaluations if e.rule_id == "LMR-2011-R06-01F-DIMENSIONS"
    )
    assert dim_eval.status == ComplianceVerdict.NOT_ASSESSABLE

    # Empty evaluations list aggregates to NOT_ASSESSABLE
    assert aggregate_disposition([]) == ComplianceVerdict.NOT_ASSESSABLE


@pytest.mark.asyncio
async def test_rule_engine_never_calls_ai_model():
    """Rule engine execution must not invoke Gemini, Google GenAI client, or network calls."""
    extraction = _make_compliant_extraction()
    engine = DeterministicRuleEngine()

    # Patch google.genai to ensure zero calls
    with patch("google.genai.Client") as mock_client:
        result = await engine.evaluate(extraction)
        mock_client.assert_not_called()

    assert result.overall_disposition == ComplianceVerdict.PASS


@pytest.mark.asyncio
async def test_rule_engine_evaluate_compliance_dict_interface():
    """Fulfill abstract RuleEngine.evaluate_compliance accepting dicts and returning dicts."""
    extraction = _make_compliant_extraction()
    engine = DeterministicRuleEngine()

    result_dict = await engine.evaluate_compliance(
        package_metadata={"package_id": "DICT-TEST-001"},
        extracted_declarations=extraction.model_dump(),
    )

    assert isinstance(result_dict, dict)
    assert result_dict["overall_disposition"] == "PASS"
    assert len(result_dict["rule_evaluations"]) == 9
    assert result_dict["package_id"] == "DICT-TEST-001"
