"""Tests for the POST /api/extract endpoint.

All tests use mocked OCR providers — no real Gemini API calls.
No API keys required.
"""

import io
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.extraction import ExtractionResult, ExtractedField, SourceRegion

client = TestClient(app)


def _make_test_image(content_type: str = "image/jpeg") -> tuple[io.BytesIO, str]:
    """Create a minimal fake image for testing uploads."""
    # A small valid-ish binary payload (not a real image, but sufficient for upload testing)
    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    fake_image.name = "test_package.jpg"
    return fake_image, content_type


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
