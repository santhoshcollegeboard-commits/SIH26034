"""Pydantic schemas for the RESULT and REPORT stage (Step 10).

Represents a presentation-ready inspection report constructed strictly from
persisted Evidence Ledger data. Does not recalculate or override compliance verdicts.
Adheres strictly to the centralized missing-data rendering policy.
"""

from typing import List, Optional, Union
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, model_serializer

from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.ledger import (
    EvidenceRecord,
    ObservationRecord,
    ReviewActionRecord,
    RuleEvaluationRecord,
)
from backend.app.schemas.quality import QualityAssessment
from backend.app.services.formatters import (
    EMPTY_EVIDENCE_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    EMPTY_REVIEW_ACTIONS_MESSAGE,
    EMPTY_RULE_EVALUATIONS_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    clean_presentation_dict,
)


class TraceabilityInfo(BaseModel):
    """Statutory and engine version traceability metadata."""

    model_config = ConfigDict(extra="forbid")

    rule_engine_version: str = Field(
        "DeterministicRuleEngine-v1.0",
        description="Deterministic compliance rule engine identifier",
    )
    statutory_source: str = Field(
        "The Legal Metrology (Packaged Commodities) Rules, 2011",
        description="Governing statutory act and notification",
    )
    evaluated_rule_count: int = Field(..., description="Total statutory rule evaluations")
    initial_rule_count: int = Field(..., description="Initial pre-review evaluations")
    post_review_rule_count: int = Field(0, description="Post-review re-evaluations")
    human_review_applied: bool = Field(..., description="Whether human review actions were recorded")
    provenance_chain: str = Field(
        "Evidence -> Observation -> Rule Evaluation -> Review Action (if applicable) -> Final Disposition",
        description="Auditable decision path chain",
    )


class ObservationPresentation(BaseModel):
    """Presentation representation of an extracted/reviewed declaration observation."""

    model_config = ConfigDict(extra="allow")

    observation_id: str = Field(..., description="Unique observation ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    field_name: str = Field(..., description="Target declaration field name")
    value: str = Field(..., description="Observed text or policy missing message")
    confidence: str = Field(..., description="Confidence score string or policy missing message")
    status: str = Field(..., description="Extraction or recording status")
    source_region: str = Field(..., description="Source region string or policy missing message")
    source_type: str = Field(..., description="Source of observation")
    parent_observation_id: Optional[str] = Field(None, description="Parent observation ID if any")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class RuleEvaluationPresentation(BaseModel):
    """Presentation representation of a statutory rule evaluation."""

    model_config = ConfigDict(extra="allow")

    evaluation_id: str = Field(..., description="Unique evaluation ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    rule_id: str = Field(..., description="Statutory rule identifier")
    rule_version: str = Field(..., description="Rule version identifier")
    rule_name: str = Field(..., description="Rule name")
    statutory_reference: str = Field(..., description="Statutory clause reference")
    status: ComplianceVerdict = Field(
        ..., description="Authoritative status: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE"
    )
    observed_value: str = Field(..., description="Observed value or policy missing message")
    expected_requirement: str = Field(..., description="Expected requirement or policy missing message")
    explanation: str = Field(..., description="Deterministic reasoning or policy missing message")
    source_region: str = Field(..., description="Bounding box string or policy missing message")
    evidence_reference: Optional[str] = Field(None, description="Evidence reference")
    evaluation_stage: str = Field("initial", description="Evaluation stage")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class ReviewActionPresentation(BaseModel):
    """Presentation representation of a human reviewer action."""

    model_config = ConfigDict(extra="allow")

    review_id: str = Field(..., description="Unique review action ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    field_name: str = Field(..., description="Target declaration field name")
    action: str = Field(..., description="Review action name")
    original_value: str = Field(..., description="Original value or policy missing message")
    reviewed_value: str = Field(..., description="Reviewed value or policy missing message")
    original_confidence: str = Field(..., description="Original confidence or policy missing message")
    source_region_before: str = Field(..., description="Prior bounding box or policy missing message")
    source_region_after: str = Field(..., description="Updated bounding box or policy missing message")
    reviewer_notes: str = Field(..., description="Reviewer notes or policy missing message")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class InspectionResultReport(BaseModel):
    """Structured report-ready representation of an inspection result."""

    model_config = ConfigDict(extra="allow")

    inspection_id: str = Field(..., description="Unique inspection identifier")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    package_id: str = Field(..., description="Package identifier if available")
    overall_disposition: ComplianceVerdict = Field(
        ...,
        description="Authoritative canonical disposition: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE",
    )
    summary: str = Field(..., description="Inspection findings summary")
    evidence: Optional[Union[EvidenceRecord, str]] = Field(
        None, description="Associated image and capture quality metadata"
    )
    quality: Optional[Union[QualityAssessment, str]] = Field(
        None, description="Quality Gate assessment details"
    )
    observations: List[Union[ObservationPresentation, ObservationRecord]] = Field(
        default_factory=list, description="Extracted and reviewed declaration observations"
    )
    rule_evaluations: List[Union[RuleEvaluationPresentation, RuleEvaluationRecord]] = Field(
        default_factory=list, description="All evaluated statutory rules"
    )
    review_actions: List[Union[ReviewActionPresentation, ReviewActionRecord]] = Field(
        default_factory=list, description="Human reviewer resolutions if any"
    )
    traceability: TraceabilityInfo = Field(
        ..., description="Statutory version and engine traceability info"
    )
    decision_trail_summary: str = Field(
        ..., description="Reconstructed narrative audit trail"
    )

    # Section-level collection status messages
    evidence_message: str = Field(
        EMPTY_EVIDENCE_MESSAGE, description="Section status message for evidence records"
    )
    observations_message: str = Field(
        EMPTY_OBSERVATIONS_MESSAGE, description="Section status message for observations"
    )
    rule_evaluations_message: str = Field(
        EMPTY_RULE_EVALUATIONS_MESSAGE, description="Section status message for rule evaluations"
    )
    review_actions_message: str = Field(
        EMPTY_REVIEW_ACTIONS_MESSAGE, description="Section status message for human review actions"
    )
    quality_assessment_message: str = Field(
        NOT_AVAILABLE_MESSAGE, description="Quality gate status message"
    )

    @model_serializer(mode="wrap")
    def _clean_nulls(self, handler):
        data = handler(self)
        return clean_presentation_dict(data)
