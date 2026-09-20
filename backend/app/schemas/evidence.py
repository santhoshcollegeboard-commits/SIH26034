"""Pydantic schemas for product evidence image records.

Provides structured models for the dedicated, isolated product-evidence
image database and API responses.
"""

from typing import Optional
from pydantic import BaseModel, Field


class ProductEvidenceRecord(BaseModel):
    """Documented packaged commodity evidence image record."""

    gtin: str = Field(..., description="Standard GTIN identifier")
    product_name: Optional[str] = Field(None, description="Trade or common product name")
    evidence_image: str = Field(
        ..., description="Path or URL to the single comprehensive evidence image"
    )
