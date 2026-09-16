"""Pydantic schemas for Legal Metrology deterministic compliance results.

These schemas define the contract for the CHECK stage of the PackCheck pipeline.
Deterministic rules evaluate extracted declarations and produce auditable verdicts.
Canonical dispositions are strictly constrained to:
PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE.
"""

from enum import Enum
from typing import Any, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from backend.app.schemas.common import SourceRegion


class ComplianceVerdict(str, Enum):
    """Canonical four-state compliance disposition.

    PASS — Statutorily compliant based on evaluated rules.
    FAIL — Non-compliant; statutory violation detected.
    REVIEW_REQUIRED — Ambiguous, low-confidence, or borderline; human inspector review needed.
    NOT_ASSESSABLE — Unusable, missing, or obscured evidence; cannot determine compliance.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    NOT_ASSESSABLE = "NOT_ASSESSABLE"


class RuleEvaluation(BaseModel):
    """Evaluation result of a single statutory compliance rule."""

    rule_id: str = Field(..., description="Unique statutory rule identifier (e.g., 'LMR-2011-R06')")
    rule_version: str = Field(..., description="Statutory rule version or amendment reference (e.g., '2011.amended2021')")
    rule_name: str = Field(..., description="Human-readable rule name or statutory description")
    status: ComplianceVerdict = Field(..., description="Evaluation verdict: PASS, FAIL, REVIEW_REQUIRED, or NOT_ASSESSABLE")
    explanation: str = Field(..., description="Deterministic reasoning explaining the verdict")
    observed_value: Optional[Any] = Field(None, description="Value(s) observed from extraction or image evidence")
    expected_requirement: Optional[str] = Field(None, description="Statutory requirement or threshold being evaluated")
    source_region: Optional[SourceRegion] = Field(None, description="Source bounding box or evidence region, if applicable")
    evidence_reference: Optional[str] = Field(None, description="Identifier, tag, or path to supporting evidence")


class InspectionResult(BaseModel):
    """Overall compliance inspection outcome aggregating individual rule evaluations.

    Output of the CHECK stage and foundation for subsequent REVIEW / RESULT stages.
    """

    overall_disposition: ComplianceVerdict = Field(..., description="Aggregate disposition: PASS, FAIL, REVIEW_REQUIRED, or NOT_ASSESSABLE")
    overall_verdict: Optional[ComplianceVerdict] = Field(None, description="Canonical verdict alias for overall_disposition")
    rule_evaluations: List[RuleEvaluation] = Field(default_factory=list, description="Individual rule check results")
    evaluations: Optional[List[RuleEvaluation]] = Field(None, description="Alias for rule_evaluations")
    summary: Optional[str] = Field(None, description="High-level narrative summary of inspection findings")
    package_id: Optional[str] = Field(None, description="Identifier for the inspected commodity package, if available")
    evaluated_at: Optional[str] = Field(None, description="ISO timestamp of deterministic evaluation")

    def model_post_init(self, __context: Any) -> None:
        if self.overall_verdict is None:
            self.overall_verdict = self.overall_disposition
        if self.evaluations is None:
            self.evaluations = self.rule_evaluations

