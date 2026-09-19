"""Comprehensive test suite for Product Evidence Image Lookup System.

Tests all 10 requirements:
1. Known GTIN with evidence record → correct evidence image returned.
2. Maggi GTIN 8901058000290 → correct evidence image returned.
3. Unknown GTIN → safe no-evidence state.
4. Multiple product records can coexist.
5. One GTIN maps to one evidence image.
6. Missing physical image does not crash verification.
7. Evidence lookup does not alter rule-engine results.
8. Evidence lookup does not alter OCR results.
9. Evidence lookup does not alter GTIN reconciliation.
10. No product-specific hardcoded GTIN UI conditions exist.
"""

import io
import json
from pathlib import Path
import re
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import zxingcpp

from backend.app.main import app
from backend.app.schemas.barcode import (
    BarcodeDetectionStatus,
    BarcodeFormat,
    BarcodeItem,
    BarcodeSummary,
    GTINValidationStatus,
)
from backend.app.schemas.evidence import ProductEvidenceRecord
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.services.evidence.service import (
    DEFAULT_EVIDENCE_PATH,
    ProductEvidenceService,
    get_evidence_service,
    set_evidence_service,
)
from backend.app.services.rules.engine import DeterministicRuleEngine


# =============================================================================
# Helpers & Fixtures
# =============================================================================

def _build_test_extraction(
    product_name: str = "MAGGI 2-Minute Noodles",
    generic_name: str = "Masala Noodles",
    brand: str = "MAGGI",
    net_quantity: str = "70 g",
    mfg_name: str = "Nestlé India Limited",
) -> ExtractionResult:
    """Helper to build an ExtractionResult matching packaging declarations."""
    return ExtractionResult(
        product_name=ExtractedField(value=product_name, confidence=0.95),
        common_or_generic_name=ExtractedField(value=generic_name, confidence=0.90),
        brand_name=ExtractedField(value=brand, confidence=0.95),
        net_quantity=ExtractedField(value=net_quantity, confidence=0.95),
        manufacturer_name=ExtractedField(value=mfg_name, confidence=0.95),
        packer_name=ExtractedField(value=None, confidence=0.0),
        importer_name=ExtractedField(value=None, confidence=0.0),
        consumer_care_details=ExtractedField(
            value="Email: wecare@nestle.in, Toll Free: 1800-103-1947", confidence=0.90
        ),
        country_of_origin=ExtractedField(value=None, confidence=0.0),
        mrp=ExtractedField(value="₹ 15.00 (incl. of all taxes)", confidence=0.95),
        unit_sale_price=ExtractedField(value="₹ 0.21 / g", confidence=0.90),
        manufacturing_date=ExtractedField(value="12/2023", confidence=0.90),
        expiry_date=ExtractedField(value="12/2024", confidence=0.90),
        best_before_date=ExtractedField(value=None, confidence=0.0),
        sizes_or_dimensions=ExtractedField(value=None, confidence=0.0),
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
def reset_evidence_service_singleton():
    """Ensure singleton is cleanly reset before and after each test."""
    set_evidence_service(None)
    yield
    set_evidence_service(None)


# =============================================================================
# Test Cases
# =============================================================================

def test_known_gtin_returns_evidence_record():
    """Requirement 1: Known GTIN with evidence record returns correct evidence image."""
    service = ProductEvidenceService()
    record = service.get_evidence("8901058000290")

    assert record is not None
    assert isinstance(record, ProductEvidenceRecord)
    assert record.gtin == "8901058000290"
    assert record.evidence_image == "/evidence/8901058000290/evidence.png"


def test_maggi_gtin_returns_correct_evidence_image():
    """Requirement 2: Maggi GTIN 8901058000290 returns MAGGI 2-Minute Noodles and expected image."""
    service = ProductEvidenceService()
    record = service.get_evidence("8901058000290")

    assert record is not None
    assert record.gtin == "8901058000290"
    assert record.product_name == "MAGGI 2-Minute Noodles"
    assert record.evidence_image == "/evidence/8901058000290/evidence.png"


def test_cadbury_gtin_returns_correct_evidence_image():
    """Cadbury GTIN 7622202225024 returns Cadbury Dairy Milk Silk Desserts Brownie and expected image."""
    service = ProductEvidenceService()
    record = service.get_evidence("7622202225024")

    assert record is not None
    assert record.gtin == "7622202225024"
    assert record.product_name == "Cadbury Dairy Milk Silk Desserts Brownie"
    assert record.evidence_image == "/evidence/7622202225024/evidence.png"


def test_dove_serum_beauty_bar_gtin_returns_correct_evidence_image():
    """Dove Serum Beauty Bar GTIN 8901030997938 returns Dove Serum Beauty Bar and expected image."""
    service = ProductEvidenceService()
    record = service.get_evidence("8901030997938")

    assert record is not None
    assert record.gtin == "8901030997938"
    assert record.product_name == "Dove Serum Beauty Bar"
    assert record.evidence_image == "/evidence/8901030997938/evidence.png"



def test_unknown_gtin_returns_safe_no_evidence_state():
    """Requirement 3: Unknown valid GTIN returns None safely without raising errors."""
    service = ProductEvidenceService()

    # Valid GTIN but not in evidence catalog (e.g. Parle-G 8901719101038)
    assert service.get_evidence("8901719101038") is None

    # Invalid check digit
    assert service.get_evidence("8901058000299") is None

    # Non-numeric / malformed strings
    assert service.get_evidence("INVALID_GTIN") is None
    assert service.get_evidence("") is None
    assert service.get_evidence(None) is None


def test_multiple_product_records_can_coexist(tmp_path: Path):
    """Requirement 4: Multiple product records can coexist in the evidence database."""
    test_evidence_file = tmp_path / "multi_evidence.json"
    multi_catalog = {
        "8901058000290": {
            "product_name": "MAGGI 2-Minute Noodles",
            "evidence_image": "/evidence/8901058000290/evidence.png",
        },
        "8901030712999": {
            "product_name": "Dove Bathing Bar",
            "evidence_image": "/evidence/8901030712999/evidence.png",
        },
        "7622202225024": {
            "product_name": "Cadbury Dairy Milk Silk Desserts Brownie",
            "evidence_image": "/evidence/7622202225024/evidence.png",
        },
    }
    test_evidence_file.write_text(json.dumps(multi_catalog), encoding="utf-8")

    service = ProductEvidenceService(evidence_path=test_evidence_file)

    # 1. Maggi
    maggi = service.get_evidence("8901058000290")
    assert maggi is not None
    assert maggi.product_name == "MAGGI 2-Minute Noodles"
    assert maggi.evidence_image == "/evidence/8901058000290/evidence.png"

    # 2. Dove
    dove = service.get_evidence("8901030712999")
    assert dove is not None
    assert dove.product_name == "Dove Bathing Bar"
    assert dove.evidence_image == "/evidence/8901030712999/evidence.png"

    # 3. Cadbury
    cadbury = service.get_evidence("7622202225024")
    assert cadbury is not None
    assert cadbury.product_name == "Cadbury Dairy Milk Silk Desserts Brownie"
    assert cadbury.evidence_image == "/evidence/7622202225024/evidence.png"


def test_one_gtin_maps_to_one_evidence_image(tmp_path: Path):
    """Requirement 5: Exactly one evidence image per GTIN record."""
    service = ProductEvidenceService()
    catalog = service.get_catalog()

    for gtin, record in catalog.items():
        assert "evidence_image" in record
        assert isinstance(record["evidence_image"], str)
        # Ensure it is a single string path, not a list
        assert not isinstance(record["evidence_image"], (list, dict, tuple))


def test_missing_physical_image_file_does_not_crash_service(tmp_path: Path):
    """Requirement 6: Missing physical image on disk does not crash service or lookup."""
    fake_catalog = tmp_path / "fake_evidence.json"
    fake_catalog.write_text(
        json.dumps({
            "8901058000290": {
                "product_name": "Test Missing Image Product",
                "evidence_image": "/evidence/nonexistent/missing.png",
            }
        }),
        encoding="utf-8",
    )

    service = ProductEvidenceService(evidence_path=fake_catalog)
    record = service.get_evidence("8901058000290")
    assert record is not None
    assert record.evidence_image == "/evidence/nonexistent/missing.png"


@pytest.mark.asyncio
async def test_evidence_lookup_does_not_alter_rule_engine_results():
    """Requirement 7: Evidence lookup does not alter rule-engine inputs, outputs, or verdicts."""
    rule_engine = DeterministicRuleEngine()
    extraction = _build_test_extraction()
    pkg_meta = {"num_images": 1, "panel_labels": ["Front"], "failed_panels": []}

    # Baseline evaluation
    verdict_before = await rule_engine.evaluate_compliance(
        package_metadata=pkg_meta,
        extracted_declarations=extraction,
    )

    # Perform evidence lookups independently
    service = ProductEvidenceService()
    service.get_evidence("8901058000290")
    service.get_evidence("8901030712999")
    service.get_evidence("INVALID")

    # Evaluation after evidence lookup
    verdict_after = await rule_engine.evaluate_compliance(
        package_metadata=pkg_meta,
        extracted_declarations=extraction,
    )

    # Must be completely identical
    assert verdict_before.overall_verdict == verdict_after.overall_verdict
    assert verdict_before.passed_count == verdict_after.passed_count
    assert verdict_before.failed_count == verdict_after.failed_count
    assert verdict_before.review_count == verdict_after.review_count
    assert len(verdict_before.evaluations) == len(verdict_after.evaluations)
    for b, a in zip(verdict_before.evaluations, verdict_after.evaluations):
        assert b.rule_id == a.rule_id
        assert b.status == a.status
        assert b.message == a.message


def test_evidence_lookup_does_not_alter_ocr_results():
    """Requirement 8: Evidence lookup does not alter OCR extraction results in API response."""
    client = TestClient(app)
    png_bytes = _generate_barcode_png_bytes("8901058000290", zxingcpp.BarcodeFormat.EAN13)
    mock_extraction = _build_test_extraction()

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
    extracted_data = data["extraction"]

    assert extracted_data["product_name"]["value"] == mock_extraction.product_name.value
    assert extracted_data["net_quantity"]["value"] == mock_extraction.net_quantity.value
    assert extracted_data["mrp"]["value"] == mock_extraction.mrp.value
    assert extracted_data["manufacturer_name"]["value"] == mock_extraction.manufacturer_name.value


def test_evidence_lookup_does_not_alter_gtin_reconciliation():
    """Requirement 9: Evidence lookup does not alter GTIN reconciliation outcome."""
    client = TestClient(app)
    png_bytes = _generate_barcode_png_bytes("8901058000290", zxingcpp.BarcodeFormat.EAN13)
    mock_extraction = _build_test_extraction()

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

    # GTIN identity reconciliation remains intact
    gtin_id = data.get("gtin_identity")
    assert gtin_id is not None
    assert gtin_id["overall_status"] == "MATCH"
    assert gtin_id["lookup_status"] == "FOUND"

    # Product evidence is populated concurrently and independently
    prod_evidence = data.get("product_evidence")
    assert prod_evidence is not None
    assert prod_evidence["gtin"] == "8901058000290"
    assert prod_evidence["evidence_image"] == "/evidence/8901058000290/evidence.png"


def test_no_product_specific_hardcoded_gtin_ui_conditions():
    """Requirement 10: Static check ensuring no product-specific GTIN conditions in React UI."""
    project_root = Path(__file__).resolve().parents[2]
    frontend_src = project_root / "frontend" / "src"

    viewer_file = frontend_src / "components" / "ProductEvidenceViewer.jsx"
    result_screen_file = frontend_src / "components" / "ResultScreen.jsx"

    assert viewer_file.exists(), "ProductEvidenceViewer.jsx must exist"
    assert result_screen_file.exists(), "ResultScreen.jsx must exist"

    viewer_code = viewer_file.read_text(encoding="utf-8")
    result_screen_code = result_screen_file.read_text(encoding="utf-8")

    # Forbidden product GTINs hardcoded in conditionals
    known_gtins = ["8901058000290", "8901030712999", "7622202225024", "8901030997938"]

    for gtin in known_gtins:
        # Check for conditional checks like `=== "8901058000290"` or `=== '8901058000290'`
        assert f'=== "{gtin}"' not in viewer_code, f"ProductEvidenceViewer has hardcoded check for {gtin}"
        assert f"=== '{gtin}'" not in viewer_code, f"ProductEvidenceViewer has hardcoded check for {gtin}"
        assert f'=== "{gtin}"' not in result_screen_code, f"ResultScreen has hardcoded check for {gtin}"
        assert f"=== '{gtin}'" not in result_screen_code, f"ResultScreen has hardcoded check for {gtin}"


def test_get_evidence_api_endpoint():
    """Test dedicated GET /api/evidence/{gtin} endpoint for 200 and 404 responses."""
    client = TestClient(app)

    # 1. Known Maggi GTIN
    res_maggi = client.get("/api/evidence/8901058000290")
    assert res_maggi.status_code == 200
    data = res_maggi.json()
    assert data["gtin"] == "8901058000290"
    assert data["product_name"] == "MAGGI 2-Minute Noodles"
    assert data["evidence_image"] == "/evidence/8901058000290/evidence.png"

    # 2. Known Cadbury GTIN
    res_cadbury = client.get("/api/evidence/7622202225024")
    assert res_cadbury.status_code == 200
    data_c = res_cadbury.json()
    assert data_c["gtin"] == "7622202225024"
    assert data_c["product_name"] == "Cadbury Dairy Milk Silk Desserts Brownie"
    assert data_c["evidence_image"] == "/evidence/7622202225024/evidence.png"

    # 3. Known Dove Serum Beauty Bar GTIN
    res_dove = client.get("/api/evidence/8901030997938")
    assert res_dove.status_code == 200
    data_d = res_dove.json()
    assert data_d["gtin"] == "8901030997938"
    assert data_d["product_name"] == "Dove Serum Beauty Bar"
    assert data_d["evidence_image"] == "/evidence/8901030997938/evidence.png"

    # 4. Unknown GTIN
    res_unknown = client.get("/api/evidence/8901719101038")
    assert res_unknown.status_code == 404
