"""Deterministic unit and integration tests for GTIN Phase 2B: Open Food Facts Provider.

Covers all required Phase 2B test scenarios:
1. Valid GTIN + OFF product found -> mapped to GTINProductRecord with source='Open Food Facts'
2. Valid GTIN + product not found (status='failure', status=0, or HTTP 404) -> None (NOT_FOUND)
3. OFF API timeout / network failure -> SERVICE_UNAVAILABLE
4. Malformed / unexpected API response -> handled safely without crashing
5. Product with missing optional fields -> mapped accurately, no invented values
6. Correct mapping of brand, product name, quantity, company, country
7. Deterministic OCR reconciliation using OFF product data -> MATCH / MISMATCH
8. OFF mismatch does not alter or force Legal Metrology verdict to FAIL
9. Invalid GTIN does not trigger external network lookup
10. Configuration-based provider selection (LOCAL_FIXTURE vs OPEN_FOOD_FACTS)
"""

import io
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import httpx
from PIL import Image
import zxingcpp

from backend.app.main import app
from backend.app.core.config import Settings
from backend.app.schemas.barcode import (
    BarcodeDetectionStatus,
    BarcodeFormat,
    BarcodeItem,
    BarcodeSummary,
    GTINValidationStatus,
)
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.schemas.gtin_identity import (
    FieldMatchStatus,
    GTINLookupStatus,
    GTINProductRecord,
    IdentityVerificationStatus,
)
from backend.app.services.gtin.providers import (
    LocalFixtureGTINProvider,
    OpenFoodFactsProvider,
    get_gtin_provider,
    set_gtin_provider,
)
from backend.app.services.gtin.reconciliation import (
    GTINReconciler,
    set_gtin_reconciler,
)


# =============================================================================
# Helpers & Fixtures
# =============================================================================

def _build_test_extraction(
    product_name: str = "Assam Gold CTC Black Tea",
    generic_name: str = "CTC Black Tea",
    brand: str = "Assam Gold",
    net_quantity: str = "500 g",
    mfg_name: str = "Himalayan Highlands Tea Estates Pvt. Ltd.",
) -> ExtractionResult:
    """Helper to build a mock ExtractionResult."""
    return ExtractionResult(
        product_name=ExtractedField(value=product_name, confidence=0.95),
        common_or_generic_name=ExtractedField(value=generic_name, confidence=0.95),
        brand_name=ExtractedField(value=brand, confidence=0.95),
        net_quantity=ExtractedField(value=net_quantity, confidence=0.95),
        manufacturer_name=ExtractedField(value=mfg_name, confidence=0.95),
        packer_name=ExtractedField(value=None, confidence=0.0),
        importer_name=ExtractedField(value=None, confidence=0.0),
        consumer_care_details=ExtractedField(
            value="Email: care@example.com, Phone: 1800-123-456", confidence=0.90
        ),
        country_of_origin=ExtractedField(value="India", confidence=0.95),
        mrp=ExtractedField(value="MRP ₹ 250.00 (inclusive of all taxes)", confidence=0.95),
        unit_sale_price=ExtractedField(value="₹ 0.50 / g", confidence=0.90),
        manufacturing_date=ExtractedField(value="08/2026", confidence=0.90),
        expiry_date=ExtractedField(value="08/2027", confidence=0.90),
        best_before_date=ExtractedField(value=None, confidence=0.0),
        sizes_or_dimensions=ExtractedField(value=None, confidence=0.0),
    )


def _build_barcode_summary(gtin: str) -> BarcodeSummary:
    """Helper to build a BarcodeSummary with a single GTIN barcode."""
    return BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        primary_gtin=gtin,
        is_valid_gtin=True,
        message=f"Single valid GTIN detected: {gtin}",
        barcodes=[
            BarcodeItem(
                raw_value=gtin,
                format=BarcodeFormat.EAN_13,
                panel_index=0,
                is_valid_gtin=True,
                gtin=gtin,
                validation_status=GTINValidationStatus.VALID,
                validation_message="Valid GTIN-13",
            )
        ],
    )


def _generate_barcode_png_bytes(content: str, barcode_format: zxingcpp.BarcodeFormat) -> bytes:
    """Generate in-memory PNG bytes of a valid barcode symbol."""
    bc = zxingcpp.create_barcode(content, barcode_format)
    zx_img = bc.to_image()
    pil_img = Image.frombytes("L", (zx_img.shape[1], zx_img.shape[0]), bytes(zx_img))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


@pytest.fixture(autouse=True)
def reset_gtin_provider_singleton():
    """Ensure the global GTIN provider and reconciler singletons are reset after each test."""
    set_gtin_provider(None)
    set_gtin_reconciler(None)
    yield
    set_gtin_provider(None)
    set_gtin_reconciler(None)


# =============================================================================
# 1. Product Lookup & Field Mapping Tests
# =============================================================================

@pytest.mark.asyncio
async def test_off_provider_valid_gtin_product_found():
    """Scenario 1: Valid GTIN with product in OFF returns mapped GTINProductRecord (API v3)."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "/api/v3/product/8901030892011.json" in str(request.url)
        assert "fields=" in str(request.url)
        assert request.headers["User-Agent"].startswith("PackCheck")
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": "success",
                "result": {"id": "product_found", "name": "Product found"},
                "product": {
                    "brands": "Assam Gold",
                    "product_name": "Assam Gold CTC Black Tea",
                    "generic_name": "Premium CTC Leaf Tea",
                    "product_quantity": "500",
                    "product_quantity_unit": "g",
                    "brand_owner": "Himalayan Highlands Tea Estates Pvt. Ltd.",
                    "origins": "India",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.gtin == "8901030892011"
    assert record.brand_name == "Assam Gold"
    assert record.product_name == "Assam Gold CTC Black Tea"
    assert record.product_description == "Premium CTC Leaf Tea"
    assert record.net_quantity == "500"
    assert record.net_quantity_unit == "g"
    assert record.company_name == "Himalayan Highlands Tea Estates Pvt. Ltd."
    assert record.country_of_origin == "India"
    assert record.source == "Open Food Facts"
    assert "GS1" not in record.source
    assert "DataKart" not in record.source


@pytest.mark.asyncio
async def test_off_provider_product_not_found_v3_status_failure():
    """Scenario 2A: Valid GTIN returning API v3 failure status and product_not_found returns None."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        assert "/api/v3/product/8901719101038.json" in str(request.url)
        return httpx.Response(
            200,
            json={
                "code": "8901719101038",
                "status": "failure",
                "result": {"id": "product_not_found", "name": "Product not found"},
                "errors": [{"message": "product not found"}],
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901719101038")

    assert record is None


@pytest.mark.asyncio
async def test_off_provider_product_not_found_status_zero():
    """Scenario 2B: Valid GTIN with status=0 in OFF (legacy v2 compatibility) returns None."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901719101038",
                "status": 0,
                "status_verbose": "product not found",
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901719101038")

    assert record is None


@pytest.mark.asyncio
async def test_off_provider_product_not_found_http_404():
    """Scenario 2C: Valid GTIN returning HTTP 404 returns None."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901719101038")

    assert record is None


# =============================================================================
# 2. Resilient Error & Network Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_off_provider_timeout_triggers_service_unavailable():
    """Scenario 3: Network timeout triggers SERVICE_UNAVAILABLE in reconciler."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Connection timed out after 3.0s")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        reconciler = GTINReconciler(provider=provider)

        barcode_summary = _build_barcode_summary("8901030892011")
        result = await reconciler.reconcile(barcode_summary, _build_test_extraction())

    assert result.lookup_status == GTINLookupStatus.SERVICE_UNAVAILABLE
    assert result.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE
    assert result.product_record is None
    assert "unavailable" in result.summary.lower()


@pytest.mark.asyncio
async def test_off_provider_network_error_triggers_service_unavailable():
    """Scenario 3B: Network connection error triggers SERVICE_UNAVAILABLE in reconciler."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        raise httpx.NetworkError("Name resolution failure: world.openfoodfacts.org")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        reconciler = GTINReconciler(provider=provider)

        barcode_summary = _build_barcode_summary("8901030892011")
        result = await reconciler.reconcile(barcode_summary, _build_test_extraction())

    assert result.lookup_status == GTINLookupStatus.SERVICE_UNAVAILABLE
    assert result.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE


@pytest.mark.asyncio
async def test_off_provider_malformed_json_handled_safely():
    """Scenario 4: Malformed/non-JSON API response handled gracefully without crashing."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<html><body>502 Bad Gateway</body></html>")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is None


# =============================================================================
# 3. Field Mapping & Normalization Edge Cases
# =============================================================================

@pytest.mark.asyncio
async def test_off_provider_missing_optional_fields_no_invented_values():
    """Scenario 5: Product with sparse/missing fields leaves missing values as None."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Simple Biscuits",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.product_name == "Simple Biscuits"
    assert record.brand_name is None
    assert record.net_quantity is None
    assert record.net_quantity_unit is None
    assert record.company_name is None
    assert record.country_of_origin is None
    assert record.source == "Open Food Facts"


@pytest.mark.asyncio
async def test_off_provider_never_uses_manufacturing_places_as_fallback():
    """Verify that manufacturing_places is NEVER used as a fallback for company_name."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Assam Tea",
                    "manufacturing_places": "Factory 4, Okhla Industrial Area, New Delhi",
                    # brand_owner is intentionally omitted
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.company_name is None  # Must remain None when brand_owner is unavailable!


@pytest.mark.asyncio
async def test_off_provider_populates_company_name_from_brand_owner():
    """Verify that company_name is populated strictly from brand_owner."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Assam Tea",
                    "brand_owner": "Himalayan Highlands Tea Estates Pvt. Ltd.",
                    "manufacturing_places": "Ignored Plant Location",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.company_name == "Himalayan Highlands Tea Estates Pvt. Ltd."


@pytest.mark.asyncio
async def test_off_provider_does_not_map_countries_to_country_of_origin():
    """Verify that the 'countries' field (market availability) is NEVER mapped to country_of_origin."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Assam Tea",
                    "countries": "India, France, Germany, United Kingdom",
                    # origins is intentionally omitted
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.country_of_origin is None  # Must remain None; countries represents sale market, not origin!


@pytest.mark.asyncio
async def test_off_provider_populates_country_of_origin_from_origins():
    """Verify that country_of_origin is populated strictly from origins."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Assam Tea",
                    "origins": "India",
                    "countries": "France, Germany",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901030892011")

    assert record is not None
    assert record.country_of_origin == "India"


@pytest.mark.asyncio
async def test_off_provider_quantity_string_fallback():
    """Scenario 6: Quantity parsed cleanly from 'quantity' string when product_quantity is absent."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901719101038",
                "status": 1,
                "product": {
                    "product_name": "Glucose Biscuits",
                    "brands": "Parle-G",
                    "quantity": "800 g",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        record = await provider.get_product("8901719101038")

    assert record is not None
    assert record.net_quantity == "800"
    assert record.net_quantity_unit == "g"


@pytest.mark.asyncio
async def test_off_provider_invalid_gtin_skips_external_lookup():
    """Scenario 9: Invalid GTIN does NOT trigger an external HTTP request."""
    call_count = 0

    def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        # Invalid check digit
        rec1 = await provider.get_product("8901030892010")
        # Non-numeric
        rec2 = await provider.get_product("ABC123456789")
        # Invalid length
        rec3 = await provider.get_product("12345")

    assert rec1 is None
    assert rec2 is None
    assert rec3 is None
    assert call_count == 0  # Zero network requests triggered!


# =============================================================================
# 4. OCR Reconciliation with Open Food Facts
# =============================================================================

@pytest.mark.asyncio
async def test_reconciler_with_off_provider_match():
    """Scenario 7A: Reconciler with Open Food Facts produces MATCH when declarations agree."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Assam Gold CTC Black Tea",
                    "brands": "Assam Gold",
                    "product_quantity": "500",
                    "product_quantity_unit": "g",
                    "brand_owner": "Himalayan Highlands Tea Estates Pvt. Ltd.",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        reconciler = GTINReconciler(provider=provider)

        barcode_summary = _build_barcode_summary("8901030892011")
        extraction = _build_test_extraction(
            product_name="Assam Gold CTC Black Tea",
            brand="Assam Gold",
            net_quantity="500 g",
        )
        result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.overall_status == IdentityVerificationStatus.MATCH
    assert result.lookup_status == GTINLookupStatus.FOUND
    assert result.product_record.source == "Open Food Facts"
    assert "Open Food Facts product record" in result.summary


@pytest.mark.asyncio
async def test_reconciler_with_off_provider_mismatch():
    """Scenario 7B: Reconciler with Open Food Facts produces MISMATCH without alarmist words."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "PureGreen Organic Green Tea",
                    "brands": "PureGreen",
                    "product_quantity": "200",
                    "product_quantity_unit": "g",
                    "brand_owner": "GreenLeaf Agro Enterprises Ltd.",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        reconciler = GTINReconciler(provider=provider)

        barcode_summary = _build_barcode_summary("8901030892011")
        extraction = _build_test_extraction(
            product_name="Assam Gold CTC Black Tea",
            brand="Assam Gold",
            net_quantity="500 g",
        )
        result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.overall_status == IdentityVerificationStatus.MISMATCH
    assert result.lookup_status == GTINLookupStatus.FOUND
    assert "conflict with Open Food Facts product record" in result.summary

    # Ensure strictly zero alarmist terms
    alarmist_words = ["counterfeit", "fake", "illegal", "forged"]
    for word in alarmist_words:
        assert word not in result.summary.lower()
        for c in result.field_comparisons:
            assert word not in c.message.lower()


@pytest.mark.asyncio
async def test_reconciler_with_off_provider_not_found_wording():
    """Verify reconciler NOT_FOUND summary wording and provider_name when OFF is active."""
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, text="Not Found")

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        provider = OpenFoodFactsProvider(client=client)
        reconciler = GTINReconciler(provider=provider)

        barcode_summary = _build_barcode_summary("8901030892011")
        result = await reconciler.reconcile(barcode_summary, _build_test_extraction())

    assert result.lookup_status == GTINLookupStatus.NOT_FOUND
    assert result.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE
    assert result.provider_name == "Open Food Facts"
    assert result.summary == (
        "GTIN 8901030892011 was not found in Open Food Facts. "
        "Product identity could not be verified against the available product database."
    )
    # Ensure forbidden words are strictly not present
    for forbidden in ["authoritative", "gs1", "datakart", "official registry"]:
        assert forbidden not in result.summary.lower()



# =============================================================================
# 5. Full Pipeline & Legal Metrology Decoupling
# =============================================================================

def test_api_verify_off_mismatch_does_not_alter_legal_metrology():
    """Scenario 8: OFF MISMATCH does NOT alter or fail Legal Metrology verdict."""
    client = TestClient(app)
    png_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)

    # OFF returns conflicting product data
    def mock_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "code": "8901030892011",
                "status": 1,
                "product": {
                    "product_name": "Conflicting Brand Coffee",
                    "brands": "WrongBrand",
                    "product_quantity": "100",
                    "product_quantity_unit": "g",
                },
            },
        )

    transport = httpx.MockTransport(mock_handler)
    mock_http_client = httpx.AsyncClient(transport=transport)
    off_provider = OpenFoodFactsProvider(client=mock_http_client)
    set_gtin_provider(off_provider)

    mock_extraction = _build_test_extraction(
        product_name="Assam Gold CTC Black Tea",
        net_quantity="500 g",
        mfg_name="Himalayan Highlands Tea Estates Pvt. Ltd.",
    )

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_ocr = AsyncMock()
        mock_ocr.extract = AsyncMock(return_value=mock_extraction)
        mock_ocr.model_name = "test-mock-ocr"
        mock_get_provider.return_value = mock_ocr

        response = client.post(
            "/api/verify",
            files=[("images", ("panel.png", png_bytes, "image/png"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # GTIN layer registers MISMATCH from Open Food Facts
    gtin_id = data.get("gtin_identity")
    assert gtin_id is not None
    assert gtin_id["overall_status"] == "MISMATCH"
    assert gtin_id["product_record"]["source"] == "Open Food Facts"

    # Legal Metrology verdict is independent and NOT failed by GTIN mismatch!
    compliance = data.get("compliance")
    assert compliance is not None
    assert compliance["overall_verdict"] in ["PASS", "FLAGGED_FOR_REVIEW"]


# =============================================================================
# 6. Configuration-Based Provider Selection
# =============================================================================

def test_provider_selection_via_configuration():
    """Scenario 10: Provider factory chooses provider based on Settings."""
    # Reset any cached provider
    set_gtin_provider(None)

    # 1. When GTIN_PROVIDER is LOCAL_FIXTURE
    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="LOCAL_FIXTURE")
        set_gtin_provider(None)
        p1 = get_gtin_provider()
        assert isinstance(p1, LocalFixtureGTINProvider)

    # 2. When GTIN_PROVIDER is OPEN_FOOD_FACTS
    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="OPEN_FOOD_FACTS")
        set_gtin_provider(None)
        p2 = get_gtin_provider()
        assert isinstance(p2, OpenFoodFactsProvider)
        assert p2.base_url == "https://world.openfoodfacts.org"
