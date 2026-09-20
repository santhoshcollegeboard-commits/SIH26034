"""Integration tests for the POST /api/verify endpoint.

All tests mock the OCR provider — no network or API keys required.
Deterministic rule verification executes end-to-end.
"""

import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.extraction import ExtractedField, ExtractionResult, SourceRegion

client = TestClient(app)


def _make_test_image(content_type: str = "image/jpeg") -> tuple[io.BytesIO, str]:
    """Create a minimal fake image payload for testing uploads."""
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    fake_image.name = "sample_commodity.jpg"
    return fake_image, content_type


def _make_mock_compliant_result() -> ExtractionResult:
    """Mock compliant package extraction."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Assam Gold Premium",
            confidence=0.98,
            source_region=SourceRegion(x=100, y=50, width=300, height=40),
            status="extracted",
        ),
        common_or_generic_name=ExtractedField(
            value="CTC Black Tea",
            confidence=0.97,
            source_region=SourceRegion(x=100, y=95, width=200, height=30),
            status="extracted",
        ),
        manufacturer_name=ExtractedField(
            value="Himalayan Highlands Tea Estates Pvt. Ltd.",
            confidence=0.94,
            source_region=SourceRegion(x=80, y=200, width=300, height=35),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Plot 42, Tea Park Road, Dibrugarh, Assam - 786001",
            confidence=0.91,
            source_region=SourceRegion(x=80, y=240, width=280, height=30),
            status="extracted",
        ),
        packer_name=ExtractedField(value=None, status="not_found"),
        importer_name=ExtractedField(value=None, status="not_found"),
        country_of_origin=ExtractedField(value="India", status="extracted"),
        net_quantity=ExtractedField(
            value="500 g",
            confidence=0.97,
            source_region=SourceRegion(x=150, y=300, width=100, height=50),
            status="extracted",
        ),
        mrp=ExtractedField(
            value="₹ 245.00 (Inclusive of all taxes) | USP: ₹ 0.49 per g",
            confidence=0.96,
            source_region=SourceRegion(x=200, y=350, width=200, height=40),
            status="extracted",
        ),
        month_year_of_manufacture=ExtractedField(
            value="08/2026",
            confidence=0.88,
            source_region=SourceRegion(x=100, y=400, width=150, height=30),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="Toll-Free: 1800-209-8899 | care@tea.in",
            confidence=0.92,
            source_region=SourceRegion(x=80, y=450, width=250, height=30),
            status="extracted",
        ),
    )


def _make_mock_defective_result() -> ExtractionResult:
    """Mock defective package with prohibited units and missing tax wording."""
    return ExtractionResult(
        product_name=ExtractedField(value="Crunchy Bites Chips", status="extracted"),
        manufacturer_name=ExtractedField(value="SnackCo Ltd", status="extracted"),
        manufacturer_address=ExtractedField(value="Industrial Phase 1", status="extracted"),
        packer_name=ExtractedField(value=None, status="not_found"),
        importer_name=ExtractedField(value=None, status="not_found"),
        net_quantity=ExtractedField(value="75", status="extracted"),  # Bare number defect
        mrp=ExtractedField(value="Price: 30", status="extracted"),     # Missing tax disclaimer defect
        month_year_of_manufacture=ExtractedField(value="05/2026", status="extracted"),
        consumer_care_details=ExtractedField(value=None, status="not_found"),
    )


@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_compliant_package(mock_get_provider):
    """POST /api/verify returns PASS verdict for compliant commodity image."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _make_mock_compliant_result()
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/verify",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["extraction"] is not None
    assert data["compliance"] is not None
    assert data["compliance"]["overall_verdict"] == "PASS"
    assert data["compliance"]["failed_count"] == 0
    assert len(data["compliance"]["evaluations"]) >= 7


@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_defective_package(mock_get_provider):
    """POST /api/verify correctly identifies statutory defects and returns FAIL."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _make_mock_defective_result()
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/verify",
        files={"image": ("defective_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["compliance"]["overall_verdict"] == "FAIL"
    assert data["compliance"]["failed_count"] >= 2


@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_provider_error(mock_get_provider):
    """POST /api/verify handles OCR failure gracefully."""
    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = RuntimeError("Quota exhausted")
    mock_provider.model_name = "gemini-flash-latest"
    mock_get_provider.return_value = mock_provider

    fake_image, content_type = _make_test_image()

    response = client.post(
        "/api/verify",
        files={"image": ("test_package.jpg", fake_image, content_type)},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["compliance"] is None
    assert "error" in data
    assert "Quota" in data["error"]


def test_verify_endpoint_rejects_non_image():
    """POST /api/verify rejects non-image formats."""
    fake_file = io.BytesIO(b"Just some text, not an image")
    response = client.post(
        "/api/verify",
        files={"image": ("document.pdf", fake_file, "application/pdf")},
    )
    assert response.status_code == 400
    assert "Unsupported image type" in response.json()["detail"]


def test_verify_endpoint_rejects_empty_file():
    """POST /api/verify rejects zero-byte uploads."""
    empty_file = io.BytesIO(b"")
    response = client.post(
        "/api/verify",
        files={"image": ("empty.jpg", empty_file, "image/jpeg")},
    )
    assert response.status_code == 400
    assert "empty" in response.json()["detail"].lower()
