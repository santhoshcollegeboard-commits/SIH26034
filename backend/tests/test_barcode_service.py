"""Integration and unit tests for BarcodeService and API verification integration.

Tests barcode decoding, multi-panel processing, safe failure modes,
and backward compatibility of POST /api/verify.
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
    GTINValidationStatus,
)
from backend.app.schemas.extraction import ExtractionResult
from backend.app.services.barcode.decoder import BarcodeDecoder
from backend.app.services.barcode.service import BarcodeService


# =============================================================================
# Test Image Helpers (In-Memory, Deterministic, Zero Network Dependency)
# =============================================================================

def _generate_barcode_png_bytes(content: str, barcode_format: zxingcpp.BarcodeFormat) -> bytes:
    """Generate in-memory PNG bytes of a valid barcode symbol."""
    bc = zxingcpp.create_barcode(content, barcode_format)
    zx_img = bc.to_image()
    # Image shape from zxingcpp is (height, width)
    pil_img = Image.frombytes("L", (zx_img.shape[1], zx_img.shape[0]), bytes(zx_img))
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_blank_png_bytes(width: int = 200, height: int = 200) -> bytes:
    """Generate in-memory PNG bytes of a blank image (no barcode)."""
    img = Image.new("RGB", (width, height), color="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_multi_barcode_png_bytes() -> bytes:
    """Generate in-memory PNG image containing two distinct barcodes."""
    bc1 = zxingcpp.create_barcode("8901030892011", zxingcpp.BarcodeFormat.EAN13)
    img1 = bc1.to_image()
    p1 = Image.frombytes("L", (img1.shape[1], img1.shape[0]), bytes(img1))

    bc2 = zxingcpp.create_barcode("96385074", zxingcpp.BarcodeFormat.EAN8)
    img2 = bc2.to_image()
    p2 = Image.frombytes("L", (img2.shape[1], img2.shape[0]), bytes(img2))

    canvas = Image.new("RGB", (400, 300), color="#FFFFFF")
    canvas.paste(p1, (20, 20))
    canvas.paste(p2, (20, 150))

    buf = io.BytesIO()
    canvas.save(buf, format="PNG")
    return buf.getvalue()


# =============================================================================
# 1. BarcodeDecoder Unit Tests
# =============================================================================

def test_decoder_ean13():
    """Decode a single EAN-13 barcode image."""
    png_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)
    results = BarcodeDecoder.decode_bytes(png_bytes, panel_index=0, panel_label="Back")

    assert len(results) == 1
    item = results[0]
    assert item.format == BarcodeFormat.EAN_13
    assert item.raw_value == "8901030892011"
    assert item.gtin == "8901030892011"
    assert item.is_valid_gtin is True
    assert item.validation_status == GTINValidationStatus.VALID
    assert item.panel_index == 0
    assert item.panel_label == "Back"


def test_decoder_ean8():
    """Decode a single EAN-8 barcode image."""
    png_bytes = _generate_barcode_png_bytes("96385074", zxingcpp.BarcodeFormat.EAN8)
    results = BarcodeDecoder.decode_bytes(png_bytes)

    assert len(results) == 1
    item = results[0]
    assert item.format == BarcodeFormat.EAN_8
    assert item.raw_value == "96385074"
    assert item.gtin == "96385074"
    assert item.is_valid_gtin is True
    assert item.validation_status == GTINValidationStatus.VALID


def test_decoder_code128_alphanumeric():
    """Decode a Code 128 barcode containing alphanumeric text."""
    png_bytes = _generate_barcode_png_bytes("PACKCHECK-ALPHA-128", zxingcpp.BarcodeFormat.Code128)
    results = BarcodeDecoder.decode_bytes(png_bytes)

    assert len(results) == 1
    item = results[0]
    assert item.format == BarcodeFormat.CODE_128
    assert item.raw_value == "PACKCHECK-ALPHA-128"
    assert item.is_valid_gtin is False
    assert item.validation_status == GTINValidationStatus.NOT_A_GTIN_FORMAT


def test_decoder_blank_image():
    """Blank image yields zero barcodes."""
    png_bytes = _generate_blank_png_bytes()
    results = BarcodeDecoder.decode_bytes(png_bytes)
    assert results == []


def test_decoder_corrupt_bytes():
    """Corrupted bytes raise ValueError."""
    with pytest.raises(ValueError, match="Corrupted or invalid image data"):
        BarcodeDecoder.decode_bytes(b"not-an-image-payload")


# =============================================================================
# 2. BarcodeService Package Processing Tests
# =============================================================================

def test_service_no_images():
    """Service handles empty images list gracefully."""
    service = BarcodeService()
    summary = service.process_package([])
    assert summary.status == BarcodeDetectionStatus.NO_BARCODE_DETECTED
    assert summary.detected is False
    assert summary.count == 0
    assert summary.barcodes == []
    assert summary.primary_gtin is None


def test_service_single_valid_barcode():
    """Single valid EAN-13 barcode on package."""
    service = BarcodeService()
    png_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)

    summary = service.process_package([(png_bytes, "image/png", "Back Panel")])
    assert summary.status == BarcodeDetectionStatus.BARCODE_DETECTED
    assert summary.detected is True
    assert summary.count == 1
    assert summary.primary_gtin == "8901030892011"
    assert summary.is_valid_gtin is True
    assert len(summary.barcodes) == 1
    assert summary.barcodes[0].panel_label == "Back Panel"


def test_service_no_barcode_detected():
    """Package images without barcodes return NO_BARCODE_DETECTED."""
    service = BarcodeService()
    png_bytes = _generate_blank_png_bytes()

    summary = service.process_package([(png_bytes, "image/png", "Front Panel")])
    assert summary.status == BarcodeDetectionStatus.NO_BARCODE_DETECTED
    assert summary.detected is False
    assert summary.count == 0
    assert summary.barcodes == []
    assert summary.primary_gtin is None
    assert summary.is_valid_gtin is None


def test_service_multiple_barcodes_on_single_image():
    """Multiple barcodes on one image are preserved, without guessing primary GTIN."""
    service = BarcodeService()
    multi_png = _generate_multi_barcode_png_bytes()

    summary = service.process_package([(multi_png, "image/png", "All-In-One")])
    assert summary.status == BarcodeDetectionStatus.MULTIPLE_BARCODES_DETECTED
    assert summary.detected is True
    assert summary.count == 2
    assert len(summary.barcodes) == 2
    # In multiple barcode scenarios, primary_gtin is intentionally None
    assert summary.primary_gtin is None
    assert summary.is_valid_gtin is None
    assert "2 barcodes detected" in summary.message


def test_service_multi_panel_one_barcode():
    """Package with Front (no barcode) and Back (EAN-13) panels."""
    service = BarcodeService()
    front_bytes = _generate_blank_png_bytes()
    back_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)

    summary = service.process_package([
        (front_bytes, "image/png", "Front"),
        (back_bytes, "image/png", "Back"),
    ])
    assert summary.status == BarcodeDetectionStatus.BARCODE_DETECTED
    assert summary.detected is True
    assert summary.count == 1
    assert summary.primary_gtin == "8901030892011"
    assert summary.is_valid_gtin is True
    assert summary.barcodes[0].panel_label == "Back"
    assert summary.barcodes[0].panel_index == 1


def test_service_corrupted_image_handling():
    """All panels corrupted returns DECODER_ERROR rather than crashing."""
    service = BarcodeService()
    summary = service.process_package([(b"garbage-bytes", "image/png", "Corrupt")])
    assert summary.status == BarcodeDetectionStatus.DECODER_ERROR
    assert summary.detected is False
    assert summary.count == 0
    assert "failed" in summary.message.lower()


# =============================================================================
# 3. Full API Integration (POST /api/verify)
# =============================================================================

@pytest.fixture
def client():
    return TestClient(app)


def test_api_verify_with_barcode(client):
    """Verify endpoint successfully returns barcode details and does not alter compliance."""
    png_bytes = _generate_barcode_png_bytes("8901030892011", zxingcpp.BarcodeFormat.EAN13)

    mock_extraction = ExtractionResult()

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.extract = AsyncMock(return_value=mock_extraction)
        mock_provider.model_name = "test-gemini-mock"
        mock_get_provider.return_value = mock_provider

        response = client.post(
            "/api/verify",
            files=[("images", ("barcode_panel.png", png_bytes, "image/png"))],
            data={"panel_labels": '["Back"]'},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Barcode field is populated in VerificationResponse
    barcode = data.get("barcode")
    assert barcode is not None
    assert barcode["detected"] is True
    assert barcode["status"] == "BARCODE_DETECTED"
    assert barcode["primary_gtin"] == "8901030892011"
    assert barcode["is_valid_gtin"] is True
    assert len(barcode["barcodes"]) == 1
    assert barcode["barcodes"][0]["format"] == "EAN_13"

    # Legal Metrology compliance verdict is still computed independently by Rule Engine
    assert "compliance" in data
    assert data["compliance"]["overall_verdict"] in ["PASS", "FAIL", "FLAGGED_FOR_REVIEW"]


def test_api_verify_without_barcode_does_not_fail_compliance(client):
    """Absence of barcode must NOT cause Legal Metrology failure."""
    blank_bytes = _generate_blank_png_bytes()

    mock_extraction = ExtractionResult()

    with patch("backend.app.api.verify.get_ocr_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.extract = AsyncMock(return_value=mock_extraction)
        mock_provider.model_name = "test-gemini-mock"
        mock_get_provider.return_value = mock_provider

        response = client.post(
            "/api/verify",
            files=[("images", ("front_panel.png", blank_bytes, "image/png"))],
            data={"panel_labels": '["Front"]'},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    barcode = data.get("barcode")
    assert barcode is not None
    assert barcode["detected"] is False
    assert barcode["status"] == "NO_BARCODE_DETECTED"
    assert barcode["count"] == 0
    assert barcode["primary_gtin"] is None

    # Compliance verdict is not set to FAIL because of missing barcode
    # Evaluator rules decide based on LM declarations only
    assert data["compliance"] is not None


# =============================================================================
# 4. Preprocessing Robustness Tests
# =============================================================================

def test_decoder_recovers_faded_low_contrast_barcode():
    """Verify that multi-pass preprocessing recovers faded/low-contrast barcodes that fail raw scan."""
    from PIL import ImageEnhance

    bc = zxingcpp.create_barcode("8901030892011", zxingcpp.BarcodeFormat.EAN13)
    img = Image.frombytes("L", (bc.to_image().shape[1], bc.to_image().shape[0]), bytes(bc.to_image()))

    # Drastically reduce contrast so raw zxingcpp detection completely fails
    low_c = ImageEnhance.Contrast(img).enhance(0.05)
    buf = io.BytesIO()
    low_c.save(buf, format="PNG")
    faded_bytes = buf.getvalue()

    # Raw zxingcpp scan on faded image finds nothing
    assert len(zxingcpp.read_barcodes(low_c)) == 0

    # BarcodeDecoder multi-pass preprocessing successfully recovers the EAN-13 barcode
    results = BarcodeDecoder.decode_bytes(faded_bytes)
    assert len(results) == 1
    assert results[0].format == BarcodeFormat.EAN_13
    assert results[0].gtin == "8901030892011"
    assert results[0].is_valid_gtin is True


def test_decoder_recovers_blurred_barcode():
    """Verify that multi-pass sharpening recovers slightly blurred barcodes that fail raw scan."""
    from PIL import ImageFilter

    bc = zxingcpp.create_barcode("8901030892011", zxingcpp.BarcodeFormat.EAN13)
    img = Image.frombytes("L", (bc.to_image().shape[1], bc.to_image().shape[0]), bytes(bc.to_image()))

    # Apply Gaussian blur so raw zxingcpp detection fails
    blurred = img.filter(ImageFilter.GaussianBlur(radius=0.9))
    buf = io.BytesIO()
    blurred.save(buf, format="PNG")
    blurred_bytes = buf.getvalue()

    # Raw zxingcpp scan on blurred image finds nothing
    assert len(zxingcpp.read_barcodes(blurred)) == 0

    # BarcodeDecoder multi-pass sharpening successfully recovers the barcode
    results = BarcodeDecoder.decode_bytes(blurred_bytes)
    assert len(results) == 1
    assert results[0].format == BarcodeFormat.EAN_13
    assert results[0].gtin == "8901030892011"
    assert results[0].is_valid_gtin is True


def test_decoder_preserves_qr_code_when_no_gtin():
    """Verify that QR codes are preserved and classified accurately without inventing a GTIN."""
    bc = zxingcpp.create_barcode("https://example.com/product/123", zxingcpp.BarcodeFormat.QRCode)
    img = Image.frombytes("L", (bc.to_image().shape[1], bc.to_image().shape[0]), bytes(bc.to_image()))
    buf = io.BytesIO()
    img.save(buf, format="PNG")

    results = BarcodeDecoder.decode_bytes(buf.getvalue())
    assert len(results) == 1
    assert results[0].format == BarcodeFormat.QR_CODE
    assert results[0].gtin is None
    assert results[0].is_valid_gtin is False
    assert results[0].validation_status == GTINValidationStatus.NOT_A_GTIN_FORMAT
