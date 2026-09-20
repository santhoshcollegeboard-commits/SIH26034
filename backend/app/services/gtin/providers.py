"""Authoritative GTIN product identity providers.

Provides an abstract interface and a deterministic local fixture provider
for offline development and testing, along with an extensible stub for future
authenticated GS1 India DataKart API integration.
"""

from abc import ABC, abstractmethod
import logging
import re
import time
from typing import Any, Dict, Optional

import httpx

from backend.app.core.config import get_settings
from backend.app.core.logging import log_off_request
from backend.app.schemas.gtin_identity import GTINProductRecord
from backend.app.services.barcode.validator import validate_gtin

logger = logging.getLogger(__name__)


class GTINProvider(ABC):
    """Abstract interface for querying authoritative GTIN product repositories."""

    @abstractmethod
    async def get_product(self, gtin: str) -> Optional[GTINProductRecord]:
        """Fetch authoritative product details for a given GTIN.

        Args:
            gtin: Standard GTIN string (8, 12, 13, or 14 digits).

        Returns:
            GTINProductRecord if found, else None.
        """
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider service is configured and available."""
        pass


class LocalFixtureGTINProvider(GTINProvider):
    """Deterministic local in-memory GS1 product registry for development and testing.

    Pre-populated with benchmark FMCG product records matching project sample labels.
    Completely offline; zero network calls.
    """

    def __init__(self) -> None:
        self._registry: Dict[str, GTINProductRecord] = {}
        self._load_default_fixtures()

    def _load_default_fixtures(self) -> None:
        # 1. Assam Gold CTC Black Tea (Matches compliant tea sample)
        self._registry["8901030892011"] = GTINProductRecord(
            gtin="8901030892011",
            brand_name="Assam Gold",
            product_name="Assam Gold CTC Black Tea",
            product_description="Assam Gold Premium CTC Leaf Tea Estate Blend 500g",
            net_quantity="500",
            net_quantity_unit="g",
            company_name="Himalayan Highlands Tea Estates Pvt. Ltd.",
            country_of_origin="India",
            source="GS1_DATAKART_LOCAL_FIXTURE",
        )

        # 2. Parle-G 800g Glucose Biscuits (Real FMCG benchmark)
        self._registry["8901719101038"] = GTINProductRecord(
            gtin="8901719101038",
            brand_name="Parle-G",
            product_name="Glucose Biscuits",
            product_description="Parle-G Original Gluco Biscuits 800g",
            net_quantity="800",
            net_quantity_unit="g",
            company_name="Parle Products Pvt. Ltd.",
            country_of_origin="India",
            source="GS1_DATAKART_LOCAL_FIXTURE",
        )

        # 3. Benchmark Contradictory Product (for mismatch testing)
        self._registry["8901234567890"] = GTINProductRecord(
            gtin="8901234567890",
            brand_name="PureGreen",
            product_name="Organic Green Tea",
            product_description="PureGreen Whole Leaf Organic Green Tea 200g",
            net_quantity="200",
            net_quantity_unit="g",
            company_name="GreenLeaf Agro Enterprises Ltd.",
            country_of_origin="India",
            source="GS1_DATAKART_LOCAL_FIXTURE",
        )

    def add_fixture(self, record: GTINProductRecord) -> None:
        """Add or overwrite a test product record in the fixture registry."""
        self._registry[record.gtin.strip()] = record

    async def get_product(self, gtin: str) -> Optional[GTINProductRecord]:
        """Retrieve product record from the local fixture registry."""
        cleaned = gtin.strip() if gtin else ""
        return self._registry.get(cleaned)

    def is_available(self) -> bool:
        """Local fixture is always available."""
        return True


class DataKartAPIProvider(GTINProvider):
    """Client stub for official GS1 India DataKart API.

    Activates when official API credentials are provided in settings/env.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://api.gs1india.org/datakart/v1") -> None:
        self.api_key = api_key
        self.base_url = base_url

    def is_available(self) -> bool:
        """Available only if an API key is configured."""
        return bool(self.api_key)

    async def get_product(self, gtin: str) -> Optional[GTINProductRecord]:
        """Fetch product record from GS1 India DataKart API."""
        if not self.is_available():
            logger.info("DataKart API credentials not configured; falling back.")
            return None
        # In future enterprise integration:
        # make authenticated HTTP call via httpx
        logger.warning("DataKart API enterprise endpoint not yet connected.")
        return None


class OpenFoodFactsProvider(GTINProvider):
    """Secondary community-maintained product identity provider querying Open Food Facts API v3.

    Adheres strictly to authority and safety rules:
    - Attribution: Source is explicitly set to 'Open Food Facts'. Never labeled as GS1 or DataKart.
    - Query Pre-filter: Only queries using a valid GTIN-8, 12, 13, or 14 (verified via Modulo-10).
    - Sensible Timeout: 3.0s default to prevent hanging client requests.
    - Safe Network Handling: Network/timeout errors raise RuntimeError, which caller catches
      to emit GTINLookupStatus.SERVICE_UNAVAILABLE without breaking /api/verify.
    """

    DEFAULT_BASE_URL = "https://world.openfoodfacts.org"
    DEFAULT_TIMEOUT = 3.0
    DEFAULT_USER_AGENT = "PackCheck - Web - Version 0.1.0 - https://github.com/packcheck"
    QUERY_FIELDS = (
        "code,product_name,brands,quantity,product_quantity,product_quantity_unit,"
        "generic_name,brand_owner,origins"
    )

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        user_agent: Optional[str] = None,
        client: Optional[httpx.AsyncClient] = None,
    ) -> None:
        settings = get_settings()
        self.base_url = (base_url or getattr(settings, "OFF_API_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        self.timeout = timeout or getattr(settings, "OFF_TIMEOUT_SECONDS", self.DEFAULT_TIMEOUT)
        self.user_agent = user_agent or getattr(settings, "OFF_USER_AGENT", self.DEFAULT_USER_AGENT)
        self._client = client

    def is_available(self) -> bool:
        """Provider is configured and available."""
        return bool(self.base_url)

    async def get_product(self, gtin: str) -> Optional[GTINProductRecord]:
        """Fetch product record from Open Food Facts API v3 for a valid GTIN.

        Args:
            gtin: Candidate barcode string.

        Returns:
            GTINProductRecord if found in Open Food Facts, else None.

        Raises:
            RuntimeError: On network failure or timeout to allow reconciler to set SERVICE_UNAVAILABLE.
        """
        # 1. Guard: Only query using a valid GTIN (reject invalid or empty GTINs with zero network activity)
        val_res = validate_gtin(gtin)
        if not val_res.is_valid or not val_res.normalized_gtin:
            logger.debug("OpenFoodFactsProvider: '%s' is not a valid GTIN; skipping external lookup.", gtin)
            return None

        clean_gtin = val_res.normalized_gtin
        url = f"{self.base_url}/api/v3/product/{clean_gtin}.json"
        params = {"fields": self.QUERY_FIELDS}
        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        # 2. Make asynchronous HTTP request
        t0 = time.monotonic()
        try:
            if self._client:
                response = await self._client.get(url, params=params, headers=headers, timeout=self.timeout)
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, params=params, headers=headers)
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            log_off_request(gtin=clean_gtin, result="SERVICE_UNAVAILABLE", response_time_ms=elapsed_ms)
            logger.warning("Open Food Facts request failed for GTIN %s: %s", clean_gtin, exc)
            raise RuntimeError(f"Open Food Facts network/timeout error: {exc}") from exc
        except Exception as exc:
            elapsed_ms = int((time.monotonic() - t0) * 1000)
            log_off_request(gtin=clean_gtin, result="SERVICE_UNAVAILABLE", response_time_ms=elapsed_ms)
            logger.error("Unexpected error contacting Open Food Facts for GTIN %s: %s", clean_gtin, exc)
            raise RuntimeError(f"Open Food Facts request error: {exc}") from exc

        elapsed_ms = int((time.monotonic() - t0) * 1000)

        # 3. Handle HTTP status codes
        if response.status_code == 404:
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.info("Open Food Facts returned 404 Not Found for GTIN %s", clean_gtin)
            return None

        if response.status_code >= 500:
            log_off_request(gtin=clean_gtin, result="SERVICE_UNAVAILABLE", response_time_ms=elapsed_ms)
            logger.warning("Open Food Facts server error HTTP %s for GTIN %s", response.status_code, clean_gtin)
            raise RuntimeError(f"Open Food Facts server error HTTP {response.status_code}")

        if response.status_code != 200:
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.warning("Open Food Facts unexpected HTTP %s for GTIN %s", response.status_code, clean_gtin)
            return None

        # 4. Safe JSON decoding
        try:
            data = response.json()
        except Exception as exc:
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.warning("Open Food Facts returned unparseable JSON for GTIN %s: %s", clean_gtin, exc)
            return None

        if not isinstance(data, dict):
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.warning("Open Food Facts returned non-dict JSON for GTIN %s", clean_gtin)
            return None

        # 5. Check Open Food Facts status indicator
        # API v2: status == 1 (found), status == 0 (not found)
        # API v3: status == "success" / 1 (found), status == "failure" / 0 (not found)
        #         result.id == "product_found" or "product_not_found"
        status = data.get("status")
        result_obj = data.get("result") if isinstance(data.get("result"), dict) else {}
        result_id = result_obj.get("id")

        if status in (0, "0", "failure") or result_id == "product_not_found":
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.info(
                "Open Food Facts product not found for GTIN %s (status=%s, result_id=%s)",
                clean_gtin,
                status,
                result_id,
            )
            return None

        product = data.get("product")
        if not isinstance(product, dict) or not product:
            log_off_request(gtin=clean_gtin, result="NOT_FOUND", response_time_ms=elapsed_ms)
            logger.info("Open Food Facts payload missing product object for GTIN %s", clean_gtin)
            return None

        # 6. Map fields into standard GTINProductRecord
        log_off_request(gtin=clean_gtin, result="FOUND", response_time_ms=elapsed_ms)
        return self._map_to_product_record(clean_gtin, product)

    def _map_to_product_record(self, gtin: str, product: Dict[str, Any]) -> GTINProductRecord:
        """Map raw Open Food Facts product fields into standard GTINProductRecord."""
        # 1. Brand name
        brands_raw = product.get("brands") or product.get("brand_owner") or None
        brand_name = brands_raw.strip() if isinstance(brands_raw, str) and brands_raw.strip() else None

        # 2. Product name & description
        name_raw = product.get("product_name") or product.get("generic_name") or None
        product_name = name_raw.strip() if isinstance(name_raw, str) and name_raw.strip() else None

        desc_raw = product.get("generic_name") or product.get("product_name") or None
        product_description = desc_raw.strip() if isinstance(desc_raw, str) and desc_raw.strip() else None

        # 3. Net quantity and unit
        net_quantity = None
        net_quantity_unit = None

        pq_val = product.get("product_quantity")
        pq_unit = product.get("product_quantity_unit")
        if pq_val is not None and str(pq_val).strip():
            net_quantity = str(pq_val).strip()
            if pq_unit and str(pq_unit).strip():
                net_quantity_unit = str(pq_unit).strip()
        elif product.get("quantity"):
            qty_str = str(product["quantity"]).strip()
            m = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?$", qty_str)
            if m:
                net_quantity = m.group(1)
                net_quantity_unit = m.group(2) if m.group(2) else None
            else:
                net_quantity = qty_str
                net_quantity_unit = None

        # 4. Company / Manufacturer (strictly brand_owner; never use manufacturing_places)
        company_raw = product.get("brand_owner") or None
        company_name = company_raw.strip() if isinstance(company_raw, str) and company_raw.strip() else None

        # 5. Country of origin (strictly origins; countries represents market availability, not origin)
        country_raw = product.get("origins") or None
        country_of_origin = country_raw.strip() if isinstance(country_raw, str) and country_raw.strip() else None

        # Explicit Authority: STRICTLY 'Open Food Facts' (never GS1 or DataKart)
        return GTINProductRecord(
            gtin=gtin,
            brand_name=brand_name,
            product_name=product_name,
            product_description=product_description,
            net_quantity=net_quantity,
            net_quantity_unit=net_quantity_unit,
            company_name=company_name,
            country_of_origin=country_of_origin,
            source="Open Food Facts",
        )


# Global provider singleton
_gtin_provider: Optional[GTINProvider] = None


def get_gtin_provider() -> GTINProvider:
    """Dependency provider returning the active GTINProvider based on application configuration."""
    global _gtin_provider
    if _gtin_provider is not None:
        return _gtin_provider

    settings = get_settings()
    provider_name = getattr(settings, "GTIN_PROVIDER", "LOCAL_CATALOG").upper()
    if provider_name == "LOCAL_CATALOG":
        from backend.app.services.gtin.local_catalog_provider import LocalCatalogProvider
        _gtin_provider = LocalCatalogProvider()
    elif provider_name == "OPEN_FOOD_FACTS":
        _gtin_provider = OpenFoodFactsProvider(
            base_url=settings.OFF_API_BASE_URL,
            timeout=settings.OFF_TIMEOUT_SECONDS,
            user_agent=settings.OFF_USER_AGENT,
        )
    else:
        _gtin_provider = LocalFixtureGTINProvider()

    return _gtin_provider


def set_gtin_provider(provider: Optional[GTINProvider]) -> None:
    """Override the global provider instance (used for testing and mock injection)."""
    global _gtin_provider
    _gtin_provider = provider


# Expose LocalCatalogProvider for backward-compatible imports
def __getattr__(name: str) -> Any:
    if name == "LocalCatalogProvider":
        from backend.app.services.gtin.local_catalog_provider import LocalCatalogProvider
        return LocalCatalogProvider
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

