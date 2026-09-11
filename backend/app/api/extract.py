import asyncio
import json
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.schemas.extraction import ExtractionResponse, ExtractionResult
from backend.app.services.aggregation import MultiPanelAggregator
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
async def extract_fields(
    images: List[UploadFile] = File(
        default=[], description="Multiple package images/panels (JPEG, PNG, or WEBP)"
    ),
    image: Optional[UploadFile] = File(
        default=None, description="Single package image (backward compatibility)"
    ),
    panel_labels: List[str] = Form(
        default=[], description="Optional labels for uploaded panels"
    ),
):
    """Extract Legal Metrology declaration fields from packaged commodity image(s).

    This endpoint performs EXTRACTION ONLY. It does not evaluate compliance.
    Supports single-image and multi-panel image requests.
    """
    uploaded_files: List[UploadFile] = []
    if images:
        uploaded_files.extend(images)
    if image:
        uploaded_files.append(image)

    if not uploaded_files:
        raise HTTPException(status_code=400, detail="No package image files uploaded.")

    if len(uploaded_files) > 10:
        raise HTTPException(
            status_code=400,
            detail=f"Too many images ({len(uploaded_files)}). Maximum allowed is 10 panels per package.",
        )

    # Parse panel labels if provided
    parsed_labels: List[str] = []
    if panel_labels:
        for item in panel_labels:
            item_str = str(item).strip()
            if item_str.startswith("[") and item_str.endswith("]"):
                try:
                    parsed_labels.extend(json.loads(item_str))
                except Exception:
                    parsed_labels.append(item_str)
            elif "," in item_str:
                parsed_labels.extend([p.strip() for p in item_str.split(",") if p.strip()])
            elif item_str:
                parsed_labels.append(item_str)

    validated_images: List[tuple[bytes, str, str]] = []
    for idx, f in enumerate(uploaded_files):
        content_type = f.content_type or ""
        if content_type not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported image type for file '{f.filename}': '{content_type}'. Accepted: JPEG, PNG, WEBP.",
            )

        data = await f.read()
        if len(data) == 0:
            raise HTTPException(
                status_code=400,
                detail=f"Uploaded file '{f.filename}' (panel #{idx + 1}) is empty.",
            )
        if len(data) > MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=400,
                detail=f"Image '{f.filename}' too large ({len(data)} bytes). Maximum is {MAX_UPLOAD_BYTES} bytes (10 MB).",
            )

        validated_images.append((data, content_type, f.filename or f"panel_{idx + 1}"))

    provider = get_ocr_provider()
    start_time = time.monotonic()

    async def _safe_extract(img_bytes: bytes, mime: str) -> ExtractionResult:
        return await provider.extract(img_bytes, mime)

    tasks = [_safe_extract(data, mime) for data, mime, _ in validated_images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_extractions: List[ExtractionResult] = []
    successful_labels: List[str] = []
    for idx, res in enumerate(results):
        lbl = (
            parsed_labels[idx]
            if idx < len(parsed_labels)
            else f"Panel {idx + 1}"
        )
        if isinstance(res, ExtractionResult):
            successful_extractions.append(res)
            successful_labels.append(lbl)
        else:
            logger.error("OCR error on panel %s: %s", lbl, res)

    if not successful_extractions:
        first_err = str(results[0]) if results else "OCR failed on all panels."
        return ExtractionResponse(
            success=False,
            result=None,
            error=f"OCR extraction failed: {first_err}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )

    unified_result = MultiPanelAggregator.aggregate(
        extractions=successful_extractions,
        panel_labels=successful_labels,
    )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return ExtractionResponse(
        success=True,
        result=unified_result,
        error=None,
        model_used=getattr(provider, "model_name", None),
        processing_time_ms=elapsed_ms,
    )
