"""Tests for the Compliance Result Pydantic schemas.

Verifies the four canonical dispositions and schema validation rules.
"""

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from pydantic import ValidationError

from backend.app.schemas.compliance import (
    ComplianceVerdict,
    InspectionResult,
    RuleEvaluation,
)
from backend.app.schemas.extraction import SourceRegion


def test_canonical_dispositions_enum():
    """Ensure exactly the four canonical dispositions are defined."""
    expected_states = {"PASS", "FAIL", "REVIEW_REQUIRED", "NOT_ASSESSABLE"}
    actual_states = {member.value for member in ComplianceVerdict}
    assert actual_states == expected_states
    assert len(ComplianceVerdict) == 4


def test_rule_evaluation_valid():
    """Verify construction of a valid RuleEvaluation."""
    eval_pass = RuleEvaluation(
        rule_id="LMR-2011-R06-MRP",
        rule_version="2011.amended2021",
        rule_name="Maximum Retail Price Declaration",
        status=ComplianceVerdict.PASS,
        explanation="MRP is clearly declared inclusive of all taxes.",
        observed_value="₹120.00",
        expected_requirement="Must declare retail sale price in format 'MRP Rs. / ₹ ... incl. of all taxes'",
        source_region=SourceRegion(x=100, y=200, width=150, height=30),
        evidence_reference="crop_mrp_001.png",
    )

    assert eval_pass.rule_id == "LMR-2011-R06-MRP"
    assert eval_pass.status == ComplianceVerdict.PASS
    assert eval_pass.source_region is not None
    assert eval_pass.source_region.x == 100

    # Ensure JSON serializable
    json_data = eval_pass.model_dump()
    assert json_data["status"] == "PASS"


def test_rule_evaluation_rejects_invalid_verdict():
    """Verify that non-canonical verdicts raise a ValidationError."""
    with pytest.raises(ValidationError):
        RuleEvaluation(
            rule_id="LMR-2011-R06",
            rule_version="1.0",
            rule_name="Rule Check",
            status="UNCERTAIN",  # Non-canonical state
            explanation="Invalid status test",
        )

    with pytest.raises(ValidationError):
        RuleEvaluation(
            rule_id="LMR-2011-R06",
            rule_version="1.0",
            rule_name="Rule Check",
            status="WARNING",  # Non-canonical state
            explanation="Invalid status test",
        )


def test_inspection_result_aggregation():
    """Verify InspectionResult with multiple RuleEvaluations."""
    eval1 = RuleEvaluation(
        rule_id="LMR-2011-R06-NETQTY",
        rule_version="2011.amended2021",
        rule_name="Net Quantity Declaration",
        status=ComplianceVerdict.PASS,
        explanation="Net quantity correctly declared in standard metric units.",
        observed_value="500 g",
        expected_requirement="Standard SI unit (g, kg, ml, l)",
    )

    eval2 = RuleEvaluation(
        rule_id="LMR-2011-R06-MFGDATE",
        rule_version="2011.amended2021",
        rule_name="Date of Manufacture",
        status=ComplianceVerdict.REVIEW_REQUIRED,
        explanation="Month/Year text is slightly blurred (confidence 0.62); inspector confirmation required.",
        observed_value="08/202?",
        expected_requirement="Month and year of manufacture or packing",
    )

    inspection = InspectionResult(
        overall_disposition=ComplianceVerdict.REVIEW_REQUIRED,
        rule_evaluations=[eval1, eval2],
        summary="1 rule passed, 1 rule flagged for human review.",
        package_id="PKG-2026-001",
        evaluated_at="2026-09-08T21:52:00Z",
    )

    assert inspection.overall_disposition == ComplianceVerdict.REVIEW_REQUIRED
    assert len(inspection.rule_evaluations) == 2
    assert inspection.rule_evaluations[0].status == ComplianceVerdict.PASS
    assert inspection.rule_evaluations[1].status == ComplianceVerdict.REVIEW_REQUIRED

    # Check JSON export
    dumped = inspection.model_dump()
    assert dumped["overall_disposition"] == "REVIEW_REQUIRED"
    assert len(dumped["rule_evaluations"]) == 2
