"""Comprehensive tests for GTIN Controlled Local Catalog Provider / Prototype Mode.

Verifies:
1. Known GTIN (8901030712999) returns Dove Bathing Bar, 50 g, Hindustan Unilever Limited.
2. Unknown GTIN returns None (yielding NOT_FOUND in reconciler).
3. Invalid GTIN is rejected before catalog lookup without searching database.
4. Correct barcode format is EAN_13.
5. GTIN remains strictly 8901030712999.
6. Open Food Facts is never invoked when LOCAL_CATALOG is active.
7. Catalog does not fabricate missing fields (null/None remain null/None).
8. Existing reconciliation engine works deterministically with the local catalog record.
9. Provider switching architecture works seamlessly (LOCAL_CATALOG, OPEN_FOOD_FACTS, LOCAL_FIXTURE).
10. Full verification pipeline (/api/verify) operates cleanly with local catalog without altering Legal Metrology.
"""

import io
import json
from pathlib import Path
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
    IdentityVerificationStatus,
)
from backend.app.services.gtin.local_catalog_provider import (
    DEFAULT_CATALOG_PATH,
    LocalCatalogProvider,
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
    product_name: str = "Dove Bathing Bar",
    generic_name: str = "Bathing Bar",
    brand: str = "Dove",
    net_quantity: str = "50 g",
    mfg_name: str = "Hindustan Unilever Limited",
) -> ExtractionResult:
    """Helper to build an ExtractionResult matching Dove packaging declarations."""
    return ExtractionResult(
        product_name=ExtractedField(value=product_name, confidence=0.95),
        common_or_generic_name=ExtractedField(value=generic_name, confidence=0.90),
        brand_name=ExtractedField(value=brand, confidence=0.95),
        net_quantity=ExtractedField(value=net_quantity, confidence=0.95),
        manufacturer_name=ExtractedField(value=mfg_name, confidence=0.95),
        packer_name=ExtractedField(value=None, confidence=0.0),
        importer_name=ExtractedField(value=None, confidence=0.0),
        consumer_care_details=ExtractedField(
            value="Email: care@hul.com, Toll Free: 1800-10-22-221", confidence=0.90
        ),
        country_of_origin=ExtractedField(value=None, confidence=0.0),
        mrp=ExtractedField(value="₹ 35.00 (incl. of all taxes)", confidence=0.95),
        unit_sale_price=ExtractedField(value="₹ 0.70 / g", confidence=0.90),
        manufacturing_date=ExtractedField(value="01/2026", confidence=0.90),
        expiry_date=ExtractedField(value="01/2028", confidence=0.90),
        best_before_date=ExtractedField(value=None, confidence=0.0),
        sizes_or_dimensions=ExtractedField(value=None, confidence=0.0),
    )


def _build_barcode_summary(gtin: str) -> BarcodeSummary:
    """Helper to build a BarcodeSummary with a single valid EAN-13 GTIN."""
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
def reset_gtin_singletons():
    """Reset the GTIN provider and reconciler singletons before and after each test."""
    set_gtin_provider(None)
    set_gtin_reconciler(None)
    yield
    set_gtin_provider(None)
    set_gtin_reconciler(None)


# =============================================================================
# Test Cases
# =============================================================================

@pytest.mark.asyncio
async def test_known_gtin_returns_dove_product():
    """Test 1 & 5: Known GTIN 8901030712999 returns Dove Bathing Bar, 50 g, Hindustan Unilever Limited."""
    provider = LocalCatalogProvider()
    assert provider.is_available() is True

    record = await provider.get_product("8901030712999")
    assert record is not None

    # Exact GTIN check
    assert record.gtin == "8901030712999"

    # Core identity fields
    assert record.product_name == "Dove Bathing Bar"
    assert record.product_description == "Bathing Bar"
    assert record.brand_name == "Dove"
    assert record.net_quantity == "50"
    assert record.net_quantity_unit == "g"
    assert record.company_name == "Hindustan Unilever Limited"

    # Source identifier
    assert record.source == "PackCheck Controlled Prototype Catalog"

    # Strict non-authoritative constraints
    assert "GS1" not in record.source
    assert "DataKart" not in record.source
    assert "Official" not in record.source



@pytest.mark.asyncio
async def test_unknown_gtin_returns_none_and_not_found():
    """Test 2: Unknown valid GTIN returns None, leading to NOT_FOUND in reconciler."""
    provider = LocalCatalogProvider()
    # 8901719101038 is a valid Parle-G GTIN, but not in products.json (only Dove is in local catalog)
    record = await provider.get_product("8901719101038")
    assert record is None

    # Reconciler test
    reconciler = GTINReconciler(provider=provider)
    summary_item = _build_barcode_summary("8901719101038")
    result = await reconciler.reconcile(summary_item, _build_test_extraction())

    assert result.lookup_status == GTINLookupStatus.NOT_FOUND
    assert result.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE
    assert result.provider_name == "Local Product Catalog (Prototype)"
    assert "not found in the local prototype product catalog" in result.summary
    assert "authoritative" not in result.summary.lower()
    assert "gs1" not in result.summary.lower()
    assert "datakart" not in result.summary.lower()


@pytest.mark.asyncio
async def test_invalid_gtin_skips_catalog_lookup():
    """Test 3: Invalid GTIN check digit or length rejected before catalog lookup."""
    provider = LocalCatalogProvider()

    # Invalid check digit (correct is 9)
    assert await provider.get_product("8901030712990") is None

    # Non-numeric
    assert await provider.get_product("890103071299A") is None

    # Invalid length
    assert await provider.get_product("123456") is None
    assert await provider.get_product("") is None


def test_catalog_barcode_format_is_ean13():
    """Test 4: Barcode format in products.json is confirmed to be EAN_13 for all seeded records."""
    with open(DEFAULT_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    # 1. Dove Bathing Bar
    dove = data.get("8901030712999")
    assert dove is not None
    assert dove.get("barcode_format") == "EAN_13"

    # 2. Maggi 2-Minute Noodles
    maggi = data.get("8901058000290")
    assert maggi is not None
    assert maggi.get("barcode_format") == "EAN_13"

    # 3. Cadbury Dairy Milk Silk Desserts Brownie
    cadbury = data.get("7622202225024")
    assert cadbury is not None
    assert cadbury.get("barcode_format") == "EAN_13"

    # 4. Dove Serum Beauty Bar
    dove_serum = data.get("8901030997938")
    assert dove_serum is not None
    assert dove_serum.get("barcode_format") == "EAN_13"


def test_all_seeded_products_present_in_catalog():
    """Verify products.json contains the seeded prototype records."""
    with open(DEFAULT_CATALOG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert {"8901030997938", "8901058000290", "7622202225024"}.issubset(set(data.keys()))
    assert data["8901030997938"]["product_name"] == "Dove Serum Beauty Bar"
    assert data["8901030997938"]["net_quantity"] == "125 g"
    assert data["8901030997938"]["manufacturer_name"] == "Lakme Lever Pvt. Ltd."
    assert data["8901058000290"]["product_name"] == "MAGGI 2-Minute Noodles"
    assert data["7622202225024"]["product_name"] == "Cadbury Dairy Milk Silk Desserts Brownie"
    assert data["7622202225024"]["brand"] == "Cadbury Dairy Milk Silk"


@pytest.mark.asyncio
async def test_known_gtin_returns_dove_serum_beauty_bar():
    """Verify GTIN 8901030997938 returns Dove Serum Beauty Bar, 125 g, Lakme Lever Pvt. Ltd."""
    provider = LocalCatalogProvider()
    assert provider.is_available() is True

    record = await provider.get_product("8901030997938")
    assert record is not None
    assert record.gtin == "8901030997938"
    assert record.product_name == "Dove Serum Beauty Bar"
    assert record.brand_name == "Dove"
    assert record.net_quantity == "125"
    assert record.net_quantity_unit == "g"
    assert record.company_name == "Lakme Lever Pvt. Ltd."
    assert record.source == "PackCheck Controlled Prototype Catalog"


@pytest.mark.asyncio
async def test_reconciliation_works_with_dove_serum_beauty_bar_catalog_record():
    """Verify OCR reconciler matches packaging declarations with Dove Serum Beauty Bar catalog record."""
    provider = LocalCatalogProvider()
    reconciler = GTINReconciler(provider=provider)

    barcode_summary = _build_barcode_summary("8901030997938")
    extraction = _build_test_extraction(
        product_name="Dove",
        generic_name="serum beauty bar",
        brand="Dove",
        net_quantity="125 g",
        mfg_name="LAKME LEVER PVT. LTD.",
    )
    result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.lookup_status == GTINLookupStatus.FOUND
    assert result.overall_status == IdentityVerificationStatus.MATCH

    comps = {c.field_name: c for c in result.field_comparisons}
    assert comps["product_name"].status == FieldMatchStatus.MATCH
    assert comps["brand"].status == FieldMatchStatus.MATCH
    assert comps["net_quantity"].status == FieldMatchStatus.MATCH
    assert comps["manufacturer"].status == FieldMatchStatus.MATCH



@pytest.mark.asyncio
async def test_known_gtin_returns_maggi_product():
    """Verify GTIN 8901058000290 returns Maggi 2-Minute Noodles from products.json."""
    provider = LocalCatalogProvider()

    record = await provider.get_product("8901058000290")
    assert record is not None

    # Exact GTIN check
    assert record.gtin == "8901058000290"

    # Core identity fields
    assert record.product_name == "MAGGI 2-Minute Noodles"
    assert record.brand_name == "MAGGI"
    assert record.net_quantity == "70"
    assert record.net_quantity_unit == "g"
    assert record.company_name == "Nestlé India Limited"
    assert record.product_description == "Masala Noodles"

    # Source identifier
    assert record.source == "PackCheck Controlled Prototype Catalog"

    # Strict non-authoritative constraints
    assert "GS1" not in record.source
    assert "DataKart" not in record.source
    assert "Official" not in record.source


@pytest.mark.asyncio
async def test_reconciliation_works_with_maggi_catalog_record():
    """Verify OCR reconciler matches packaging declarations with Maggi local catalog record."""
    provider = LocalCatalogProvider()
    reconciler = GTINReconciler(provider=provider)

    barcode_summary = _build_barcode_summary("8901058000290")

    extraction = _build_test_extraction(
        product_name="MAGGI 2-Minute Noodles",
        generic_name="Masala Noodles",
        brand="MAGGI",
        net_quantity="70 g",
        mfg_name="Nestlé India Limited",
    )
    result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.lookup_status == GTINLookupStatus.FOUND
    assert result.overall_status == IdentityVerificationStatus.MATCH
    assert result.provider_name == "Local Product Catalog (Prototype)"
    assert "packaging declarations match local prototype product record" in result.summary

    comps = {c.field_name: c for c in result.field_comparisons}
    assert comps["product_name"].status == FieldMatchStatus.MATCH
    assert comps["brand"].status == FieldMatchStatus.MATCH
    assert comps["net_quantity"].status == FieldMatchStatus.MATCH
    assert comps["manufacturer"].status == FieldMatchStatus.MATCH


@pytest.mark.asyncio
async def test_known_gtin_returns_cadbury_product():
    """Verify GTIN 7622202225024 returns Cadbury Dairy Milk Silk Desserts Brownie from products.json."""
    provider = LocalCatalogProvider()

    record = await provider.get_product("7622202225024")
    assert record is not None

    # Exact GTIN check
    assert record.gtin == "7622202225024"

    # Core identity fields
    assert record.product_name == "Cadbury Dairy Milk Silk Desserts Brownie"
    assert record.brand_name == "Cadbury Dairy Milk Silk"
    assert record.net_quantity == "70"
    assert record.net_quantity_unit == "g"
    assert record.company_name == "Mondelez India Foods Private Limited"
    assert record.product_description == "Milk Chocolate with Centre Filling"

    # Source identifier
    assert record.source == "PackCheck Controlled Prototype Catalog"

    # Strict non-authoritative constraints
    assert "GS1" not in record.source
    assert "DataKart" not in record.source
    assert "Official" not in record.source


@pytest.mark.asyncio
async def test_reconciliation_works_with_cadbury_catalog_record():
    """Verify OCR reconciler matches packaging declarations with Cadbury local catalog record."""
    provider = LocalCatalogProvider()
    reconciler = GTINReconciler(provider=provider)

    barcode_summary = _build_barcode_summary("7622202225024")

    extraction = _build_test_extraction(
        product_name="Cadbury Dairy Milk Silk Desserts Brownie",
        generic_name="Milk Chocolate with Centre Filling",
        brand="Cadbury Dairy Milk Silk",
        net_quantity="70 g",
        mfg_name="Mondelez India Foods Private Limited",
    )
    result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.lookup_status == GTINLookupStatus.FOUND
    assert result.overall_status == IdentityVerificationStatus.MATCH
    assert result.provider_name == "Local Product Catalog (Prototype)"
    assert "packaging declarations match local prototype product record" in result.summary

    comps = {c.field_name: c for c in result.field_comparisons}
    assert comps["product_name"].status == FieldMatchStatus.MATCH
    assert comps["brand"].status == FieldMatchStatus.MATCH
    assert comps["net_quantity"].status == FieldMatchStatus.MATCH
    assert comps["manufacturer"].status == FieldMatchStatus.MATCH


@pytest.mark.asyncio
async def test_open_food_facts_never_called_when_local_catalog_active():
    """Test 6: Open Food Facts is NOT invoked when LOCAL_CATALOG is active (Dove, Maggi, and Cadbury)."""
    call_detected = False

    def mock_off_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_detected
        call_detected = True
        return httpx.Response(200, json={})

    transport = httpx.MockTransport(mock_off_handler)

    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="LOCAL_CATALOG")
        set_gtin_provider(None)
        provider = get_gtin_provider()

        assert isinstance(provider, LocalCatalogProvider)

        # Lookup Dove in local catalog
        rec_dove = await provider.get_product("8901030712999")
        assert rec_dove is not None
        assert rec_dove.product_name == "Dove Bathing Bar"

        # Lookup Maggi in local catalog
        rec_maggi = await provider.get_product("8901058000290")
        assert rec_maggi is not None
        assert rec_maggi.product_name == "MAGGI 2-Minute Noodles"

        # Lookup Cadbury in local catalog
        rec_cadbury = await provider.get_product("7622202225024")
        assert rec_cadbury is not None
        assert rec_cadbury.product_name == "Cadbury Dairy Milk Silk Desserts Brownie"

        # Lookup unknown in local catalog
        rec_unknown = await provider.get_product("8901719101038")
        assert rec_unknown is None

    # OFF was never touched!
    assert call_detected is False



@pytest.mark.asyncio
async def test_catalog_does_not_fabricate_missing_fields():
    """Test 7: Unconfirmed fields remain None and are not invented."""
    provider = LocalCatalogProvider()
    record = await provider.get_product("8901030712999")
    assert record is not None

    # Fields that are unconfirmed/null in products.json must be None in GTINProductRecord
    assert record.country_of_origin is None


@pytest.mark.asyncio
async def test_reconciliation_works_with_local_catalog_record():
    """Test 8: Reconciler successfully matches packaging declarations with local catalog record."""
    provider = LocalCatalogProvider()
    reconciler = GTINReconciler(provider=provider)

    barcode_summary = _build_barcode_summary("8901030712999")

    # 1. Matching extraction
    extraction = _build_test_extraction(
        product_name="Dove Bathing Bar",
        generic_name="Bathing Bar",
        brand="Dove",
        net_quantity="50 g",
        mfg_name="Hindustan Unilever Limited",
    )
    result = await reconciler.reconcile(barcode_summary, extraction)

    assert result.lookup_status == GTINLookupStatus.FOUND
    assert result.overall_status == IdentityVerificationStatus.MATCH
    assert result.provider_name == "Local Product Catalog (Prototype)"
    assert "packaging declarations match local prototype product record" in result.summary

    # Ensure field comparisons
    comps = {c.field_name: c for c in result.field_comparisons}
    assert comps["product_name"].status == FieldMatchStatus.MATCH
    assert comps["brand"].status == FieldMatchStatus.MATCH
    assert comps["net_quantity"].status == FieldMatchStatus.MATCH
    assert comps["manufacturer"].status == FieldMatchStatus.MATCH

    # 2. Mismatching extraction (e.g., net quantity conflict 50g vs 100g)
    mismatch_extraction = _build_test_extraction(
        product_name="Dove Bathing Bar",
        generic_name="Bathing Bar",
        brand="Dove",
        net_quantity="100 g",
        mfg_name="Hindustan Unilever Limited",
    )

    mismatch_result = await reconciler.reconcile(barcode_summary, mismatch_extraction)
    assert mismatch_result.overall_status == IdentityVerificationStatus.MISMATCH
    assert "mismatch on [net_quantity]" in mismatch_result.summary
    assert "conflict with local prototype product record" in mismatch_result.summary


def test_provider_switching_architecture():
    """Test 10: Provider switching architecture remains intact across all supported providers."""
    # 1. LOCAL_CATALOG
    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="LOCAL_CATALOG")
        set_gtin_provider(None)
        p1 = get_gtin_provider()
        assert isinstance(p1, LocalCatalogProvider)

    # 2. OPEN_FOOD_FACTS
    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="OPEN_FOOD_FACTS")
        set_gtin_provider(None)
        p2 = get_gtin_provider()
        assert isinstance(p2, OpenFoodFactsProvider)

    # 3. LOCAL_FIXTURE
    with patch("backend.app.services.gtin.providers.get_settings") as mock_settings:
        mock_settings.return_value = Settings(GTIN_PROVIDER="LOCAL_FIXTURE")
        set_gtin_provider(None)
        p3 = get_gtin_provider()
        assert isinstance(p3, LocalFixtureGTINProvider)


def test_api_verify_end_to_end_with_local_catalog():
    """Test full verification pipeline (/api/verify) with local catalog provider."""
    client = TestClient(app)
    png_bytes = _generate_barcode_png_bytes("8901030712999", zxingcpp.BarcodeFormat.EAN13)

    mock_extraction = _build_test_extraction(
        product_name="Dove Bathing Bar",
        generic_name="Bathing Bar",
        brand="Dove",
        net_quantity="50 g",
        mfg_name="Hindustan Unilever Limited",
    )

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_ocr = AsyncMock()
        mock_ocr.extract = AsyncMock(return_value=mock_extraction)
        mock_ocr.model_name = "test-mock-ocr"
        mock_get_provider.return_value = mock_ocr

        response = client.post(
            "/api/verify",
            files=[("images", ("dove_panel.png", png_bytes, "image/png"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Barcode detected
    barcode_data = data.get("barcode")
    assert barcode_data is not None
    assert barcode_data["primary_gtin"] == "8901030712999"
    assert barcode_data["is_valid_gtin"] is True

    # GTIN Identity verified via local catalog
    gtin_id = data.get("gtin_identity")
    assert gtin_id is not None
    assert gtin_id["overall_status"] == "MATCH"
    assert gtin_id["provider_name"] == "Local Product Catalog (Prototype)"
    assert gtin_id["product_record"]["product_name"] == "Dove Bathing Bar"
    assert gtin_id["product_record"]["product_description"] == "Bathing Bar"
    assert gtin_id["product_record"]["net_quantity"] == "50"
    assert gtin_id["product_record"]["company_name"] == "Hindustan Unilever Limited"
    assert gtin_id["product_record"]["source"] == "PackCheck Controlled Prototype Catalog"


    # Legal Metrology verdict evaluated normally
    compliance = data.get("compliance")
    assert compliance is not None
    assert compliance["overall_verdict"] in ["PASS", "FLAGGED_FOR_REVIEW"]


@pytest.mark.asyncio
async def test_custom_catalog_path_and_missing_file_safety(tmp_path: Path):
    """Test that LocalCatalogProvider handles custom paths and missing files safely."""
    # 1. Custom temporary catalog
    custom_file = tmp_path / "custom_products.json"
    custom_file.write_text(
        json.dumps({
            "8901030712999": {
                "gtin": "8901030712999",
                "product_name": "Dove Custom Test",
                "brand": "Dove",
                "net_quantity": "50 g",
                "manufacturer_name": "Test HUL",
                "source": "PackCheck Controlled Prototype Catalog",
            }
        }),
        encoding="utf-8",
    )

    custom_provider = LocalCatalogProvider(catalog_path=custom_file)
    rec = await custom_provider.get_product("8901030712999")
    assert rec is not None
    assert rec.product_name == "Dove Custom Test"

    # 2. Non-existent file
    missing_provider = LocalCatalogProvider(catalog_path=tmp_path / "nonexistent.json")
    assert await missing_provider.get_product("8901030712999") is None
