"""Pydantic schemas and enums for GTIN product identity and OCR reconciliation.

Defines the structured output contract for GTIN Phase 2.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class FieldMatchStatus(str, Enum):
    """Evaluation status for an individual field comparison between OCR and GTIN."""

    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_COMPARABLE = "NOT_COMPARABLE"


class IdentityVerificationStatus(str, Enum):
    """Overall product identity verification verdict."""

    MATCH = "MATCH"
    PARTIAL_MATCH = "PARTIAL_MATCH"
    MISMATCH = "MISMATCH"
    NOT_VERIFIABLE = "NOT_VERIFIABLE"


class GTINLookupStatus(str, Enum):
    """Status of querying the authoritative GTIN registry/provider."""

    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    INVALID_GTIN = "INVALID_GTIN"
    AMBIGUOUS_GTIN = "AMBIGUOUS_GTIN"
    NO_GTIN_DETECTED = "NO_GTIN_DETECTED"


class GTINProductRecord(BaseModel):
    """Authoritative product data retrieved from a GS1/DataKart registry."""

    gtin: str = Field(..., description="Canonical 8, 12, 13, or 14-digit GTIN")
    brand_name: Optional[str] = Field(None, description="Registered brand name")
    product_name: Optional[str] = Field(None, description="Official product title / variant")
    product_description: Optional[str] = Field(None, description="Detailed product description")
    net_quantity: Optional[str] = Field(None, description="Net content numeric value")
    net_quantity_unit: Optional[str] = Field(None, description="Unit of measurement (g, kg, ml, etc.)")
    company_name: Optional[str] = Field(None, description="Registered manufacturer / brand owner")
    country_of_origin: Optional[str] = Field(None, description="Registered country of origin")
    source: str = Field("LOCAL_GS1_FIXTURE", description="Provider source identifier")


class FieldComparison(BaseModel):
    """Field-level comparison finding between OCR extracted declaration and GTIN record."""

    field_name: str = Field(..., description="Name of declaration field compared")
    ocr_value: Optional[str] = Field(None, description="Value read from packaging via OCR")
    gtin_value: Optional[str] = Field(None, description="Authoritative value from GTIN record")
    status: FieldMatchStatus = Field(..., description="Comparison outcome")
    message: str = Field(..., description="Explanatory notes on match / mismatch")


class GTINIdentityVerification(BaseModel):
    """Composite outcome of GTIN product lookup and OCR reconciliation."""

    gtin: Optional[str] = Field(None, description="GTIN evaluated for product identity")
    lookup_status: GTINLookupStatus = Field(..., description="Outcome of product registry query")
    product_record: Optional[GTINProductRecord] = Field(
        None, description="Authoritative product record if found"
    )
    overall_status: IdentityVerificationStatus = Field(
        ..., description="Aggregated identity verification verdict"
    )
    field_comparisons: List[FieldComparison] = Field(
        default_factory=list, description="Field-level comparison findings"
    )
    summary: str = Field(..., description="Narrative summary of GTIN identity reconciliation")
    provider_name: Optional[str] = Field(
        None, description="Active product identity provider identifier (e.g. 'Open Food Facts', 'GS1 / DataKart')"
    )
