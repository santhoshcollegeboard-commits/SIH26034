"""GTIN product identity and OCR reconciliation service package."""

from backend.app.services.gtin.local_catalog_provider import LocalCatalogProvider
from backend.app.services.gtin.providers import (
    DataKartAPIProvider,
    GTINProvider,
    LocalFixtureGTINProvider,
    get_gtin_provider,
    set_gtin_provider,
)
from backend.app.services.gtin.reconciliation import (
    GTINReconciler,
    get_gtin_reconciler,
    parse_canonical_quantity,
)
from backend.app.services.gtin.selector import (
    GTINSelectionResult,
    select_gtin_candidate,
)

__all__ = [
    "GTINProvider",
    "LocalFixtureGTINProvider",
    "LocalCatalogProvider",
    "DataKartAPIProvider",
    "get_gtin_provider",
    "set_gtin_provider",
    "GTINReconciler",
    "get_gtin_reconciler",
    "parse_canonical_quantity",
    "GTINSelectionResult",
    "select_gtin_candidate",
]

