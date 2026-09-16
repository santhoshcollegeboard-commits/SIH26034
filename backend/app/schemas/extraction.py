"""Pydantic schemas for Legal Metrology extraction results.

These schemas define the structured output contract between the OCR provider
and the rest of the PackCheck application. AI/OCR only extracts and proposes;
it does NOT decide compliance.
"""

from typing import Optional
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


from backend.app.schemas.common import SourceRegion


class ExtractedField(BaseModel):
    """A single extracted field from a packaged commodity label.

    status:
        'extracted' — value was successfully read from the image.
        'unreadable' — field region was found but value could not be read.
        'not_found' — field was not detected on the image at all.
    """

    value: Optional[str] = Field(
        None, description="Extracted text value, or null if unreadable/not found"
    )
    confidence: Optional[float] = Field(
        None, description="Confidence score 0.0–1.0, or null if not extracted"
    )
    source_region: Optional[SourceRegion] = Field(
        None, description="Bounding box where the field was detected, if available"
    )
    status: str = Field(
        "not_found",
        description="One of: 'extracted', 'unreadable', 'not_found'",
    )


class ExtractionResult(BaseModel):
    """Structured extraction of all mandatory Legal Metrology declarations.

    This is the output of the EXTRACT stage. It contains proposals only —
    no compliance judgments. The RuleEngine (CHECK stage) evaluates these later.
    """

    product_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_address: ExtractedField = Field(default_factory=ExtractedField)
    packer_name: ExtractedField = Field(default_factory=ExtractedField)
    importer_name: ExtractedField = Field(default_factory=ExtractedField)
    net_quantity: ExtractedField = Field(default_factory=ExtractedField)
    mrp: ExtractedField = Field(default_factory=ExtractedField)
    month_year_of_manufacture: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care_details: ExtractedField = Field(default_factory=ExtractedField)


from backend.app.schemas.compliance import InspectionResult
from backend.app.schemas.quality import QualityAssessment


class ExtractionResponse(BaseModel):
    """API response wrapper for the extraction endpoint."""

    success: bool = Field(..., description="Whether extraction completed without errors")
    result: Optional[ExtractionResult] = Field(
        None, description="Extracted fields, or null on error"
    )
    compliance: Optional[InspectionResult] = Field(
        None, description="Deterministic statutory compliance evaluation result, or null on error"
    )
    quality: Optional[QualityAssessment] = Field(
        None, description="Image quality assessment details from the pre-OCR quality gate"
    )
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    model_used: Optional[str] = Field(
        None, description="AI model identifier used for extraction"
    )
    processing_time_ms: Optional[int] = Field(
        None, description="Total processing time in milliseconds"
    )

