"""Integration tests for multi-image / multi-panel verification API."""

import io
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.schemas.compliance import OverallVerdict
from backend.app.schemas.extraction import ExtractedField, ExtractionResult

client = TestClient(app)

DUMMY_JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb"


def _make_field(val: str | None, status: str = "extracted", conf: float = 0.95):
    return ExtractedField(value=val, confidence=conf if val else None, status=status)


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_multi_image_complementary(mock_get_provider, mock_settings):
    """Multiple images with complementary declarations merge and yield PASS."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    # Front panel extraction
    front_extraction = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Black Tea"),
        net_quantity=_make_field("500 g"),
    )

    # Back panel extraction
    back_extraction = ExtractionResult(
        manufacturer_name=_make_field("Himalayan Highlands Ltd"),
        manufacturer_address=_make_field("Plot 42, Tea Park Road, Dibrugarh, Assam - 786001"),
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes) | USP: ₹ 0.49 per g"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Toll-Free: 1800-209-8899"),
        country_of_origin=_make_field("India"),
    )

    mock_provider = AsyncMock()
    # Return front for 1st call, back for 2nd call
    mock_provider.extract.side_effect = [front_extraction, back_extraction]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("front.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("back.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"panel_labels": ["Front", "Back"]}

    response = client.post("/api/verify", files=files, data=data)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["image_count"] == 2
    assert res_json["panel_labels"] == ["Front", "Back"]

    # Rule engine evaluates merged declarations
    compliance = res_json["compliance"]
    assert compliance["overall_verdict"] == OverallVerdict.PASS.value
    assert compliance["failed_count"] == 0

    # Check extraction provenance
    ext = res_json["extraction"]
    assert ext["product_name"]["value"] == "Assam Gold"
    assert ext["product_name"]["source_panel_label"] == "Front"
    assert ext["manufacturer_name"]["value"] == "Himalayan Highlands Ltd"
    assert ext["manufacturer_name"]["source_panel_label"] == "Back"


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_multi_image_conflicting(mock_get_provider, mock_settings):
    """Contradictory values on two panels produce FLAGGED_FOR_REVIEW."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    panel1 = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Tea"),
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 100 (Inclusive of all taxes)"),
        manufacturer_name=_make_field("Apex Foods Ltd"),
        manufacturer_address=_make_field("Plot 4, Industrial Area, Pune - 411018"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Phone: 1800-209-8899"),
    )
    panel2 = ExtractionResult(
        mrp=_make_field("₹ 250 (Inclusive of all taxes)"),  # Conflicting price!
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [panel1, panel2]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("p1.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("p2.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]

    response = client.post("/api/verify", files=files)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["compliance"]["overall_verdict"] == OverallVerdict.FLAGGED_FOR_REVIEW.value
    assert res_json["extraction"]["mrp"]["status"] == "conflict"


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_single_panel_failure_resilience(mock_get_provider, mock_settings):
    """If 1 of 2 panels throws an OCR error, the other is still processed."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    panel1 = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Tea"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [panel1, RuntimeError("Vision API timeout on panel 2")]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("p1.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("p2.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]

    response = client.post("/api/verify", files=files)

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    # Panel 1 succeeded
    assert res_json["extraction"]["product_name"]["value"] == "Assam Gold"
    # Note added to summary about failed panel
    assert "could not be parsed" in res_json["compliance"]["summary"]


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.extract.get_ocr_provider")
def test_extract_endpoint_multi_image(mock_get_provider, mock_settings):
    """POST /api/extract supports multiple images and aggregates results."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    front_extraction = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        net_quantity=_make_field("500 g"),
    )
    back_extraction = ExtractionResult(
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes)"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [front_extraction, back_extraction]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("front.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("back.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]

    response = client.post("/api/extract", files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["result"]["product_name"]["value"] == "Assam Gold"
    assert res_json["result"]["mrp"]["value"] == "₹ 245.00 (Inclusive of all taxes)"


def test_verify_endpoint_rejects_empty_file_list():
    """POST /api/verify with no files returns 400."""
    response = client.post("/api/verify")
    assert response.status_code == 400
    assert "No package image files uploaded" in response.json()["detail"]


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_endpoint_single_image_backward_compatibility(mock_get_provider, mock_settings):
    """POST /api/verify with legacy single 'image' field continues to work seamlessly."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    extraction = ExtractionResult(
        product_name=_make_field("Assam Gold"),
        common_or_generic_name=_make_field("CTC Black Tea"),
        net_quantity=_make_field("500 g"),
        mrp=_make_field("₹ 245.00 (Inclusive of all taxes) | USP: ₹ 0.49 per g"),
        manufacturer_name=_make_field("Himalayan Highlands Ltd"),
        manufacturer_address=_make_field("Plot 42, Tea Park Road, Dibrugarh, Assam - 786001"),
        month_year_of_manufacture=_make_field("08/2026"),
        consumer_care_details=_make_field("Toll-Free: 1800-209-8899"),
        country_of_origin=_make_field("India"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = extraction
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    # Legacy client sends single file under name 'image'
    files = {"image": ("package.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")}

    response = client.post("/api/verify", files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["success"] is True
    assert res_json["image_count"] == 1
    assert res_json["compliance"]["overall_verdict"] == OverallVerdict.PASS.value

