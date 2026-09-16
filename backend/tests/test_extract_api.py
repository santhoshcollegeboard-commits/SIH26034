"""Tests for the POST /api/extract endpoint.

All tests use mocked OCR providers — no real Gemini API calls.
No API keys required.
"""

import io
from unittest.mock import AsyncMock, patch

# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.extraction import ExtractionResult, ExtractedField, SourceRegion

client = TestClient(app)


def _make_test_image(content_type: str = "image/jpeg", size: tuple = (400, 400)) -> tuple[io.BytesIO, str]:
    """Create a valid in-memory image that passes quality checks for endpoint testing."""
    from PIL import Image, ImageDraw

    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(240, 240, 240))
    draw = ImageDraw.Draw(img)
    # Add high-contrast lines to ensure adequate Laplacian variance / focus score
    for i in range(0, size[0], 20):
        draw.line([(i, 0), (i, size[1])], fill=(20, 20, 20), width=2)
    fmt = "PNG" if "png" in content_type else "WEBP" if "webp" in content_type else "JPEG"
    img.save(buf, format=fmt)
    buf.seek(0)
    buf.name = f"test_package.{fmt.lower()}"
    return buf, content_type


def _mock_extraction_result() -> ExtractionResult:
    """Build a realistic mock extraction result."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Tata Salt",
            confidence=0.95,
            source_region=SourceRegion(x=100, y=50, width=200, height=40),
            status="extracted",
        ),
        manufacturer_name=ExtractedField(
            value="Tata Consumer Products Ltd",
            confidence=0.92,
            source_region=SourceRegion(x=80, y=200, width=300, height=35),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Kolkata, West Bengal",
            confidence=0.88,
            source_region=SourceRegion(x=80, y=240, width=280, height=30),
            status="extracted",
        ),
        packer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        importer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        net_quantity=ExtractedField(
            value="1 kg",
            confidence=0.97,
            source_region=SourceRegion(x=150, y=300, width=100, height=50),
            status="extracted",
        ),
        mrp=ExtractedField(
            value="₹28.00",
            confidence=0.93,
            source_region=SourceRegion(x=200, y=350, width=120, height=40),
            status="extracted",
        ),
        month_year_of_manufacture=ExtractedField(
            value="Aug 2026",
            confidence=0.85,
            source_region=SourceRegion(x=100, y=400, width=150, height=30),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="1800-209-8765",
            confidence=0.90,
            source_region=SourceRegion(x=80, y=450, width=250, height=30),
            status="extracted",
        ),
    )


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_endpoint_success(mock_get_provider):
    """POST /api/extract returns structured JSON when provider succeeds."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _mock_extraction_result()
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["result"] is not None
    assert data["result"]["product_name"]["value"] == "Tata Salt"
    assert data["result"]["product_name"]["status"] == "extracted"
    assert data["result"]["packer_name"]["status"] == "not_found"
    assert data["result"]["packer_name"]["value"] is None
    assert data["model_used"] == "gemini-flash-latest"
    assert data["processing_time_ms"] is not None


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_endpoint_provider_error(mock_get_provider):
    """POST /api/extract returns error gracefully when provider fails."""
    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = RuntimeError("Gemini API quota exceeded")
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["error"] is not None
    assert "quota" in data["error"].lower()


def test_extract_endpoint_rejects_non_image():
    """POST /api/extract rejects non-image file types."""
    fake_file = io.BytesIO(b"not an image, just text")

    response = client.post(
        "/api/extract",
        files={"image": ("document.txt", fake_file, "text/plain")},
    )

    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]


def test_extract_endpoint_rejects_empty_file():
    """POST /api/extract rejects empty uploads."""
    empty_file = io.BytesIO(b"")

    response = client.post(
        "/api/extract",
        files={"image": ("empty.jpg", empty_file, "image/jpeg")},
    )

    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_triggers_rule_6_compliant_pass(mock_get_provider):
    """Successful compliant extraction triggers Rule 6 producing overall PASS with traceability."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _mock_extraction_result()
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["compliance"] is not None
    assert data["compliance"]["overall_verdict"] == "PASS"
    assert data["compliance"]["overall_disposition"] == "PASS"
    assert len(data["compliance"]["rule_evaluations"]) == 9

    # Verify Rule 6 traceability
    for item in data["compliance"]["rule_evaluations"]:
        assert item["rule_id"].startswith("LMR-2011-R06-")
        assert item["rule_version"] == "LMR-2011-BASE-R06"
        assert item["status"] in ("PASS", "FAIL", "REVIEW_REQUIRED", "NOT_ASSESSABLE")
        assert len(item["explanation"]) > 0


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_triggers_rule_6_non_compliant_fail(mock_get_provider):
    """Missing mandatory field (MRP) produces overall FAIL via Rule 6."""
    mock_res = _mock_extraction_result()
    mock_res.mrp = ExtractedField(
        value=None, confidence=None, source_region=None, status="not_found"
    )

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = mock_res
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["compliance"] is not None
    assert data["compliance"]["overall_verdict"] == "FAIL"

    mrp_eval = next(
        e for e in data["compliance"]["rule_evaluations"] if e["rule_id"] == "LMR-2011-R06-01E-MRP"
    )
    assert mrp_eval["status"] == "FAIL"


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_low_confidence_triggers_review_required(mock_get_provider):
    """Low-confidence date declaration (<0.70) triggers overall REVIEW_REQUIRED."""
    mock_res = _mock_extraction_result()
    mock_res.month_year_of_manufacture = ExtractedField(
        value="08/2026", confidence=0.55, status="extracted"
    )

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = mock_res
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["compliance"] is not None
    assert data["compliance"]["overall_verdict"] == "REVIEW_REQUIRED"


@patch("backend.app.api.extract.get_rule_engine")
@patch("backend.app.api.extract.get_ocr_provider")
def test_extraction_failure_does_not_call_rule_engine(mock_get_provider, mock_get_engine):
    """When OCR provider fails, RuleEngine is never called."""
    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = RuntimeError("OCR service unavailable")
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["compliance"] is None
    mock_get_engine.assert_not_called()


@patch("backend.app.api.extract.get_rule_engine")
@patch("backend.app.api.extract.get_ocr_provider")
def test_rule_engine_failure_handled_safely(mock_get_provider, mock_get_engine):
    """When RuleEngine raises an unexpected exception, API returns safe error without leaking stack trace."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _mock_extraction_result()
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    mock_engine = AsyncMock()
    mock_engine.evaluate.side_effect = RuntimeError("Simulated unexpected engine fault")
    mock_get_engine.return_value = mock_engine

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["compliance"] is None
    assert "Compliance evaluation failed" in data["error"]
    assert "Simulated unexpected engine fault" not in data["error"]  # Internal details sanitized


@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_with_package_metadata_imported_fails_missing_importer(mock_get_provider):
    """When package is flagged as imported, missing importer produces FAIL."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _mock_extraction_result()  # Has no importer
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/extract",
        files={"image": ("test_package.jpg", fake_image, content_type)},
        data={"is_imported": "true"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["compliance"]["overall_verdict"] == "FAIL"

    importer_eval = next(
        e for e in data["compliance"]["rule_evaluations"] if e["rule_id"] == "LMR-2011-R06-01A-IMPORTER"
    )
    assert importer_eval["status"] == "FAIL"

