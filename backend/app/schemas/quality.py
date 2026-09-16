"""Pydantic schemas for image capture quality assessment.

These schemas define the contract for the QUALITY GATE stage of the PackCheck pipeline.
Images that fail the quality gate are rejected before any AI/OCR provider is called,
preventing wasted compute and avoiding hallucinated extractions from degraded imagery.
"""

from typing import Any, Dict, List, Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class QualityMetricDetail(BaseModel):
    """Evaluation metrics for an individual quality dimension."""

    passed: bool = Field(..., description="Whether this specific quality dimension passed")
    score: Optional[float] = Field(None, description="Observed numerical score (e.g. Laplacian variance or mean luminance)")
    threshold: Optional[Any] = Field(None, description="Statutory or operational threshold applied")
    message: Optional[str] = Field(None, description="Human-readable assessment message")


class QualityAssessment(BaseModel):
    """Aggregate result of the image capture quality gate evaluation."""

    is_acceptable: bool = Field(
        ...,
        description="True if the image meets all minimum quality requirements for OCR processing",
    )
    overall_score: float = Field(
        ...,
        description="Composite quality score from 0.0 (unusable) to 1.0 (optimal)",
    )
    reasons: List[str] = Field(
        default_factory=list,
        description="Specific rejection reasons explaining why the image is unacceptable",
    )
    details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed breakdown of per-dimension checks (resolution, sharpness, brightness, framing)",
    )
