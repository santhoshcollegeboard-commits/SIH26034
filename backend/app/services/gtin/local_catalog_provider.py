"""Controlled local product catalog GTIN provider for prototype demonstrations.

Completely offline and deterministic. Loads curated product records from
a local JSON database (backend/data/products.json) created from physical package images.

STRICT CONSTRAINTS:
- Non-authoritative: NEVER labeled as GS1, DataKart, official registry, or government database.
- Zero network calls: Never queries Open Food Facts, GS1, or external websites.
- High fidelity: Only contains fields directly confirmed from physical package samples.
  Missing fields remain None; never fabricated.
"""

import json
import logging
from pathlib import Path
import re
from typing import Any, Dict, Optional, Union

from backend.app.core.config import get_settings
from backend.app.schemas.gtin_identity import GTINProductRecord
from backend.app.services.barcode.validator import validate_gtin
from backend.app.services.gtin.providers import GTINProvider

logger = logging.getLogger(__name__)

# backend/app/services/gtin/local_catalog_provider.py -> parents[3] is 'backend'
DEFAULT_CATALOG_PATH = Path(__file__).resolve().parents[3] / "data" / "products.json"


class LocalCatalogProvider(GTINProvider):
    """Controlled local product database provider for PackCheck prototype demonstrations.

    Provides deterministic, offline product identity lookups for products seeded
    from verified physical packaging images.
    """

    def __init__(self, catalog_path: Optional[Union[str, Path]] = None) -> None:
        """Initialize local catalog provider.

        Args:
            catalog_path: Optional path to JSON catalog file. Defaults to settings or backend/data/products.json.
        """
        if catalog_path:
            self.catalog_path = Path(catalog_path)
        else:
            settings = get_settings()
            config_path = getattr(settings, "LOCAL_CATALOG_PATH", None)
            if config_path:
                p = Path(config_path)
                if p.is_absolute():
                    self.catalog_path = p
                else:
                    # Resolve relative to project root (parents[4]) or backend (parents[3])
                    project_root = Path(__file__).resolve().parents[4]
                    candidate = project_root / config_path
                    if candidate.exists():
                        self.catalog_path = candidate
                    else:
                        self.catalog_path = DEFAULT_CATALOG_PATH
            else:
                self.catalog_path = DEFAULT_CATALOG_PATH

        self._catalog_cache: Optional[Dict[str, Dict[str, Any]]] = None

    def _load_catalog(self) -> Dict[str, Dict[str, Any]]:
        """Load and cache the products catalog from the JSON file."""
        if not self.catalog_path.exists():
            logger.warning("Local catalog file not found at %s", self.catalog_path)
            return {}

        try:
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    return data
                logger.error("Local catalog JSON root must be a dictionary keyed by GTIN.")
                return {}
        except Exception as exc:
            logger.error("Failed to load local product catalog from %s: %s", self.catalog_path, exc)
            return {}

    def get_catalog(self, reload: bool = False) -> Dict[str, Dict[str, Any]]:
        """Retrieve all catalog entries, optionally reloading from disk."""
        if self._catalog_cache is None or reload:
            self._catalog_cache = self._load_catalog()
        return self._catalog_cache

    def is_available(self) -> bool:
        """Local catalog provider is always available if file exists or is readable."""
        return True

    async def get_product(self, gtin: str) -> Optional[GTINProductRecord]:
        """Fetch product record from local catalog for a valid GTIN.

        Args:
            gtin: Candidate barcode string.

        Returns:
            GTINProductRecord if found in local catalog, else None.
        """
        # 1. Guard: Only query using a valid GTIN (reject invalid or empty GTINs)
        val_res = validate_gtin(gtin)
        if not val_res.is_valid or not val_res.normalized_gtin:
            logger.debug("LocalCatalogProvider: '%s' is not a valid GTIN; skipping catalog lookup.", gtin)
            return None

        clean_gtin = val_res.normalized_gtin
        catalog = self.get_catalog()

        item = catalog.get(clean_gtin)
        if not item or not isinstance(item, dict):
            logger.info("LocalCatalogProvider: GTIN %s not found in local prototype catalog.", clean_gtin)
            return None

        return self._map_to_product_record(clean_gtin, item)

    def _map_to_product_record(self, gtin: str, item: Dict[str, Any]) -> GTINProductRecord:
        """Map raw catalog record dictionary to standardized GTINProductRecord.

        Strictly preserves nulls; never fabricates unconfirmed packaging data.
        """
        # 1. Brand name
        brand_raw = item.get("brand") or item.get("brand_name")
        brand_name = brand_raw.strip() if isinstance(brand_raw, str) and brand_raw.strip() else None

        # 2. Product name & description
        product_name_raw = item.get("product_name")
        product_name = (
            product_name_raw.strip()
            if isinstance(product_name_raw, str) and product_name_raw.strip()
            else None
        )

        desc_raw = item.get("product_description") or item.get("common_or_generic_name")
        product_description = desc_raw.strip() if isinstance(desc_raw, str) and desc_raw.strip() else None

        # 3. Net quantity & unit
        net_quantity = None
        net_quantity_unit = None

        if "net_quantity" in item and item["net_quantity"] is not None:
            qty_val = str(item["net_quantity"]).strip()
            m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?$", qty_val)
            if m:
                net_quantity = m.group(1)
                net_quantity_unit = m.group(2) if m.group(2) else item.get("net_quantity_unit")
            else:
                net_quantity = qty_val
                net_quantity_unit = item.get("net_quantity_unit")

        if item.get("net_quantity_unit") and not net_quantity_unit:
            net_quantity_unit = str(item["net_quantity_unit"]).strip()

        # 4. Company / Manufacturer
        company_raw = (
            item.get("manufacturer_name")
            or item.get("company_name")
            or item.get("packer_name")
        )
        company_name = company_raw.strip() if isinstance(company_raw, str) and company_raw.strip() else None

        # 5. Country of origin (strictly as recorded; null if unconfirmed)
        country_raw = item.get("country_of_origin")
        country_of_origin = country_raw.strip() if isinstance(country_raw, str) and country_raw.strip() else None

        # 6. Source identifier
        source = item.get("source") or "PackCheck Controlled Prototype Catalog"

        return GTINProductRecord(
            gtin=gtin,
            brand_name=brand_name,
            product_name=product_name,
            product_description=product_description,
            net_quantity=net_quantity,
            net_quantity_unit=net_quantity_unit,
            company_name=company_name,
            country_of_origin=country_of_origin,
            source=source,
        )
