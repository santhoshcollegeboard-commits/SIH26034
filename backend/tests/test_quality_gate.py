"""Comprehensive tests for the Image Quality Gate (Step 6).

Covers:
1. Unit tests for StandardImageQualityChecker:
   - High quality image passes
   - Blurry image fails sharpness check
   - Low resolution (< 300x300) image fails resolution check
   - Severely underexposed / dark image fails brightness check
   - Severely overexposed / washed out image fails brightness check
   - Extreme aspect ratio fails framing check
   - Corrupted / invalid image bytes handled safely
2. API integration tests for POST /api/extract with Quality Gate:
   - Good image passes quality gate, calls OCR provider, runs Rule 6
   - Blurry image rejected by quality gate -> OCR provider is NEVER called
   - Low resolution image rejected by quality gate -> OCR provider is NEVER called
   - Dark image rejected by quality gate -> OCR provider is NEVER called
   - Corrupted image rejected by quality gate -> OCR provider is NEVER called
   - Rejection response preserves four-state canonical model: ComplianceVerdict.NOT_ASSESSABLE
   - No API keys or network calls required for any test.
"""

import io
from unittest.mock import AsyncMock, patch

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
# pyrefly: ignore [missing-import]
import pytest
# pyrefly: ignore [missing-import]
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.compliance import ComplianceVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult, SourceRegion
from backend.app.services.quality_service import StandardImageQualityChecker

client = TestClient(app)


# --------------------------------------------------------------------------
# Image Generation Helpers
# --------------------------------------------------------------------------

def _make_good_image(size: tuple[int, int] = (600, 600)) -> bytes:
    """Generate a high-resolution, sharp, properly exposed test image."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(220, 220, 220))
    draw = ImageDraw.Draw(img)
    # High contrast pattern creating strong gradients
    for i in range(0, size[0], 25):
        draw.line([(i, 0), (i, size[1])], fill=(20, 20, 20), width=3)
        draw.line([(0, i), (size[0], i)], fill=(20, 20, 20), width=3)
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_blurred_image(size: tuple[int, int] = (600, 600), blur_radius: int = 15) -> bytes:
    """Generate an image with excessive blur that should fail the focus check."""
    good_bytes = _make_good_image(size)
    img = Image.open(io.BytesIO(good_bytes))
    blurred = img.filter(ImageFilter.GaussianBlur(radius=blur_radius))
    buf = io.BytesIO()
    blurred.save(buf, format="JPEG")
    return buf.getvalue()


def _make_low_res_image(size: tuple[int, int] = (150, 150)) -> bytes:
    """Generate an image below the minimum resolution threshold (300x300)."""
    return _make_good_image(size)


def _make_dark_image(size: tuple[int, int] = (400, 400)) -> bytes:
    """Generate a severely underexposed image (mean luminance < 25.0)."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(10, 10, 10))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_overexposed_image(size: tuple[int, int] = (400, 400)) -> bytes:
    """Generate a severely overexposed image with glare (mean luminance > 245.0)."""
    buf = io.BytesIO()
    img = Image.new("RGB", size, color=(252, 252, 252))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _make_extreme_aspect_image() -> bytes:
    """Generate an image with extreme aspect ratio (e.g. 1000x20)."""
    buf = io.BytesIO()
    img = Image.new("RGB", (1000, 20), color=(128, 128, 128))
    img.save(buf, format="JPEG")
    return buf.getvalue()


def _mock_extraction_result() -> ExtractionResult:
    """Build a standard mock extraction result for API pipeline verification."""
    return ExtractionResult(
        product_name=ExtractedField(
            value="Krackjack Biscuits",
            confidence=0.95,
            source_region=SourceRegion(x=100, y=50, width=200, height=40),
            status="extracted",
        ),
        manufacturer_name=ExtractedField(
            value="Parle Biscuits Pvt Ltd",
            confidence=0.95,
            source_region=SourceRegion(x=80, y=200, width=300, height=35),
            status="extracted",
        ),
        manufacturer_address=ExtractedField(
            value="Mumbai, MH - 400057",
            confidence=0.90,
            source_region=SourceRegion(x=80, y=240, width=280, height=30),
            status="extracted",
        ),
        packer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        importer_name=ExtractedField(value=None, confidence=None, source_region=None, status="not_found"),
        net_quantity=ExtractedField(
            value="176.4 g",
            confidence=0.98,
            source_region=SourceRegion(x=150, y=300, width=100, height=50),
            status="extracted",
        ),
        mrp=ExtractedField(
            value="₹40.00",
            confidence=0.95,
            source_region=SourceRegion(x=100, y=350, width=120, height=40),
            status="extracted",
        ),
        month_year_of_manufacture=ExtractedField(
            value="08/2026",
            confidence=0.90,
            source_region=SourceRegion(x=100, y=400, width=150, height=30),
            status="extracted",
        ),
        consumer_care_details=ExtractedField(
            value="consumer@parle.biz",
            confidence=0.92,
            source_region=SourceRegion(x=80, y=450, width=250, height=30),
            status="extracted",
        ),
    )


# --------------------------------------------------------------------------
# 1. Unit Tests: StandardImageQualityChecker
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_quality_checker_good_image_passes():
    """Good quality image passes all checks and receives a high quality score."""
    checker = StandardImageQualityChecker()
    image_bytes = _make_good_image()

    result = await checker.assess_quality(image_bytes)

    assert result["is_acceptable"] is True
    assert result["overall_score"] >= 0.60
    assert len(result["reasons"]) == 0
    assert result["details"]["resolution"]["passed"] is True
    assert result["details"]["sharpness"]["passed"] is True
    assert result["details"]["brightness"]["passed"] is True
    assert result["details"]["framing"]["passed"] is True


@pytest.mark.asyncio
async def test_quality_checker_blurred_image_fails():
    """Heavily blurred image fails the sharpness check."""
    checker = StandardImageQualityChecker()
    blurred_bytes = _make_blurred_image()

    result = await checker.assess_quality(blurred_bytes)

    assert result["is_acceptable"] is False
    assert result["overall_score"] <= 0.45
    assert any("blurred" in r.lower() for r in result["reasons"])
    assert result["details"]["sharpness"]["passed"] is False


@pytest.mark.asyncio
async def test_quality_checker_low_resolution_fails():
    """Image with resolution below minimum threshold fails."""
    checker = StandardImageQualityChecker()
    low_res_bytes = _make_low_res_image(size=(180, 180))

    result = await checker.assess_quality(low_res_bytes)

    assert result["is_acceptable"] is False
    assert any("resolution" in r.lower() for r in result["reasons"])
    assert result["details"]["resolution"]["passed"] is False


@pytest.mark.asyncio
async def test_quality_checker_dark_image_fails():
    """Severely underexposed / dark image fails brightness check."""
    checker = StandardImageQualityChecker()
    dark_bytes = _make_dark_image()

    result = await checker.assess_quality(dark_bytes)

    assert result["is_acceptable"] is False
    assert any("underexposed" in r.lower() or "dark" in r.lower() for r in result["reasons"])
    assert result["details"]["brightness"]["passed"] is False


@pytest.mark.asyncio
async def test_quality_checker_overexposed_image_fails():
    """Severely overexposed image with glare fails brightness check."""
    checker = StandardImageQualityChecker()
    bright_bytes = _make_overexposed_image()

    result = await checker.assess_quality(bright_bytes)

    assert result["is_acceptable"] is False
    assert any("overexposed" in r.lower() or "glare" in r.lower() for r in result["reasons"])
    assert result["details"]["brightness"]["passed"] is False


@pytest.mark.asyncio
async def test_quality_checker_extreme_aspect_ratio_fails():
    """Image with extreme aspect ratio fails framing check."""
    checker = StandardImageQualityChecker()
    sliver_bytes = _make_extreme_aspect_image()

    result = await checker.assess_quality(sliver_bytes)

    assert result["is_acceptable"] is False
    assert any("aspect ratio" in r.lower() for r in result["reasons"])
    assert result["details"]["framing"]["passed"] is False


@pytest.mark.asyncio
async def test_quality_checker_corrupted_bytes_handled_safely():
    """Random unparseable bytes do not cause an unhandled crash."""
    checker = StandardImageQualityChecker()
    corrupted_bytes = b"\x00\x01\x02\x03CORRUPTED_NOT_AN_IMAGE\xff\xfe"

    result = await checker.assess_quality(corrupted_bytes)

    assert result["is_acceptable"] is False
    assert result["overall_score"] == 0.0
    assert any("corrupted" in r.lower() or "not a valid" in r.lower() for r in result["reasons"])


# --------------------------------------------------------------------------
# 2. Integration Tests: POST /api/extract with Quality Gate
# --------------------------------------------------------------------------

@patch("backend.app.api.extract.get_ocr_provider")
def test_api_quality_gate_passes_and_invokes_ocr(mock_get_provider):
    """When an image passes the quality gate, OCR is invoked and Rule 6 runs."""
    mock_provider = AsyncMock()
    mock_provider.extract.return_value = _mock_extraction_result()
    mock_provider.model_name = "gemini-3.6-flash"
    mock_get_provider.return_value = mock_provider

    good_image = _make_good_image()

    response = client.post(
        "/api/extract",
        files={"image": ("good_package.jpg", io.BytesIO(good_image), "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    # Verify OCR provider was called
    assert mock_get_provider.called
    assert mock_provider.extract.called

    # Verify response structure
    assert data["success"] is True
    assert data["result"] is not None
    assert data["result"]["product_name"]["value"] == "Krackjack Biscuits"
    assert data["compliance"] is not None
    assert data["compliance"]["overall_disposition"] == "PASS"

    # Verify quality metadata is attached
    assert data["quality"] is not None
    assert data["quality"]["is_acceptable"] is True
    assert data["quality"]["overall_score"] >= 0.60


@patch("backend.app.api.extract.get_ocr_provider")
def test_api_quality_gate_blocks_blurry_image_without_ocr(mock_get_provider):
    """When an image is excessively blurred, OCR is NEVER called."""
    mock_provider = AsyncMock()
    mock_get_provider.return_value = mock_provider

    blurry_image = _make_blurred_image()

    response = client.post(
        "/api/extract",
        files={"image": ("blurry_package.jpg", io.BytesIO(blurry_image), "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    # CRITICAL: OCR provider must NEVER be called for failed quality
    assert not mock_get_provider.called
    assert not mock_provider.extract.called

    # Verify safe failure response
    assert data["success"] is False
    assert data["result"] is None
    assert data["error"] is not None
    assert "quality gate failed" in data["error"].lower()

    # Verify canonical four-state disposition is NOT_ASSESSABLE
    assert data["compliance"] is not None
    assert data["compliance"]["overall_disposition"] == ComplianceVerdict.NOT_ASSESSABLE
    assert "quality gate rejected" in data["compliance"]["summary"].lower()

    # Verify quality details report blur
    assert data["quality"] is not None
    assert data["quality"]["is_acceptable"] is False
    assert any("blurred" in r.lower() for r in data["quality"]["reasons"])


@patch("backend.app.api.extract.get_ocr_provider")
def test_api_quality_gate_blocks_low_res_image_without_ocr(mock_get_provider):
    """When an image is low resolution (< 300x300), OCR is NEVER called."""
    mock_provider = AsyncMock()
    mock_get_provider.return_value = mock_provider

    low_res_image = _make_low_res_image(size=(120, 120))

    response = client.post(
        "/api/extract",
        files={"image": ("low_res.jpg", io.BytesIO(low_res_image), "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    # OCR provider must not be called
    assert not mock_get_provider.called

    assert data["success"] is False
    assert data["result"] is None
    assert data["compliance"]["overall_disposition"] == ComplianceVerdict.NOT_ASSESSABLE
    assert any("resolution" in r.lower() for r in data["quality"]["reasons"])


@patch("backend.app.api.extract.get_ocr_provider")
def test_api_quality_gate_blocks_dark_image_without_ocr(mock_get_provider):
    """When an image is dark / underexposed, OCR is NEVER called."""
    mock_provider = AsyncMock()
    mock_get_provider.return_value = mock_provider

    dark_image = _make_dark_image()

    response = client.post(
        "/api/extract",
        files={"image": ("dark.jpg", io.BytesIO(dark_image), "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    assert not mock_get_provider.called
    assert data["success"] is False
    assert data["result"] is None
    assert data["compliance"]["overall_disposition"] == ComplianceVerdict.NOT_ASSESSABLE
    assert any("underexposed" in r.lower() or "dark" in r.lower() for r in data["quality"]["reasons"])


@patch("backend.app.api.extract.get_ocr_provider")
def test_api_quality_gate_blocks_corrupted_payload_without_ocr(mock_get_provider):
    """When raw uploaded bytes cannot be decoded, OCR is NEVER called."""
    mock_provider = AsyncMock()
    mock_get_provider.return_value = mock_provider

    corrupted_bytes = b"NOT_A_VALID_IMAGE_PAYLOAD_CORRUPTED"

    response = client.post(
        "/api/extract",
        files={"image": ("corrupted.jpg", io.BytesIO(corrupted_bytes), "image/jpeg")},
    )

    assert response.status_code == 200
    data = response.json()

    assert not mock_get_provider.called
    assert data["success"] is False
    assert data["result"] is None
    assert data["compliance"]["overall_disposition"] == ComplianceVerdict.NOT_ASSESSABLE
    assert any("corrupted" in r.lower() or "not a valid" in r.lower() for r in data["quality"]["reasons"])
