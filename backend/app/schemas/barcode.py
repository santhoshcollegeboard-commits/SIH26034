"""Pydantic schemas and enums for barcode detection and local GTIN validation.

Defines the structured output contract for GTIN Phase 1.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class BarcodeFormat(str, Enum):
    """Supported 1D and 2D barcode symbology formats."""

    EAN_13 = "EAN_13"
    EAN_8 = "EAN_8"
    UPC_A = "UPC_A"
    UPC_E = "UPC_E"
    CODE_128 = "CODE_128"
    ITF_14 = "ITF_14"
    ITF = "ITF"
    QR_CODE = "QR_CODE"
    DATA_MATRIX = "DATA_MATRIX"
    UNKNOWN = "UNKNOWN"


class GTINValidationStatus(str, Enum):
    """Evaluation status for local GTIN check-digit validation."""

    VALID = "VALID"
    INVALID_CHECK_DIGIT = "INVALID_CHECK_DIGIT"
    INVALID_LENGTH = "INVALID_LENGTH"
    NON_NUMERIC = "NON_NUMERIC"
    NOT_A_GTIN_FORMAT = "NOT_A_GTIN_FORMAT"
    EMPTY = "EMPTY"


class BarcodeDetectionStatus(str, Enum):
    """Aggregate barcode detection status for a package."""

    NO_BARCODE_DETECTED = "NO_BARCODE_DETECTED"
    BARCODE_DETECTED = "BARCODE_DETECTED"
    MULTIPLE_BARCODES_DETECTED = "MULTIPLE_BARCODES_DETECTED"
    DECODER_ERROR = "DECODER_ERROR"


class BarcodeItem(BaseModel):
    """A single barcode detected on a package image or panel."""

    raw_value: str = Field(
        ..., description="Raw text decoded from the barcode symbol"
    )
    format: BarcodeFormat = Field(
        ..., description="Detected barcode symbology format"
    )
    gtin: Optional[str] = Field(
        None, description="Normalized GTIN string if format is GTIN-compatible"
    )
    is_valid_gtin: bool = Field(
        False, description="True if local GTIN check digit is valid"
    )
    validation_status: GTINValidationStatus = Field(
        ..., description="Detailed status of GTIN check-digit validation"
    )
    validation_message: str = Field(
        ..., description="Explanatory text for the validation result"
    )
    position: Optional[str] = Field(
        None, description="Position coordinates reported by the barcode decoder"
    )
    panel_index: Optional[int] = Field(
        None, description="0-indexed panel index where this barcode was detected"
    )
    panel_label: Optional[str] = Field(
        None, description="Panel label where detected (e.g. 'Front', 'Back')"
    )


class BarcodeSummary(BaseModel):
    """Composite barcode detection and validation outcome across all submitted panels."""

    status: BarcodeDetectionStatus = Field(
        ..., description="Overall barcode detection outcome"
    )
    detected: bool = Field(
        False, description="Whether at least one barcode was successfully detected"
    )
    count: int = Field(
        0, description="Total count of detected barcodes across all panels"
    )
    barcodes: List[BarcodeItem] = Field(
        default_factory=list, description="All detected barcode items"
    )
    primary_gtin: Optional[str] = Field(
        None,
        description="Single primary GTIN if uniquely identified; null if multiple or none",
    )
    is_valid_gtin: Optional[bool] = Field(
        None,
        description="Validity of the primary GTIN; null if no primary GTIN is determined",
    )
    message: str = Field(
        ..., description="Human-readable summary of barcode detection outcome"
    )
