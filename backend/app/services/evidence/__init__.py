"""Product Evidence Service Package."""

from backend.app.services.evidence.service import (
    DEFAULT_EVIDENCE_PATH,
    ProductEvidenceService,
    get_evidence_service,
    set_evidence_service,
)

__all__ = [
    "DEFAULT_EVIDENCE_PATH",
    "ProductEvidenceService",
    "get_evidence_service",
    "set_evidence_service",
]
