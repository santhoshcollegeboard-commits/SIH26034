"""Integration tests for Multi-Product Independent Reports API.

Verifies all required scenarios from the specification:
- CASE 1 — SINGLE PRODUCT: 1 image -> 1 independent report.
- CASE 2 — TWO DIFFERENT PRODUCTS: 2 images -> 2 independent reports with distinct state.
- CASE 3 — THREE DIFFERENT PRODUCTS: Maggi, Cadbury, Dove -> 3 independent reports with exact evidence images.
- CASE 4 — PRODUCT FAILURE ISOLATION: 1 failed product does not corrupt other product reports.
- CASE 5 — EXISTING MULTI-PANEL REGRESSION: Multi-panel single-package verification preserved.
- CASE 6 — SEQUENTIAL INSPECTION STATE RESET: Complete isolation between sequential verification requests.
"""

import io
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
import zxingcpp
from PIL import Image

from backend.app.main import app
from backend.app.schemas.compliance import OverallVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

client = TestClient(app)

DUMMY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb"


def _make_valid_image_bytes() -> bytes:
    """Create a minimal valid PNG image."""
    img = Image.new("RGB", (64, 64), color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_barcode_png_bytes(content: str, barcode_format: zxingcpp.BarcodeFormat) -> bytes:
    """Generate in-memory PNG bytes of a valid barcode symbol."""
    bc = zxingcpp.create_barcode(content, barcode_format)
    zx_img = bc.to_image()
    pil_img = Image.frombytes("L", (zx_img.shape[1], zx_img.shape[0]), bytes(zx_img))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _make_field(val: str | None, status: str = "extracted", conf: float = 0.95):
    return ExtractedField(value=val, confidence=conf if val else None, status=status)


def _make_extraction(product_name: str, generic_name: str, net_qty: str, mrp: str, mfg: str) -> ExtractionResult:
    mrp_val = mrp if "USP" in mrp else f"{mrp} | USP: ₹ 0.20 per g"
    return ExtractionResult(
        product_name=_make_field(product_name),
        common_or_generic_name=_make_field(generic_name),
        net_quantity=_make_field(net_qty),
        mrp=_make_field(mrp_val),
        manufacturer_name=_make_field(mfg),
        manufacturer_address=_make_field("Plot 12, Industrial Area, Sector 5, Haridwar, Uttarakhand - 249403"),
        month_year_of_manufacture=_make_field("06/2026"),
        consumer_care_details=_make_field("Toll-Free: 1800-123-4567 | care@brand.in"),
        country_of_origin=_make_field("India"),
    )


# =============================================================================
# CASE 1 — SINGLE PRODUCT
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_1_single_product(mock_get_provider, mock_settings):
    """CASE 1: Uploading 1 image returns 1 independent product report."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext = _make_extraction(
        product_name="MAGGI 2-Minute Noodles",
        generic_name="Masala Noodles",
        net_qty="70 g",
        mrp="₹ 14.00 (Inclusive of all taxes)",
        mfg="Nestlé India Limited",
    )
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = ext
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    files = [("images", ("maggi.png", io.BytesIO(_make_valid_image_bytes()), "image/png"))]
    data = {"inspection_mode": "multi_product"}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    assert res["inspection_mode"] == "multi_product"
    assert "results" in res
    assert len(res["results"]) == 1

    report = res["results"][0]
    assert report["product_id"] == "product_1"
    assert "MAGGI" in (report["product_name"] or "")
    assert report["success"] is True
    assert report["extraction"] is not None
    assert report["compliance"] is not None
    assert report["compliance"]["overall_verdict"] == OverallVerdict.PASS.value


# =============================================================================
# CASE 2 — TWO DIFFERENT PRODUCTS
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_2_two_different_products(mock_get_provider, mock_settings):
    """CASE 2: Uploading 2 distinct product images returns 2 independent reports."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext_a = _make_extraction(
        product_name="Brand A Biscuits",
        generic_name="Cookies",
        net_qty="100 g",
        mrp="₹ 30.00 (Inclusive of all taxes)",
        mfg="Bakery India Ltd",
    )
    ext_b = _make_extraction(
        product_name="Brand B Shampoo",
        generic_name="Hair Cleanser",
        net_qty="200 ml",
        mrp="₹ 180.00 (Inclusive of all taxes)",
        mfg="Personal Care Ltd",
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [ext_a, ext_b]
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("product_a.png", io.BytesIO(_make_valid_image_bytes()), "image/png")),
        ("images", ("product_b.png", io.BytesIO(_make_valid_image_bytes()), "image/png")),
    ]
    data = {
        "inspection_mode": "multi_product",
        "product_labels": ["Product A", "Product B"],
    }

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    assert len(res["results"]) == 2

    # Product A
    rep_a = res["results"][0]
    assert rep_a["product_id"] == "product_1"
    assert rep_a["extraction"]["product_name"]["value"] == "Brand A Biscuits"
    assert rep_a["extraction"]["net_quantity"]["value"] == "100 g"
    assert rep_a["compliance"]["overall_verdict"] == OverallVerdict.PASS.value

    # Product B
    rep_b = res["results"][1]
    assert rep_b["product_id"] == "product_2"
    assert rep_b["extraction"]["product_name"]["value"] == "Brand B Shampoo"
    assert rep_b["extraction"]["net_quantity"]["value"] == "200 ml"
    assert rep_b["compliance"]["overall_verdict"] == OverallVerdict.PASS.value

    # Data isolation check: no leakage
    assert rep_a["extraction"]["product_name"]["value"] != rep_b["extraction"]["product_name"]["value"]
    assert rep_a["extraction"]["net_quantity"]["value"] != rep_b["extraction"]["net_quantity"]["value"]


# =============================================================================
# CASE 3 — THREE DIFFERENT PRODUCTS (MAGGI, CADBURY, DOVE)
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_3_three_different_products_maggi_cadbury_dove(mock_get_provider, mock_settings):
    """CASE 3: Maggi, Cadbury, and Dove uploaded together.
    
    Expected 3 independent reports with exact evidence images:
    - Maggi   -> /evidence/8901058000290/evidence.png
    - Cadbury -> /evidence/7622202225024/evidence.png
    - Dove    -> /evidence/8901030997938/evidence.png
    """
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    # Generate real barcode symbols for all three GTINs
    maggi_bc = _generate_barcode_png_bytes("8901058000290", zxingcpp.BarcodeFormat.EAN13)
    cadbury_bc = _generate_barcode_png_bytes("7622202225024", zxingcpp.BarcodeFormat.EAN13)
    dove_bc = _generate_barcode_png_bytes("8901030997938", zxingcpp.BarcodeFormat.EAN13)

    ext_maggi = _make_extraction(
        product_name="MAGGI 2-Minute Noodles",
        generic_name="Masala Noodles",
        net_qty="70 g",
        mrp="₹ 14.00 (Inclusive of all taxes)",
        mfg="Nestlé India Limited",
    )
    ext_cadbury = _make_extraction(
        product_name="Cadbury Dairy Milk Silk Desserts Brownie",
        generic_name="Milk Chocolate with Centre Filling",
        net_qty="70 g",
        mrp="₹ 175.00 (Inclusive of all taxes)",
        mfg="Mondelez India Foods Private Limited",
    )
    ext_dove = _make_extraction(
        product_name="Dove Serum Beauty Bar",
        generic_name="Bathing Bar",
        net_qty="100 g",
        mrp="₹ 85.00 (Inclusive of all taxes)",
        mfg="Hindustan Unilever Limited",
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [ext_maggi, ext_cadbury, ext_dove]
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("maggi.png", io.BytesIO(maggi_bc), "image/png")),
        ("images", ("cadbury.png", io.BytesIO(cadbury_bc), "image/png")),
        ("images", ("dove.png", io.BytesIO(dove_bc), "image/png")),
    ]
    data = {
        "inspection_mode": "multi_product",
        "product_labels": ["Maggi Noodles", "Cadbury Silk", "Dove Soap"],
    }

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    assert len(res["results"]) == 3

    rep_maggi = res["results"][0]
    rep_cadbury = res["results"][1]
    rep_dove = res["results"][2]

    # Check Maggi report
    assert rep_maggi["gtin"] == "8901058000290"
    assert rep_maggi["product_evidence"] is not None
    assert rep_maggi["product_evidence"]["evidence_image"] == "/evidence/8901058000290/evidence.png"
    assert "MAGGI" in rep_maggi["product_name"]

    # Check Cadbury report
    assert rep_cadbury["gtin"] == "7622202225024"
    assert rep_cadbury["product_evidence"] is not None
    assert rep_cadbury["product_evidence"]["evidence_image"] == "/evidence/7622202225024/evidence.png"
    assert "Cadbury" in rep_cadbury["product_name"]

    # Check Dove report
    assert rep_dove["gtin"] == "8901030997938"
    assert rep_dove["product_evidence"] is not None
    assert rep_dove["product_evidence"]["evidence_image"] == "/evidence/8901030997938/evidence.png"
    assert "Dove" in rep_dove["product_name"]

    # Verify no evidence images are swapped or shared
    evidence_images = [r["product_evidence"]["evidence_image"] for r in res["results"]]
    assert len(set(evidence_images)) == 3
    assert "/evidence/8901058000290/evidence.png" in evidence_images
    assert "/evidence/7622202225024/evidence.png" in evidence_images
    assert "/evidence/8901030997938/evidence.png" in evidence_images


# =============================================================================
# CASE 4 — PRODUCT FAILURE ISOLATION
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_4_product_failure_isolation(mock_get_provider, mock_settings):
    """CASE 4: Product 2 fails OCR, but Product 1 and Product 3 succeed without corruption."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext1 = _make_extraction("Product 1", "Tea", "500 g", "₹ 200", "Mfg 1")
    ext3 = _make_extraction("Product 3", "Coffee", "200 g", "₹ 350", "Mfg 3")

    mock_provider = AsyncMock()
    # Product 1 succeeds, Product 2 raises OCR timeout, Product 3 succeeds
    mock_provider.extract.side_effect = [
        ext1,
        RuntimeError("Vision API rate limit on Product 2"),
        ext3,
    ]
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("prod1.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("prod2.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("prod3.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"inspection_mode": "multi_product"}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    # Overall inspection succeeds because at least one product succeeded
    assert res["success"] is True
    assert len(res["results"]) == 3

    # Product 1 is fully intact
    assert res["results"][0]["success"] is True
    assert res["results"][0]["extraction"]["product_name"]["value"] == "Product 1"
    assert res["results"][0]["compliance"] is not None

    # Product 2 has isolated failure
    assert res["results"][1]["success"] is False
    assert "rate limit" in res["results"][1]["error"].lower()
    assert res["results"][1]["compliance"] is None

    # Product 3 is fully intact
    assert res["results"][2]["success"] is True
    assert res["results"][2]["extraction"]["product_name"]["value"] == "Product 3"
    assert res["results"][2]["compliance"] is not None


# =============================================================================
# CASE 5 — EXISTING MULTI-PANEL REGRESSION
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_5_existing_multi_panel_regression(mock_get_provider, mock_settings):
    """CASE 5: Existing multi-panel verification still works without inspection_mode."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    front_ext = ExtractionResult(
        product_name=_make_field("Assam Tea"),
        net_quantity=_make_field("500 g"),
    )
    back_ext = ExtractionResult(
        mrp=_make_field("₹ 250.00 (Inclusive of all taxes)"),
        manufacturer_name=_make_field("Tea Co Ltd"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [front_ext, back_ext]
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("front.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("back.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"panel_labels": ["Front Panel", "Back Panel"]}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["success"] is True
    assert res["image_count"] == 2
    assert res["panel_labels"] == ["Front Panel", "Back Panel"]
    assert res["inspection_mode"] == "single_product"

    # Merged declarations
    assert res["extraction"]["product_name"]["value"] == "Assam Tea"
    assert res["extraction"]["mrp"]["value"] == "₹ 250.00 (Inclusive of all taxes)"
    assert res["extraction"]["product_name"]["source_panel_label"] == "Front Panel"
    assert res["extraction"]["mrp"]["source_panel_label"] == "Back Panel"


# =============================================================================
# CASE 6 — NEW INSPECTION STATE RESET
# =============================================================================

@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_case_6_sequential_inspection_state_reset(mock_get_provider, mock_settings):
    """CASE 6: Verifying 3 products followed by 1 product leaves no residual state."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    mock_provider = AsyncMock()
    ext1 = _make_extraction("P1", "G1", "100 g", "₹ 50", "M1")
    ext2 = _make_extraction("P2", "G2", "200 g", "₹ 80", "M2")
    ext3 = _make_extraction("P3", "G3", "300 g", "₹ 110", "M3")
    ext_single = _make_extraction("Single Clean Product", "Clean Item", "50 g", "₹ 20", "Clean Mfg")

    mock_provider.extract.side_effect = [ext1, ext2, ext3, ext_single]
    mock_provider.model_name = "mock-vision"
    mock_get_provider.return_value = mock_provider

    # Inspection 1: 3 products
    files_3 = [
        ("images", ("p1.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("p2.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("p3.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    res1 = client.post("/api/verify", files=files_3, data={"inspection_mode": "multi_product"}).json()
    assert len(res1["results"]) == 3

    # Inspection 2: 1 product
    files_1 = [
        ("images", ("single.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    res2 = client.post("/api/verify", files=files_1, data={"inspection_mode": "multi_product"}).json()
    assert len(res2["results"]) == 1
    assert res2["results"][0]["product_id"] == "product_1"
    assert res2["results"][0]["extraction"]["product_name"]["value"] == "Single Clean Product"
