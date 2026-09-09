"""Verification API endpoint — POST /api/verify

Chains the PackCheck compliance pipeline:
IMAGE UPLOAD ──> AI/OCR EXTRACTION ──> DETERMINISTIC RULE ENGINE ──> COMPLIANCE RESULT

AI/OCR only extracts and proposes.
Deterministic rules decide compliance.
"""

import logging
import time

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.app.api.extract import ALLOWED_MIME_TYPES, MAX_UPLOAD_BYTES, get_ocr_provider
from backend.app.schemas.compliance import VerificationResponse
from backend.app.services.rules.engine import DeterministicRuleEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["verification"])

# Reusable rule engine instance
rule_engine = DeterministicRuleEngine()


@router.post("/verify", response_model=VerificationResponse)
async def verify_package(
    image: UploadFile = File(..., description="Packaged commodity image (JPEG, PNG, or WEBP)")
):
    """Verify package compliance against Legal Metrology (Packaged Commodities) Rules.

    Executes:
    1. Visual feature and text extraction via OCRProvider (proposals only)
    2. Deterministic statutory evaluation via RuleEngine (compliance decisions)
    """
    # 1. Validate MIME type
    content_type = image.content_type or ""
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported image type: '{content_type}'. Accepted: JPEG, PNG, WEBP.",
        )

    # 2. Read and validate file size
    image_data = await image.read()
    if len(image_data) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    if len(image_data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Image too large ({len(image_data)} bytes). Maximum is {MAX_UPLOAD_BYTES} bytes (10 MB).",
        )

    # 3. Obtain OCR provider (provider-independent factory)
    provider = get_ocr_provider()

    start_time = time.monotonic()

    # 4. Extract declarations (AI/OCR Proposer stage)
    try:
        extraction_result = await provider.extract(image_data, content_type)
    except ValueError as e:
        logger.error("Extraction parsing error: %s", e)
        return VerificationResponse(
            success=False,
            extraction=None,
            compliance=None,
            error=f"Failed to parse label extraction: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )
    except RuntimeError as e:
        logger.error("Provider error during verification: %s", e)
        return VerificationResponse(
            success=False,
            extraction=None,
            compliance=None,
            error=f"OCR Provider error: {e}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
        )

    # 5. Deterministic Statutory Rule Evaluation (Decider stage)
    compliance_result = await rule_engine.evaluate_compliance(
        package_metadata={}, extracted_declarations=extraction_result
    )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return VerificationResponse(
        success=True,
        extraction=extraction_result,
        compliance=compliance_result,
        error=None,
        model_used=getattr(provider, "model_name", None),
        processing_time_ms=elapsed_ms,
    )
