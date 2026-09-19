"""Product Evidence Image Lookup Service.

Dedicated, isolated service for resolving pre-prepared, single-image
packaged commodity evidence views from backend/data/evidence.json.

STRICT CONSTRAINTS:
- 100% Isolated from Legal Metrology statutory rule evaluators.
- Fully offline: zero external network calls or secondary AI model invocations.
- Exactly one comprehensive evidence image per product/GTIN.
- Safe fallback: returns None if GTIN is uncataloged or invalid; never crashes.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional, Union

from backend.app.schemas.evidence import ProductEvidenceRecord
from backend.app.services.barcode.validator import validate_gtin

logger = logging.getLogger(__name__)

# backend/app/services/evidence/service.py -> parents[3] is 'backend'
DEFAULT_EVIDENCE_PATH = Path(__file__).resolve().parents[3] / "data" / "evidence.json"


class ProductEvidenceService:
    """Service for resolving packaged commodity evidence image records."""

    def __init__(self, evidence_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize evidence lookup service.

        Args:
            evidence_path: Optional path to JSON evidence catalog file.
                           Defaults to backend/data/evidence.json.
        """
        self.evidence_path = Path(evidence_path) if evidence_path else DEFAULT_EVIDENCE_PATH
        self._catalog_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _load_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Load and parse the evidence catalog JSON file safely."""
        if not self.evidence_path.exists():
            logger.warning("Evidence catalog file not found at %s", self.evidence_path)
            return {}

        try:
            with open(self.evidence_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                logger.error("Evidence catalog JSON root must be a dictionary keyed by GTIN.")
                return {}
        except Exception as exc:
            logger.error("Failed to load evidence catalog from %s: %s", self.evidence_path, exc)
            return {}

    def get_catalog(self, reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """Retrieve all catalog entries, optionally reloading from disk."""
        if self._catalog_cache is None or reload:
            self._catalog_cache = self._load_catalog()
        return self._catalog_cache

    def get_evidence(self, gtin: str) -> Optional[ProductEvidenceRecord]:
        """Look up evidence record for a candidate GTIN.

        Args:
            gtin: GTIN string identified by barcode decoder or product verification.

        Returns:
            ProductEvidenceRecord if found in catalog with valid image, else None.
        """
        if not gtin or not isinstance(gtin, str):
            return None

        # Validate GTIN format and check digit
        val_res = validate_gtin(gtin)
        if not val_res.is_valid or not val_res.normalized_gtin:
            logger.debug("ProductEvidenceService: '%s' is not a valid GTIN; skipping evidence lookup.", gtin)
            return None

        clean_gtin = val_res.normalized_gtin
        catalog = self.get_catalog()
        item = catalog.get(clean_gtin)

        if not item or not isinstance(item, dict):
            logger.debug("ProductEvidenceService: GTIN %s has no evidence catalog entry.", clean_gtin)
            return None

        evidence_image = item.get("evidence_image")
        if not evidence_image or not isinstance(evidence_image, str):
            logger.warning("ProductEvidenceService: GTIN %s has no valid evidence_image configured.", clean_gtin)
            return None

        product_name = item.get("product_name")
        return ProductEvidenceRecord(
            gtin=clean_gtin,
            product_name=str(product_name).strip() if product_name else None,
            evidence_image=str(evidence_image).strip(),
        )


# =============================================================================
# Singleton Accessor
# =============================================================================

_evidence_service: Optional[ProductEvidenceService] = None


def get_evidence_service() -> ProductEvidenceService:
    """Retrieve or create the singleton ProductEvidenceService instance."""
    global _evidence_service
    if _evidence_service is None:
        _evidence_service = ProductEvidenceService()
    return _evidence_service


def set_evidence_service(service: Optional[ProductEvidenceService]) -> None:
    """Set or reset the singleton ProductEvidenceService instance (useful in tests)."""
    global _evidence_service
    _evidence_service = service
