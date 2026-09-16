"""Pydantic schemas for the Evidence Ledger (Step 9).

Preserves the complete auditable chain:
Evidence -> Observation -> Rule Evaluation -> Review Action -> Final Disposition

Answering:
"What evidence and decision path produced this inspection result?"
"""

from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field

from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict, InspectionResult
from backend.app.schemas.extraction import ExtractionResult
from backend.app.schemas.quality import QualityAssessment
from backend.app.schemas.review import FieldCorrection, FieldProvenance, ReviewAction


class EvidenceMetadataInput(BaseModel):
    """Input metadata for image/evidence uploaded for inspection."""

    model_config = ConfigDict(extra="forbid")

    filename: str = Field(..., description="Sanitized filename or safe identifier")
    media_type: str = Field(..., description="Image MIME type (e.g. image/jpeg, image/png)")
    file_size_bytes: Optional[int] = Field(None, description="Image file size in bytes")
    image_width: Optional[int] = Field(None, description="Image width in pixels")
    image_height: Optional[int] = Field(None, description="Image height in pixels")
    quality_assessment: Optional[QualityAssessment] = Field(
        None, description="QualityAssessment details from pre-OCR quality gate"
    )


class CreateInspectionRecordRequest(BaseModel):
    """Request payload to store an inspection result in the Evidence Ledger."""

    model_config = ConfigDict(extra="forbid")

    package_id: Optional[str] = Field(None, description="Optional commodity package identifier")
    evidence: Optional[EvidenceMetadataInput] = Field(
        None, description="Associated image/evidence metadata"
    )
    extraction: ExtractionResult = Field(..., description="OCR extraction declarations")
    compliance: InspectionResult = Field(..., description="Deterministic rule inspection outcome")
    provenance: Optional[Dict[str, FieldProvenance]] = Field(
        None, description="Optional field-level provenance records"
    )
    corrections: Optional[List[FieldCorrection]] = Field(
        None, description="Optional review corrections if already performed"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Arbitrary safe inspection metadata"
    )


class InspectionRecordSummary(BaseModel):
    """Header record summarizing an inspection in the ledger."""

    inspection_id: str = Field(..., description="Unique inspection identifier")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    overall_disposition: ComplianceVerdict = Field(
        ..., description="Canonical disposition: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE"
    )
    package_id: Optional[str] = Field(None, description="Package identifier")
    summary: Optional[str] = Field(None, description="Narrative summary")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Metadata")


class EvidenceRecord(BaseModel):
    """Persisted evidence record linked to an inspection."""

    evidence_id: str = Field(..., description="Unique evidence record ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    filename: str = Field(..., description="Safe filename or identifier")
    media_type: str = Field(..., description="MIME type")
    file_size_bytes: Optional[int] = Field(None, description="Byte size")
    image_width: Optional[int] = Field(None, description="Width")
    image_height: Optional[int] = Field(None, description="Height")
    quality_assessment: Optional[QualityAssessment] = Field(
        None, description="Quality assessment details"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp")


class ObservationRecord(BaseModel):
    """Persisted append-oriented field observation."""

    observation_id: str = Field(..., description="Unique observation ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    field_name: str = Field(..., description="Target declaration field name")
    value: Optional[str] = Field(None, description="Observed text")
    confidence: Optional[float] = Field(None, description="Confidence score 0.0-1.0")
    status: str = Field(..., description="Extraction status: extracted, unreadable, not_found")
    source_region: Optional[SourceRegion] = Field(None, description="Bounding box")
    source_type: str = Field(
        ...,
        description="Source of observation: 'ai_extraction', 'reviewer_correction', 'reviewer_confirmation'",
    )
    parent_observation_id: Optional[str] = Field(
        None, description="Parent observation ID if this observation modifies an earlier one"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp")


class RuleEvaluationRecord(BaseModel):
    """Persisted statutory rule evaluation record."""

    evaluation_id: str = Field(..., description="Unique evaluation ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    rule_id: str = Field(..., description="Statutory rule identifier")
    rule_version: str = Field(..., description="Rule version identifier")
    rule_name: str = Field(..., description="Rule name")
    statutory_reference: str = Field(..., description="Statutory clause reference")
    status: ComplianceVerdict = Field(
        ..., description="Verdict: PASS, FAIL, REVIEW_REQUIRED, NOT_ASSESSABLE"
    )
    observed_value: Optional[str] = Field(None, description="Observed value")
    expected_requirement: Optional[str] = Field(None, description="Expected requirement")
    explanation: str = Field(..., description="Deterministic reasoning")
    source_region: Optional[SourceRegion] = Field(None, description="Bounding box")
    evidence_reference: Optional[str] = Field(None, description="Evidence reference")
    evaluation_stage: str = Field(
        "initial", description="Evaluation stage: 'initial' or 'post_review'"
    )
    created_at: str = Field(..., description="ISO 8601 timestamp")


class ReviewActionRecord(BaseModel):
    """Persisted human reviewer action record."""

    review_id: str = Field(..., description="Unique review action ID")
    inspection_id: str = Field(..., description="Associated inspection ID")
    field_name: str = Field(..., description="Target declaration field name")
    action: ReviewAction = Field(..., description="Action: confirm, correct, mark_unassessable")
    original_value: Optional[str] = Field(None, description="Value prior to review")
    reviewed_value: Optional[str] = Field(None, description="Value after review")
    original_confidence: Optional[float] = Field(None, description="Initial AI confidence")
    source_region_before: Optional[SourceRegion] = Field(None, description="Prior bounding box")
    source_region_after: Optional[SourceRegion] = Field(None, description="Updated bounding box")
    reviewer_notes: Optional[str] = Field(None, description="Reviewer rationale")
    created_at: str = Field(..., description="ISO 8601 timestamp")


class AppendReviewRequest(BaseModel):
    """Payload to append review actions and re-evaluations to an existing inspection."""

    model_config = ConfigDict(extra="forbid")

    corrections: List[FieldCorrection] = Field(..., description="List of review actions")
    updated_extraction: ExtractionResult = Field(
        ..., description="ExtractionResult with reviewer resolutions"
    )
    new_compliance: InspectionResult = Field(
        ..., description="New InspectionResult produced by DeterministicRuleEngine"
    )
    provenance: Optional[Dict[str, FieldProvenance]] = Field(
        None, description="Provenance tracking"
    )


class FullInspectionTrailResponse(BaseModel):
    """Complete auditable decision trail reconstructing the entire inspection."""

    inspection: InspectionRecordSummary = Field(..., description="Inspection summary header")
    evidence: List[EvidenceRecord] = Field(default_factory=list, description="Evidence records")
    observations: List[ObservationRecord] = Field(
        default_factory=list, description="All observations (AI + reviewed)"
    )
    rule_evaluations: List[RuleEvaluationRecord] = Field(
        default_factory=list, description="All rule evaluations (initial + post_review)"
    )
    review_actions: List[ReviewActionRecord] = Field(
        default_factory=list, description="All human reviewer actions"
    )
    decision_trail_summary: str = Field(
        ..., description="Narrative summary reconstructing the evidence and decision path"
    )
