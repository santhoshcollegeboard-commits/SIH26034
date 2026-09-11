"""Verification API endpoint — POST /api/verify

Chains the PackCheck compliance pipeline:
IMAGE UPLOAD ──> AI/OCR EXTRACTION ──> DETERMINISTIC RULE ENGINE ──> COMPLIANCE RESULT

AI/OCR only extracts and proposes.
Deterministic rules decide compliance.
"""

import asyncio
import json
import logging
import time
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from backend.app.api.extract import ALLOWED_MIME_TYPES, MAX_UPLOAD_BYTES, get_ocr_provider
from backend.app.schemas.compliance import VerificationResponse
from backend.app.schemas.extraction import ExtractionResult
from backend.app.services.aggregation import MultiPanelAggregator
from backend.app.services.rules.engine import DeterministicRuleEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["verification"])

# Reusable rule engine instance
rule_engine = DeterministicRuleEngine()


@router.post("/verify", response_model=VerificationResponse)
async def verify_package(
    images: List[UploadFile] = File(
        default=[], description="Multiple packaged commodity images/panels"
    ),
    image: Optional[UploadFile] = File(
        default=None, description="Single packaged commodity image (backward compatibility)"
    ),
    panel_labels: List[str] = Form(
        default=[], description="Optional labels for uploaded panels (e.g. ['Front', 'Back'])"
    ),
):
    """Verify package compliance against Legal Metrology (Packaged Commodities) Rules.

    Supports single-image or multi-panel image verification.
    When multiple panels of the same product are uploaded:
    1. Each panel is processed concurrently via OCRProvider.
    2. MultiPanelAggregator consolidates declarations, tracks panel origins, and detects conflicts.
    3. DeterministicRuleEngine evaluates compliance once on the unified declarations.
    """
    # 1. Collect all uploaded files
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

    # 2. Validate all files
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

    start_time = time.monotonic()
    provider = get_ocr_provider()

    # 3. Concurrent Per-Image Extraction (AI/OCR Proposer stage)
    async def _safe_extract(img_bytes: bytes, mime: str) -> ExtractionResult:
        return await provider.extract(img_bytes, mime)

    tasks = [_safe_extract(data, mime) for data, mime, _ in validated_images]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    successful_extractions: List[ExtractionResult] = []
    successful_labels: List[str] = []
    failed_panels: List[str] = []

    for idx, res in enumerate(results):
        lbl = (
            parsed_labels[idx]
            if idx < len(parsed_labels)
            else f"Panel {idx + 1}"
        )
        if isinstance(res, Exception):
            logger.error("OCR error on %s: %s", lbl, res)
            failed_panels.append(f"{lbl}: {res}")
        elif isinstance(res, ExtractionResult):
            successful_extractions.append(res)
            successful_labels.append(lbl)

    # If all panels failed OCR, return provider error
    if not successful_extractions:
        first_err = str(results[0]) if results else "OCR failed on all panels."
        return VerificationResponse(
            success=False,
            extraction=None,
            compliance=None,
            error=f"OCR extraction failed on all submitted images: {first_err}",
            model_used=getattr(provider, "model_name", None),
            processing_time_ms=int((time.monotonic() - start_time) * 1000),
            image_count=len(uploaded_files),
            panel_labels=parsed_labels if parsed_labels else None,
        )

    # 4. Aggregate extractions across panels (MultiPanelAggregator)
    unified_extraction = MultiPanelAggregator.aggregate(
        extractions=successful_extractions,
        panel_labels=successful_labels,
    )

    # 5. Deterministic Statutory Rule Evaluation (Decider stage)
    package_metadata = {
        "num_images": len(uploaded_files),
        "panel_labels": successful_labels,
        "failed_panels": failed_panels,
    }
    compliance_result = await rule_engine.evaluate_compliance(
        package_metadata=package_metadata,
        extracted_declarations=unified_extraction,
    )

    # If any panel failed OCR but others succeeded, note it in compliance summary
    if failed_panels and compliance_result.summary:
        compliance_result.summary += (
            f" [Note: {len(failed_panels)} panel(s) could not be parsed: {', '.join(failed_panels)}]"
        )

    elapsed_ms = int((time.monotonic() - start_time) * 1000)

    return VerificationResponse(
        success=True,
        extraction=unified_extraction,
        compliance=compliance_result,
        error=None,
        model_used=getattr(provider, "model_name", None),
        processing_time_ms=elapsed_ms,
        image_count=len(uploaded_files),
        panel_labels=successful_labels,
        per_image_extractions=successful_extractions,
    )
