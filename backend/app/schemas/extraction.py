"""Pydantic schemas for Legal Metrology extraction results.

These schemas define the structured output contract between the OCR provider
and the rest of the PackCheck application. AI/OCR only extracts and proposes;
it does NOT decide compliance.
"""

from typing import Optional
from pydantic import BaseModel, Field


class SourceRegion(BaseModel):
    """Bounding box region on the source image where a field was detected."""

    x: float = Field(..., description="Left edge of the bounding box (normalized 0.0 to 1.0)")
    y: float = Field(..., description="Top edge of the bounding box (normalized 0.0 to 1.0)")
    width: float = Field(..., description="Width of the bounding box (normalized 0.0 to 1.0)")
    height: float = Field(..., description="Height of the bounding box (normalized 0.0 to 1.0)")
    image_index: Optional[int] = Field(
        None, description="Index of the source image in the submitted images list"
    )
    panel_label: Optional[str] = Field(
        None, description="Optional panel label, e.g. 'Front', 'Back', 'Side', 'Top', 'Bottom'"
    )


class CandidateField(BaseModel):
    """A candidate extracted value from a specific package panel."""

    value: Optional[str] = Field(None, description="Candidate text value")
    confidence: Optional[float] = Field(None, description="Extraction confidence")
    source_region: Optional[SourceRegion] = Field(None, description="Bounding box on panel")
    source_image_index: Optional[int] = Field(None, description="Source image index")
    source_panel_label: Optional[str] = Field(None, description="Source panel label")


class ExtractedField(BaseModel):
    """A single extracted field from a packaged commodity label.

    status:
        'extracted' — value was successfully read from the image.
        'unreadable' — field region was found but value could not be read.
        'not_found' — field was not detected on the image at all.
        'conflict' — multiple package panels proposed contradictory values.
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
        description="One of: 'extracted', 'unreadable', 'not_found', 'conflict'",
    )
    source_image_index: Optional[int] = Field(
        None, description="Index of the image panel where this field was extracted"
    )
    source_panel_label: Optional[str] = Field(
        None, description="Panel label where this field was extracted (e.g., 'Front', 'Back')"
    )
    all_candidates: Optional[list[CandidateField]] = Field(
        None, description="All competing candidates extracted across panels"
    )
    conflict_details: Optional[str] = Field(
        None, description="Explanatory text if conflicting declarations were detected across panels"
    )


class ExtractionResult(BaseModel):
    """Structured extraction of all mandatory Legal Metrology declarations.

    This is the output of the EXTRACT stage. It contains proposals only —
    no compliance judgments. The RuleEngine (CHECK stage) evaluates these later.
    """

    product_name: ExtractedField = Field(default_factory=ExtractedField)
    common_or_generic_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_name: ExtractedField = Field(default_factory=ExtractedField)
    manufacturer_address: ExtractedField = Field(default_factory=ExtractedField)
    packer_name: ExtractedField = Field(default_factory=ExtractedField)
    importer_name: ExtractedField = Field(default_factory=ExtractedField)
    country_of_origin: ExtractedField = Field(default_factory=ExtractedField)
    net_quantity: ExtractedField = Field(default_factory=ExtractedField)
    mrp: ExtractedField = Field(default_factory=ExtractedField)
    month_year_of_manufacture: ExtractedField = Field(default_factory=ExtractedField)
    consumer_care_details: ExtractedField = Field(default_factory=ExtractedField)


class ExtractionResponse(BaseModel):
    """API response wrapper for the extraction endpoint."""

    success: bool = Field(..., description="Whether extraction completed without errors")
    result: Optional[ExtractionResult] = Field(
        None, description="Extracted fields, or null on error"
    )
    error: Optional[str] = Field(None, description="Error message if extraction failed")
    model_used: Optional[str] = Field(
        None, description="AI model identifier used for extraction"
    )
    processing_time_ms: Optional[int] = Field(
        None, description="Total processing time in milliseconds"
    )
