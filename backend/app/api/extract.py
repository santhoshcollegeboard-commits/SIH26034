"""Extraction API endpoint — POST /api/extract

Accepts a package image upload, performs OCR extraction via OCRProvider,
and deterministically evaluates statutory Legal Metrology compliance (Rule 6).
"""

import time
import logging
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.core.config import get_settings
from backend.app.schemas.compliance import ComplianceVerdict, InspectionResult
from backend.app.schemas.extraction import ExtractionResponse
from backend.app.schemas.quality import QualityAssessment
from backend.app.services.interfaces.ocr import OCRProvider
from backend.app.services.interfaces.quality import ImageQualityChecker
from backend.app.services.providers.gemini_provider import GeminiOCRProvider
from backend.app.services.quality_service import StandardImageQualityChecker
from backend.app.services.rule_engine_service import DeterministicRuleEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["extraction"])

# Supported image MIME types
ALLOWED_MIME_TYPES = {"image/jpeg", "image/png", "image/webp"}

# Maximum upload size in bytes (10 MB)
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def get_quality_checker() -> ImageQualityChecker:
    """Factory function returning the configured image quality checker."""
    return StandardImageQualityChecker()


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


def get_rule_engine() -> DeterministicRuleEngine:
    """Factory function returning the deterministic compliance rule engine."""
    return DeterministicRuleEngine()


@router.post("/extract", response_model=ExtractionResponse)
async def extract_fields(
    image: UploadFile = File(..., description="Package image (JPEG, PNG, or WEBP)"),
    is_imported: Optional[bool] = Form(None, description="Optional flag: whether package is imported"),
    is_packed_by_third_party: Optional[bool] = Form(None, description="Optional flag: whether packing is outsourced"),
):
    """Extract Legal Metrology declarations and evaluate Rule 6 statutory compliance.

    Workflow:
    1. AI/OCR Provider extracts raw declarations and assigns confidence scores (Proposals).
    2. DeterministicRuleEngine evaluates extracted fields against statutory criteria (Decision).
    3. Returns both extraction observations and auditable compliance verdicts.
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

    start_time = time.monotonic()

    # 1. Quality Gate: Evaluate image capture quality BEFORE calling OCR
    quality_checker = get_quality_checker()
    quality_dict = await quality_checker.assess_quality(image_data)
    quality_assessment = QualityAssessment(**quality_dict)

    if not quality_assessment.is_acceptable:
        reasons_text = (
            "; ".join(quality_assessment.reasons)
            if quality_assessment.reasons
            else "Image quality is insufficient for statutory inspection"
        )
        logger.warning("Quality gate rejected image: %s", reasons_text)
        elapsed_ms = int((time.monotonic() - start_time) * 1000)

        return ExtractionResponse(
            success=False,
            result=None,
            compliance=InspectionResult(
                overall_disposition=ComplianceVerdict.NOT_ASSESSABLE,
                summary=f"Quality gate rejected image: {reasons_text}. Image is not assessable under statutory rules; recapture required.",
                rule_evaluations=[],
            ),
            quality=quality_assessment,
            error=f"Image quality gate failed: {reasons_text}. Please recapture the package image under better lighting and focus.",
            model_used=None,
            processing_time_ms=elapsed_ms,
        )

    # 2. Get the provider through the factory (provider-independent)
    provider = get_ocr_provider()

    # 3. Extract fields via OCR provider
    try:
        extraction_result = await provider.extract(image_data, content_type)
    except ValueError as e:
        logger.error("Extraction parsing error: %s", e)
        return ExtractionResponse(
            success=False,
            result=None,
            compliance=None,
            quality=quality_assessment,
            error=f"Failed to parse extraction result: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )
    except RuntimeError as e:
        logger.error("Provider API error: %s", e)
        return ExtractionResponse(
            success=False,
            result=None,
            compliance=None,
            quality=quality_assessment,
            error=f"Provider error: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )

    # 4. Evaluate Rule 6 compliance deterministically
    rule_engine = get_rule_engine()
    package_metadata = {}
    if is_imported is not None:
        package_metadata["is_imported"] = is_imported
    if is_packed_by_third_party is not None:
        package_metadata["is_packed_by_third_party"] = is_packed_by_third_party

    try:
        compliance_result = await rule_engine.evaluate(
            extraction=extraction_result,
            package_metadata=package_metadata,
        )
    except Exception as e:
        logger.exception("Compliance evaluation unexpected failure: %s", e)
        return ExtractionResponse(
            success=False,
            result=extraction_result,
            compliance=None,
            quality=quality_assessment,
            error="Compliance evaluation failed due to an internal error.",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return ExtractionResponse(
        success=True,
        result=extraction_result,
        compliance=compliance_result,
        quality=quality_assessment,
        error=None,
        model_used=getattr(provider, "model_name", None),
        processing_time_ms=elapsed_ms,
    )
