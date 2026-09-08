"""Extraction API endpoint — POST /api/extract

Accepts a package image upload and returns structured field extraction.
The endpoint uses the OCRProvider abstraction; it does not call Gemini directly.
"""

import time
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.schemas.extraction import ExtractionResponse
from backend.app.services.interfaces.ocr import OCRProvider
from backend.app.services.providers.gemini_provider import GeminiOCRProvider

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["extraction"])

# Supported image MIME types
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Maximum upload size in bytes (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def get_ocr_provider() -> OCRProvider:
    """Factory function returning the configured OCR provider.

    Currently returns GeminiOCRProvider for Phase 1.
    Will be extended to support provider selection (Groq, local) later.
    """
    settings = get_settings()

    if not settings.GEMINI_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="GEMINI_API_KEY is not configured. Set it in the .env file.",
        )

    return GeminiOCRProvider(
        api_key=settings.GEMINI_API_KEY,
        model_name=settings.GEMINI_MODEL,
    )


@router.post("/extract", response_model=ExtractionResponse)
async def extract_fields(image: UploadFile = File(..., description="Package image (JPEG, PNG, or WEBP)")):
    """Extract Legal Metrology declaration fields from a packaged commodity image.

    This endpoint performs EXTRACTION ONLY. It does not evaluate compliance.
    The AI/OCR provider proposes field values; a separate RuleEngine decides compliance.
    """
    # Validate content type
    content_type = image.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: '{content_type}'. Accepted: JPEG, PNG, WEBP.",
        )

    # Read and validate file size
    image_data = await image.read()

    if len(image_data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(image_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({len(image_data)} bytes). Maximum is {MAX_UPLOAD_BYTES} bytes (10 MB).",
        )

    # Get the provider through the factory (provider-independent)
    provider = get_ocr_provider()

    # Extract fields
    start_time = time.monotonic()

    try:
        result = await provider.extract(image_data, content_type)
    except ValueError as e:
        logger.error("Extraction parsing error: %s", e)
        return ExtractionResponse(
            success=False,
            result=None,
            error=f"Failed to parse extraction result: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )
    except RuntimeError as e:
        logger.error("Provider API error: %s", e)
        return ExtractionResponse(
            success=False,
            result=None,
            error=f"Provider error: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return ExtractionResponse(
        success=True,
        result=result,
        error=None,
        model_used=getattr(provider, "model_name", None),
        processing_time_ms=elapsed_ms,
    )
