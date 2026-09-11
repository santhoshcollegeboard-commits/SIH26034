"""Pydantic schemas for Legal Metrology compliance rule evaluation results.

These schemas define the structured output contract for the CHECK stage.
AI/OCR proposes extracted text; deterministic rules decide compliance.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from backend.app.schemas.extraction import ExtractionResult, SourceRegion


class RuleStatus(str, Enum):
    """Evaluation status for an individual Legal Metrology statutory rule."""

    PASS = "PASS"
    FAIL = "FAIL"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class RuleSeverity(str, Enum):
    """Statutory severity of non-compliance."""

    CRITICAL = "CRITICAL"
    MAJOR = "MAJOR"
    MINOR = "MINOR"


class OverallVerdict(str, Enum):
    """Aggregated compliance decision across all evaluated rules."""

    PASS = "PASS"
    FAIL = "FAIL"
    FLAGGED_FOR_REVIEW = "FLAGGED_FOR_REVIEW"


class RuleEvaluation(BaseModel):
    """The result of evaluating a single statutory Legal Metrology rule."""

    rule_id: str = Field(..., description="Unique rule identifier, e.g. 'LM-PC-06-1-E'")
    rule_reference: str = Field(
        ...,
        description="Official statutory section, e.g. 'Rule 6(1)(e), Legal Metrology (Packaged Commodities) Rules, 2011'",
    )
    rule_name: str = Field(..., description="Human-readable title of the rule")
    status: RuleStatus = Field(..., description="Evaluation outcome")
    severity: RuleSeverity = Field(
        default=RuleSeverity.MAJOR, description="Statutory severity"
    )
    message: str = Field(
        ..., description="Specific finding details explaining why the rule passed, failed, or was flagged"
    )
    extracted_value: Optional[str] = Field(
        None, description="Raw or parsed value read from the packaging label"
    )
    expected_condition: str = Field(
        ..., description="Legal requirement under Legal Metrology rules"
    )
    source_region: Optional[SourceRegion] = Field(
        None, description="Bounding box on the packaging image where the field was detected"
    )


class ComplianceResult(BaseModel):
    """The complete set of rule evaluations and the overall compliance verdict."""

    overall_verdict: OverallVerdict = Field(
        ..., description="Aggregate verdict: PASS, FAIL, or FLAGGED_FOR_REVIEW"
    )
    summary: str = Field(
        ..., description="High-level narrative summary of the compliance inspection"
    )
    evaluations: List[RuleEvaluation] = Field(
        default_factory=list, description="Per-rule evaluation records"
    )
    passed_count: int = Field(0, description="Number of rules evaluated as PASS")
    failed_count: int = Field(0, description="Number of rules evaluated as FAIL")
    review_count: int = Field(
        0, description="Number of rules evaluated as NOT_VERIFIABLE"
    )
    not_applicable_count: int = Field(
        0, description="Number of rules evaluated as NOT_APPLICABLE"
    )


class VerificationResponse(BaseModel):
    """Composite API response for POST /api/verify."""

    success: bool = Field(..., description="Whether verification completed successfully")
    extraction: Optional[ExtractionResult] = Field(
        None, description="Extracted label fields proposed by AI/OCR"
    )
    compliance: Optional[ComplianceResult] = Field(
        None, description="Deterministic rule engine compliance verdict"
    )
    error: Optional[str] = Field(None, description="Error message if processing failed")
    model_used: Optional[str] = Field(
        None, description="AI/OCR model identifier used in the extraction stage"
    )
    processing_time_ms: Optional[int] = Field(
        None, description="Total pipeline execution time in milliseconds"
    )
    image_count: Optional[int] = Field(
        None, description="Total number of package images/panels processed"
    )
    panel_labels: Optional[List[str]] = Field(
        None, description="Labels corresponding to processed panels (e.g., ['Front', 'Back'])"
    )
    per_image_extractions: Optional[List[ExtractionResult]] = Field(
        None, description="Individual extraction results for each processed panel"
    )
