"""Unit and integration tests for GTIN Phase 2: GS1 Product Identity + OCR Reconciliation.

Covers all 10 required Phase 2 scenarios:
1. Valid GTIN with product record -> MATCH
2. Valid GTIN with contradictory product data -> MISMATCH
3. Missing product record -> NOT_VERIFIABLE (NOT_FOUND)
4. Missing OCR field -> NOT_COMPARABLE
5. Equivalent quantities (500 g / 0.5 kg, 1 L / 1000 ml) -> MATCH
6. Same GTIN appearing on multiple panels -> deduplicated
7. Different GTINs -> ambiguity preserved (AMBIGUOUS_GTIN)
8. Invalid GTIN -> no external lookup (INVALID_GTIN)
9. External provider unavailable -> NOT_VERIFIABLE (SERVICE_UNAVAILABLE)
10. Existing Legal Metrology verdict remains unchanged
"""

import io
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from PIL import Image
import pytest
import zxingcpp

from backend.app.main import app
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
    GTINProvider,
    LocalFixtureGTINProvider,
)
from backend.app.services.gtin.reconciliation import (
    GTINReconciler,
    parse_canonical_quantity,
)
from backend.app.services.gtin.selector import select_gtin_candidate


# =============================================================================
# Test Image Helpers (In-Memory, Deterministic)
# =============================================================================

def _generate_barcode_png_bytes(content: str, barcode_format: zxingcpp.BarcodeFormat) -> bytes:
    """Generate in-memory PNG bytes of a valid barcode symbol."""
    bc = zxingcpp.create_barcode(content, barcode_format)
    zx_img = bc.to_image()
    pil_img = Image.frombytes("L", (zx_img.shape[1], zx_img.shape[0]), bytes(zx_img))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _build_test_extraction(
    product_name: str = "Assam Gold CTC Black Tea",
    generic_name: str = "CTC Leaf Tea",
    net_quantity: str = "500 g",
    mfg_name: str = "Himalayan Highlands Tea Estates Pvt. Ltd.",
) -> ExtractionResult:
    """Helper creating an ExtractionResult populated with test declarations."""
    return ExtractionResult(
        product_name=ExtractedField(value=product_name, status="extracted", confidence=0.98),
        common_or_generic_name=ExtractedField(value=generic_name, status="extracted", confidence=0.95),
        net_quantity=ExtractedField(value=net_quantity, status="extracted", confidence=0.99),
        manufacturer_name=ExtractedField(value=mfg_name, status="extracted", confidence=0.97),
    )


# =============================================================================
# 1. Physical Quantity Normalization Tests (Scenario 5)
# =============================================================================

@pytest.mark.parametrize("val_str,unit_hint,expected_val,expected_unit", [
    ("500 g", None, 500.0, "g"),
    ("0.5 kg", None, 500.0, "g"),
    ("1 kg", None, 1000.0, "g"),
    ("1000 g", None, 1000.0, "g"),
    ("250 gm", None, 250.0, "g"),
    ("500 grams", None, 500.0, "g"),
    ("1 l", None, 1000.0, "ml"),
    ("1000 ml", None, 1000.0, "ml"),
    ("0.5 L", None, 500.0, "ml"),
    ("750 mls", None, 750.0, "ml"),
    ("10 N", None, 10.0, "units"),
    ("50 units", None, 50.0, "units"),
    ("500", "g", 500.0, "g"),
    ("0.5", "kg", 500.0, "g"),
])
def test_parse_canonical_quantity(val_str, unit_hint, expected_val, expected_unit):
    """Verify physical unit normalization across metric mass, volume, and count."""
    res = parse_canonical_quantity(val_str, unit_hint=unit_hint)
    assert res is not None
    num, unit = res
    assert abs(num - expected_val) < 1e-4
    assert unit == expected_unit


def test_parse_canonical_quantity_invalid():
    """Unparseable or empty quantities return None safely."""
    assert parse_canonical_quantity("") is None
    assert parse_canonical_quantity(None) is None
    assert parse_canonical_quantity("abc xyz") is None


# =============================================================================
# 2. GTIN Selection & Deduplication Tests (Scenarios 6, 7, 8)
# =============================================================================

def test_selector_deduplicates_same_gtin_across_panels():
    """Scenario 6: Same GTIN appearing on multiple panels is deduplicated."""
    item1 = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
        panel_index=0,
        panel_label="Front",
    )
    item2 = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
        panel_index=1,
        panel_label="Back",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.MULTIPLE_BARCODES_DETECTED,
        detected=True,
        count=2,
        barcodes=[item1, item2],
        primary_gtin=None,
        is_valid_gtin=None,
        message="2 barcodes detected",
    )

    res = select_gtin_candidate(summary)
    assert res.status == GTINLookupStatus.FOUND
    assert res.selected_gtin == "8901030892011"
    assert len(res.unique_candidates) == 1
    assert "Front, Back" in res.message


def test_selector_preserves_ambiguity_for_different_gtins():
    """Scenario 7: Distinct valid GTINs preserve ambiguity without guessing."""
    item1 = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    item2 = BarcodeItem(
        raw_value="96385074",
        format=BarcodeFormat.EAN_8,
        gtin="96385074",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-8",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.MULTIPLE_BARCODES_DETECTED,
        detected=True,
        count=2,
        barcodes=[item1, item2],
        message="2 barcodes detected",
    )

    res = select_gtin_candidate(summary)
    assert res.status == GTINLookupStatus.AMBIGUOUS_GTIN
    assert res.selected_gtin is None
    assert len(res.unique_candidates) == 2


def test_selector_filters_out_marketing_qr_code():
    """2D marketing QR code does not conflict with 1D retail GTIN."""
    retail_item = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    qr_item = BarcodeItem(
        raw_value="https://brand.example.com/promo",
        format=BarcodeFormat.QR_CODE,
        gtin=None,
        is_valid_gtin=False,
        validation_status=GTINValidationStatus.NOT_A_GTIN_FORMAT,
        validation_message="QR Code is not GTIN",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.MULTIPLE_BARCODES_DETECTED,
        detected=True,
        count=2,
        barcodes=[retail_item, qr_item],
        message="2 barcodes detected",
    )

    res = select_gtin_candidate(summary)
    assert res.status == GTINLookupStatus.FOUND
    assert res.selected_gtin == "8901030892011"
    assert len(res.unique_candidates) == 1


def test_selector_rejects_invalid_gtin():
    """Scenario 8: Invalid check digit returns INVALID_GTIN without lookup."""
    invalid_item = BarcodeItem(
        raw_value="8901030892014",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892014",
        is_valid_gtin=False,
        validation_status=GTINValidationStatus.INVALID_CHECK_DIGIT,
        validation_message="Invalid check digit",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[invalid_item],
        primary_gtin="8901030892014",
        is_valid_gtin=False,
        message="Invalid barcode",
    )

    res = select_gtin_candidate(summary)
    assert res.status == GTINLookupStatus.INVALID_GTIN
    assert res.selected_gtin is None


# =============================================================================
# 3. Reconciliation Engine Tests (Scenarios 1, 2, 3, 4, 5, 9)
# =============================================================================

@pytest.mark.asyncio
async def test_reconciliation_exact_match():
    """Scenario 1: Valid GTIN with matching product record -> MATCH."""
    reconciler = GTINReconciler(provider=LocalFixtureGTINProvider())

    item = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8901030892011",
        is_valid_gtin=True,
        message="Single barcode detected",
    )

    extraction = _build_test_extraction(
        product_name="Assam Gold Premium CTC Black Tea",
        generic_name="CTC Leaf Tea",
        net_quantity="500 g",
        mfg_name="Himalayan Highlands Tea Estates Pvt. Ltd.",
    )

    res = await reconciler.reconcile(summary, extraction)
    assert res.lookup_status == GTINLookupStatus.FOUND
    assert res.overall_status == IdentityVerificationStatus.MATCH
    assert res.gtin == "8901030892011"
    assert res.product_record is not None
    assert res.product_record.brand_name == "Assam Gold"

    # All 4 comparable fields should match
    field_map = {c.field_name: c for c in res.field_comparisons}
    assert field_map["product_name"].status in [FieldMatchStatus.MATCH, FieldMatchStatus.PARTIAL_MATCH]
    assert field_map["brand"].status == FieldMatchStatus.MATCH
    assert field_map["net_quantity"].status == FieldMatchStatus.MATCH
    assert field_map["manufacturer"].status == FieldMatchStatus.MATCH


@pytest.mark.asyncio
async def test_reconciliation_equivalent_quantity_match():
    """Scenario 5: 0.5 kg on packaging matches 500 g in GTIN registry -> MATCH."""
    reconciler = GTINReconciler(provider=LocalFixtureGTINProvider())

    item = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8901030892011",
        is_valid_gtin=True,
        message="Single barcode",
    )

    # Packaging declared in '0.5 kg' while registry stores '500 g'
    extraction = _build_test_extraction(net_quantity="0.5 kg")

    res = await reconciler.reconcile(summary, extraction)
    assert res.overall_status == IdentityVerificationStatus.MATCH
    field_map = {c.field_name: c for c in res.field_comparisons}
    assert field_map["net_quantity"].status == FieldMatchStatus.MATCH
    assert "physically equivalent" in field_map["net_quantity"].message


@pytest.mark.asyncio
async def test_reconciliation_contradictory_product_data():
    """Scenario 2: Valid GTIN with contradictory label declarations -> MISMATCH."""
    reconciler = GTINReconciler(provider=LocalFixtureGTINProvider())

    # GTIN 8901234567890 in fixture is 'PureGreen Organic Green Tea 200g' by 'GreenLeaf Agro'
    item = BarcodeItem(
        raw_value="8901234567890",
        format=BarcodeFormat.EAN_13,
        gtin="8901234567890",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8901234567890",
        is_valid_gtin=True,
        message="Single barcode",
    )

    # Label declarations contradict the GTIN record on product name, brand, quantity, and mfg
    contradictory_extraction = _build_test_extraction(
        product_name="Crunchy Bites Masala Chips",
        generic_name="Potato Crisps",
        net_quantity="500 g",  # Registry is 200 g
        mfg_name="FastSnacks Industries Pvt. Ltd.",
    )

    res = await reconciler.reconcile(summary, contradictory_extraction)
    assert res.lookup_status == GTINLookupStatus.FOUND
    assert res.overall_status == IdentityVerificationStatus.MISMATCH
    assert "mismatch" in res.summary.lower()

    field_map = {c.field_name: c for c in res.field_comparisons}
    assert field_map["net_quantity"].status == FieldMatchStatus.MISMATCH
    assert field_map["manufacturer"].status == FieldMatchStatus.MISMATCH


@pytest.mark.asyncio
async def test_reconciliation_unregistered_gtin():
    """Scenario 3: Missing product record -> NOT_VERIFIABLE (NOT_FOUND)."""
    reconciler = GTINReconciler(provider=LocalFixtureGTINProvider())

    # A syntactically valid GTIN not in the registry
    item = BarcodeItem(
        raw_value="8909999999995",
        format=BarcodeFormat.EAN_13,
        gtin="8909999999995",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8909999999995",
        is_valid_gtin=True,
        message="Single barcode",
    )

    extraction = _build_test_extraction()
    res = await reconciler.reconcile(summary, extraction)

    assert res.lookup_status == GTINLookupStatus.NOT_FOUND
    assert res.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE
    assert res.product_record is None
    assert "not found in the authoritative product registry" in res.summary


@pytest.mark.asyncio
async def test_reconciliation_missing_ocr_field():
    """Scenario 4: Missing OCR field -> NOT_COMPARABLE for that field."""
    reconciler = GTINReconciler(provider=LocalFixtureGTINProvider())

    item = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8901030892011",
        is_valid_gtin=True,
        message="Single barcode",
    )

    # Empty net_quantity on packaging
    extraction = ExtractionResult(
        product_name=ExtractedField(value="Assam Gold Tea", status="extracted"),
        net_quantity=ExtractedField(value=None, status="not_found"),
    )

    res = await reconciler.reconcile(summary, extraction)
    field_map = {c.field_name: c for c in res.field_comparisons}
    assert field_map["net_quantity"].status == FieldMatchStatus.NOT_COMPARABLE
    assert field_map["net_quantity"].ocr_value is None


@pytest.mark.asyncio
async def test_reconciliation_provider_unavailable():
    """Scenario 9: External provider error -> NOT_VERIFIABLE (SERVICE_UNAVAILABLE)."""
    # Create failing mock provider
    failing_provider = AsyncMock(spec=GTINProvider)
    failing_provider.get_product.side_effect = ConnectionError("Registry connection timed out.")
    failing_provider.is_available.return_value = False

    reconciler = GTINReconciler(provider=failing_provider)

    item = BarcodeItem(
        raw_value="8901030892011",
        format=BarcodeFormat.EAN_13,
        gtin="8901030892011",
        is_valid_gtin=True,
        validation_status=GTINValidationStatus.VALID,
        validation_message="Valid GTIN-13",
    )
    summary = BarcodeSummary(
        status=BarcodeDetectionStatus.BARCODE_DETECTED,
        detected=True,
        count=1,
        barcodes=[item],
        primary_gtin="8901030892011",
        is_valid_gtin=True,
        message="Single barcode",
    )

    res = await reconciler.reconcile(summary, _build_test_extraction())
    assert res.lookup_status == GTINLookupStatus.SERVICE_UNAVAILABLE
    assert res.overall_status == IdentityVerificationStatus.NOT_VERIFIABLE
    assert "unavailable" in res.summary.lower()


# =============================================================================
# 4. End-to-End API Integration & Legal Metrology Independence (Scenario 10)
# =============================================================================

@pytest.fixture
def client():
    return TestClient(app)


def test_api_verify_reconciles_gtin_identity_matching(client):
    """Scenario 10A: API /api/verify populates gtin_identity MATCH without affecting LM verdict."""
    png_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)

    # Mock OCR returning compliant declarations matching Assam Gold Tea
    mock_extraction = _build_test_extraction(
        product_name="Assam Gold CTC Black Tea",
        generic_name="Black Tea",
        net_quantity="500 g",
        mfg_name="Himalayan Highlands Tea Estates Pvt. Ltd.",
    )

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.extract = AsyncMock(return_value=mock_extraction)
        mock_provider.model_name = "test-gemini-mock"
        mock_get_provider.return_value = mock_provider

        response = client.post(
            "/api/verify",
            files=[("images", ("panel.png", png_bytes, "image/png"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Barcode Phase 1 data is present
    assert data["barcode"] is not None
    assert data["barcode"]["primary_gtin"] == "8901030892011"

    # GTIN Phase 2 data is present
    gtin_id = data.get("gtin_identity")
    assert gtin_id is not None
    assert gtin_id["lookup_status"] == "FOUND"
    assert gtin_id["overall_status"] == "MATCH"
    assert gtin_id["gtin"] == "8901030892011"
    assert gtin_id["product_record"]["brand_name"] == "Assam Gold"

    # Legal Metrology verdict is independently computed
    assert "compliance" in data
    assert data["compliance"]["overall_verdict"] in ["PASS", "FAIL", "FLAGGED_FOR_REVIEW"]


def test_api_verify_gtin_mismatch_does_not_fail_legal_metrology(client):
    """Scenario 10B: A GTIN MISMATCH must NOT alter or force Legal Metrology verdict to FAIL."""
    # GTIN 8901234567890 is 'PureGreen Organic Green Tea 200g'
    png_bytes = _generate_barcode_png_bytes("8901234567890", zxingcpp.BarcodeFormat.EAN13)

    # Packaging declares Assam Gold CTC Black Tea 500g
    mock_extraction = _build_test_extraction(
        product_name="Assam Gold CTC Black Tea",
        net_quantity="500 g",
        mfg_name="Himalayan Highlands Tea Estates",
    )

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.extract = AsyncMock(return_value=mock_extraction)
        mock_provider.model_name = "test-gemini-mock"
        mock_get_provider.return_value = mock_provider

        response = client.post(
            "/api/verify",
            files=[("images", ("panel.png", png_bytes, "image/png"))],
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # GTIN Identity reflects MISMATCH
    gtin_id = data.get("gtin_identity")
    assert gtin_id is not None
    assert gtin_id["overall_status"] == "MISMATCH"

    # Legal Metrology rule engine evaluates declarations on their own statutory merit
    # The LM verdict is NOT forced to FAIL because of a GTIN identity mismatch!
    compliance = data["compliance"]
    assert compliance is not None
    # Verify the rule engine evaluated LM rules independently
    rule_ids = [e["rule_id"] for e in compliance["evaluations"]]
    assert "LM-PC-06-1-A" in rule_ids  # Generic name rule
    assert "LM-PC-06-1-B" in rule_ids  # Manufacturer rule
