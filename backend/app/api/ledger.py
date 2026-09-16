"""Evidence Ledger API Router — /api/ledger

Provides REST endpoints to persist inspections and retrieve complete auditable decision trails.
"""

import logging
from typing import List, Optional

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Query, status

from backend.app.schemas.ledger import (
    AppendReviewRequest,
    CreateInspectionRecordRequest,
    FullInspectionTrailResponse,
    InspectionRecordSummary,
)
from backend.app.services.ledger_service import EvidenceLedgerService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ledger", tags=["ledger"])


def get_ledger_service() -> EvidenceLedgerService:
    """Factory dependency returning the EvidenceLedgerService singleton/instance."""
    return EvidenceLedgerService()


@router.post(
    "/inspections",
    response_model=FullInspectionTrailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record an inspection in the Evidence Ledger",
    description="Atomically stores image evidence, extracted declarations, and statutory evaluations.",
)
async def create_inspection_record(
    request: CreateInspectionRecordRequest,
) -> FullInspectionTrailResponse:
    """Record an inspection and return its complete decision trail."""
    try:
        service = get_ledger_service()
        inspection_id = service.record_inspection(request)
        return service.get_inspection(inspection_id)
    except Exception as e:
        logger.exception("Failed to record inspection in Evidence Ledger: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record inspection: {str(e)}",
        )


@router.get(
    "/inspections/{inspection_id}",
    response_model=FullInspectionTrailResponse,
    summary="Retrieve an inspection and its complete decision trail",
    description="Reconstructs the full auditable path: Evidence -> Observations -> Evaluations -> Review -> Final Disposition.",
)
async def get_inspection_trail(inspection_id: str) -> FullInspectionTrailResponse:
    """Fetch complete auditable decision trail for an inspection."""
    service = get_ledger_service()
    try:
        return service.get_inspection(inspection_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found in Evidence Ledger.",
        )
    except Exception as e:
        logger.exception("Error retrieving inspection '%s': %s", inspection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve inspection trail: {str(e)}",
        )


@router.post(
    "/inspections/{inspection_id}/review",
    response_model=FullInspectionTrailResponse,
    summary="Append human reviewer actions to an existing inspection",
    description="Appends reviewer corrections and post-review rule evaluations without overwriting historical AI observations.",
)
async def append_review_to_inspection(
    inspection_id: str,
    request: AppendReviewRequest,
) -> FullInspectionTrailResponse:
    """Record human review actions and post-review re-evaluations for an inspection."""
    service = get_ledger_service()
    try:
        return service.record_review_resolution(inspection_id, request)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found in Evidence Ledger.",
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.exception("Error appending review to inspection '%s': %s", inspection_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to append review resolution: {str(e)}",
        )


@router.get(
    "/inspections",
    response_model=List[InspectionRecordSummary],
    summary="List recorded inspections",
    description="Lists summary headers for recorded inspections in reverse chronological order.",
)
async def list_inspections(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[InspectionRecordSummary]:
    """List recorded inspection summaries."""
    service = get_ledger_service()
    try:
        return service.list_inspections(limit=limit, offset=offset)
    except Exception as e:
        logger.exception("Error listing inspections: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list inspections: {str(e)}",
        )
