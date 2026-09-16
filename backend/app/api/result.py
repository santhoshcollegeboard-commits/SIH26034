"""Result and PDF Report API Router — /api/result

Exposes endpoints to retrieve structured inspection reports and downloadable PDF reports.
Strict presentation layer: reads from the Evidence Ledger without altering verdicts or invoking AI.
"""

import logging

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Response, status

from backend.app.schemas.result import InspectionResultReport
from backend.app.services.ledger_service import EvidenceLedgerService
from backend.app.services.report_service import PDFReportService
from backend.app.services.result_service import ResultService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/result", tags=["result"])


def get_result_service() -> ResultService:
    """Factory dependency returning the ResultService."""
    ledger_service = EvidenceLedgerService()
    return ResultService(ledger_service=ledger_service)


def get_report_service() -> PDFReportService:
    """Factory dependency returning the PDFReportService."""
    return PDFReportService()


@router.get(
    "/{inspection_id}",
    response_model=InspectionResultReport,
    summary="Retrieve structured inspection result report",
    description=(
        "Returns a complete report-ready representation of the inspection from the Evidence Ledger, "
        "including evidence details, declarations, rule evaluations, human review actions, "
        "traceability, and decision trail."
    ),
)
async def get_inspection_result(inspection_id: str) -> InspectionResultReport:
    """Retrieve structured report for an inspection."""
    result_service = get_result_service()
    try:
        return result_service.get_inspection_report(inspection_id)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found in Evidence Ledger.",
        )
    except Exception as e:
        logger.exception("Failed to retrieve inspection result report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve report: {str(e)}",
        )


@router.get(
    "/{inspection_id}/pdf",
    summary="Download or stream PDF inspection report",
    description=(
        "Generates and streams an official Legal Metrology inspection PDF report using ReportLab, "
        "derived strictly from persisted Evidence Ledger records."
    ),
    responses={
        200: {
            "content": {"application/pdf": {}},
            "description": "Binary PDF report stream.",
        },
        404: {"description": "Inspection not found."},
    },
)
async def get_inspection_pdf(inspection_id: str) -> Response:
    """Generate and return official PDF report for an inspection."""
    result_service = get_result_service()
    report_service = get_report_service()
    try:
        report = result_service.get_inspection_report(inspection_id)
        pdf_bytes = report_service.generate_report_pdf(report)
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Inspection '{inspection_id}' not found in Evidence Ledger.",
        )
    except Exception as e:
        logger.exception("Failed to generate PDF report: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate PDF report: {str(e)}",
        )

    safe_id = "".join(c for c in inspection_id if c.isalnum() or c in ("-", "_"))
    filename = f"PackCheck_{safe_id}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{filename}"',
            "Content-Length": str(len(pdf_bytes)),
        },
    )
