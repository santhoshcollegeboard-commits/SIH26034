"""Common reusable schema primitives for PackCheck."""

# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field


class SourceRegion(BaseModel):
    """Bounding box region on the source image where a field was detected."""

    x: int = Field(..., description="Left edge of the bounding box in pixels")
    y: int = Field(..., description="Top edge of the bounding box in pixels")
    width: int = Field(..., description="Width of the bounding box in pixels")
    height: int = Field(..., description="Height of the bounding box in pixels")
