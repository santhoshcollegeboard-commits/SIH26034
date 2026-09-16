"""Pydantic schemas for the REVIEW stage of Legal Metrology inspection.

These schemas define the contract for human inspector/reviewer interaction
when resolving evidence and observation uncertainty.

Architecture Axiom:
AI extracts/proposes -> deterministic rules decide -> human resolves uncertainty.
Reviewers resolve observation uncertainty; they do NOT directly set or force
statutory compliance verdicts.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import ComplianceVerdict, InspectionResult
from backend.app.schemas.extraction import ExtractionResult


class ReviewAction(str, Enum):
    """Actions an inspector can perform on an extracted field observation."""

    CONFIRM = "confirm"
    CORRECT = "correct"
    MARK_UNASSESSABLE = "mark_unassessable"


# Allowed field names on ExtractionResult that can be reviewed
ALLOWED_REVIEW_FIELDS = {
    "product_name",
    "manufacturer_name",
    "manufacturer_address",
    "packer_name",
    "importer_name",
    "net_quantity",
    "mrp",
    "month_year_of_manufacture",
    "consumer_care_details",
}


class FieldCorrection(BaseModel):
    """Structured human review action targeting a specific extracted field.

    CRITICAL SAFETY CONSTRAINT:
    This model forbids extra fields, preventing clients/reviewers from directly
    submitting compliance statuses (e.g. 'status', 'verdict', 'disposition').
    """

    model_config = ConfigDict(extra="forbid")

    field_name: str = Field(
        ...,
        description="Target declaration field name (e.g. 'net_quantity', 'mrp')",
    )
    action: ReviewAction = Field(
        ...,
        description="Reviewer action: 'confirm', 'correct', or 'mark_unassessable'",
    )
    corrected_value: Optional[str] = Field(
        None,
        description="Corrected text value; required if action is 'correct'",
    )
    source_region: Optional[SourceRegion] = Field(
        None,
        description="Updated or confirmed bounding box coordinates on source image",
    )
    reviewer_notes: Optional[str] = Field(
        None,
        description="Auditable human reviewer notes explaining the resolution",
    )

    @field_validator("field_name")
    @classmethod
    def validate_field_name(cls, v: str) -> str:
        if v not in ALLOWED_REVIEW_FIELDS:
            raise ValueError(
                f"Unknown field '{v}'. Allowed fields: {sorted(list(ALLOWED_REVIEW_FIELDS))}"
            )
        return v

    @field_validator("corrected_value")
    @classmethod
    def validate_corrected_value(cls, v: Optional[str], info: Any) -> Optional[str]:
        action = info.data.get("action")
        if action == ReviewAction.CORRECT:
            if v is None or not v.strip():
                raise ValueError("corrected_value cannot be empty when action is 'correct'")
        return v


class FieldProvenance(BaseModel):
    """Full auditable provenance distinguishing AI observation and human resolution."""

    field_name: str = Field(..., description="Target declaration field name")
    original_value: Optional[str] = Field(None, description="Original AI/OCR extracted value")
    original_confidence: Optional[float] = Field(None, description="Original AI confidence score")
    original_status: str = Field("not_found", description="Original extraction status")
    original_source_region: Optional[SourceRegion] = Field(None, description="Original bounding box")
    reviewed_value: Optional[str] = Field(None, description="Value after human review resolution")
    reviewed_status: str = Field("not_found", description="Field status after review")
    reviewed_source_region: Optional[SourceRegion] = Field(None, description="Bounding box after review")
    action_taken: str = Field(
        "unmodified",
        description="Action performed: 'confirmed', 'corrected', 'marked_unassessable', or 'unmodified'",
    )
    reviewer_notes: Optional[str] = Field(None, description="Reviewer rationale")
    reviewed_at: Optional[str] = Field(None, description="ISO timestamp of review resolution")


class ReviewItem(BaseModel):
    """Item requiring human inspection and resolution."""

    rule_id: str = Field(..., description="Statutory rule identifier (e.g. 'LMR-2011-R06-1-C')")
    rule_version: str = Field(..., description="Statutory rule version reference")
    rule_name: str = Field(..., description="Human-readable rule name")
    statutory_reference: str = Field(..., description="Legal source clause reference")
    rule_status: ComplianceVerdict = Field(
        ComplianceVerdict.REVIEW_REQUIRED,
        description="Evaluation status (must be REVIEW_REQUIRED)",
    )
    reason_for_review: str = Field(..., description="Deterministic reason human inspection is needed")
    field_name: Optional[str] = Field(None, description="Associated extracted field name if applicable")
    observed_value: Optional[Any] = Field(None, description="Value observed from extraction or evidence")
    confidence: Optional[float] = Field(None, description="AI extraction confidence score (0.0-1.0)")
    source_region: Optional[SourceRegion] = Field(
        None,
        description="Bounding box coordinates for highlighting evidence on original image",
    )
    what_to_verify: str = Field(..., description="Clear instructions on what the inspector needs to verify")


class ReviewItemsRequest(BaseModel):
    """Request to identify and fetch review-required items."""

    model_config = ConfigDict(extra="forbid")

    extraction: ExtractionResult = Field(..., description="Structured OCR extraction result")
    inspection: Optional[InspectionResult] = Field(
        None,
        description="Optional pre-existing inspection result; if omitted, rules will be evaluated",
    )
    package_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional package metadata (dimensions, flags, calibration)",
    )
    rules: Optional[List[int]] = Field(
        None,
        description="Optional list of rule numbers to evaluate (defaults to all active rules)",
    )


class ReviewItemsResponse(BaseModel):
    """Response containing surfaced review-required items."""

    review_items: List[ReviewItem] = Field(default_factory=list, description="Items needing review")
    total_items: int = Field(..., description="Total rule evaluations inspected")
    review_required_count: int = Field(..., description="Number of evaluations requiring human review")
    requires_human_review: bool = Field(..., description="True if any evaluation requires review")
    initial_disposition: ComplianceVerdict = Field(..., description="Current aggregate compliance disposition")


class ReviewSubmissionRequest(BaseModel):
    """Request payload submitting human reviewer resolutions.

    CRITICAL SAFETY CONSTRAINT:
    This model forbids extra fields, preventing clients from submitting any compliance
    verdict or status bypass. The deterministic rule engine decides all verdicts.
    """

    model_config = ConfigDict(extra="forbid")

    original_extraction: ExtractionResult = Field(
        ...,
        description="Initial AI extraction result (preserves original baseline)",
    )
    corrections: List[FieldCorrection] = Field(
        default_factory=list,
        description="List of human field confirmations, corrections, or unassessable flags",
    )
    package_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Optional updated package metadata (e.g. physical measurements, calibration)",
    )
    rules: Optional[List[int]] = Field(
        None,
        description="Optional list of rule numbers to re-evaluate (defaults to [6, 7, 8, 9])",
    )


class ReviewSubmissionResponse(BaseModel):
    """Response returned after human review resolutions are processed and re-evaluated."""

    success: bool = Field(..., description="Whether review resolution and re-evaluation succeeded")
    initial_disposition: ComplianceVerdict = Field(
        ...,
        description="Disposition prior to human review resolution",
    )
    final_disposition: ComplianceVerdict = Field(
        ...,
        description="New deterministic compliance disposition after re-evaluating reviewed observations",
    )
    compliance: InspectionResult = Field(
        ...,
        description="Deterministic statutory compliance results from the re-evaluation",
    )
    updated_extraction: ExtractionResult = Field(
        ...,
        description="Updated extraction observation state used for the deterministic re-evaluation",
    )
    provenance: Dict[str, FieldProvenance] = Field(
        ...,
        description="Complete provenance mapping preserving original AI observations and reviewer edits",
    )
    remaining_review_items: List[ReviewItem] = Field(
        default_factory=list,
        description="Any evaluations still requiring review after re-evaluation",
    )
    requires_further_review: bool = Field(
        ...,
        description="True if final disposition remains REVIEW_REQUIRED",
    )
    summary: str = Field(..., description="Narrative summary of review outcome and re-evaluation")
