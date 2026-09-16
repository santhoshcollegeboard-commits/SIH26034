"""Review API endpoints — /api/review

Provides backend endpoints for human-in-the-loop review of Legal Metrology evidence.
Enables inspectors to identify review-required items with source regions and submit
structured corrections/confirmations for deterministic re-evaluation.

Architecture Axiom:
AI extracts/proposes -> deterministic rules decide -> human resolves uncertainty.
Reviewers resolve observation uncertainty; they do NOT directly set or force
statutory compliance verdicts.
"""

import logging
from typing import Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, status

from backend.app.schemas.review import (
    ReviewItemsRequest,
    ReviewItemsResponse,
    ReviewSubmissionRequest,
    ReviewSubmissionResponse,
)
from backend.app.services.review_service import ReviewService
from backend.app.services.rule_engine_service import DeterministicRuleEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/review", tags=["review"])


def get_review_service() -> ReviewService:
    """Factory dependency returning the ReviewService."""
    rule_engine = DeterministicRuleEngine()
    return ReviewService(rule_engine=rule_engine)


@router.post(
    "/items",
    response_model=ReviewItemsResponse,
    summary="Identify review-required rule evaluations",
    description=(
        "Exposes all evaluations where human review is required, including statutory references, "
        "reasons for uncertainty, extracted values, confidence scores, bounding box coordinates "
        "(source_region) for UI highlighting, and actionable reviewer instructions."
    ),
)
async def get_review_items(request: ReviewItemsRequest) -> ReviewItemsResponse:
    """Surface all items requiring human inspection and resolution."""
    try:
        service = get_review_service()
        response = await service.identify_review_items(
            extraction=request.extraction,
            inspection=request.inspection,
            package_metadata=request.package_metadata,
            rules=request.rules,
        )
        return response
    except Exception as e:
        logger.exception("Error identifying review items: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to identify review items: {str(e)}",
        )


@router.post(
    "/submit",
    response_model=ReviewSubmissionResponse,
    summary="Submit human review resolutions and re-evaluate deterministically",
    description=(
        "Accepts structured reviewer confirmations, corrections, or unassessable flags for "
        "extracted fields. Preserves full AI observation provenance alongside reviewer resolutions, "
        "and immediately re-evaluates the updated observations through the DeterministicRuleEngine. "
        "The reviewer CANNOT directly set or force a compliance verdict."
    ),
)
async def submit_review(request: ReviewSubmissionRequest) -> ReviewSubmissionResponse:
    """Submit human reviewer resolutions and obtain updated deterministic compliance verdicts."""
    try:
        service = get_review_service()
        response = await service.apply_review_and_evaluate(
            original_extraction=request.original_extraction,
            corrections=request.corrections,
            package_metadata=request.package_metadata,
            rules=request.rules,
        )
        return response
    except ValueError as e:
        logger.warning("Validation error in review submission: %s", e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Unexpected error in review submission: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Review processing and re-evaluation failed: {str(e)}",
        )
