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


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_single_uploaded_image_produces_exactly_one_panel(mock_get_provider, mock_settings):
    """Regression: 1 uploaded image produces exactly 1 panel with zero phantom panels or conflicts."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    extraction = ExtractionResult(
        product_name=_make_field("MAGGI 2-Minute Noodles"),
        common_or_generic_name=_make_field("Masala Noodles"),
        net_quantity=_make_field("70 g"),
        mrp=_make_field("₹ 15.00 (incl. of all taxes)"),
        manufacturer_name=_make_field("Nestlé India Limited"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = extraction
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [("images", ("maggi.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg"))]
    data = {"panel_labels": ["Front Panel"]}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    # Exact count checks
    assert res["image_count"] == 1
    assert res["panel_labels"] == ["Front Panel"]
    assert len(res["per_image_extractions"]) == 1

    # Zero phantom panels or cross-panel conflicts
    assert "Panel 2" not in res["panel_labels"]
    assert res["extraction"]["product_name"]["status"] != "conflict"
    assert res["extraction"]["net_quantity"]["status"] != "conflict"
    assert "conflicting" not in (res["compliance"]["summary"] or "").lower()


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_single_image_with_compat_field_does_not_duplicate_panel(mock_get_provider, mock_settings):
    """Regression: If client redundantly sends both 'images' and 'image', 'images' takes precedence and 1 panel is created."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    extraction = ExtractionResult(
        product_name=_make_field("MAGGI 2-Minute Noodles"),
        net_quantity=_make_field("70 g"),
    )

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = extraction
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    # Redundant payload: both 'images' and 'image' sent with same file
    files = [
        ("images", ("maggi.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("image", ("maggi.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"panel_labels": ["Front Panel"]}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["image_count"] == 1
    assert res["panel_labels"] == ["Front Panel"]
    assert len(res["per_image_extractions"]) == 1
    assert "Panel 2" not in res["panel_labels"]


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_two_real_images_produce_exactly_two_panels(mock_get_provider, mock_settings):
    """Regression: 2 distinct uploaded images produce exactly 2 panels."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext1 = ExtractionResult(product_name=_make_field("Brand Front"))
    ext2 = ExtractionResult(mrp=_make_field("₹ 100.00"))

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [ext1, ext2]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("panel_front.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("panel_back.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"panel_labels": ["Front Panel", "Back Panel"]}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["image_count"] == 2
    assert res["panel_labels"] == ["Front Panel", "Back Panel"]
    assert len(res["per_image_extractions"]) == 2


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_verify_three_real_images_produce_exactly_three_panels(mock_get_provider, mock_settings):
    """Regression: 3 distinct uploaded images produce exactly 3 panels."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext1 = ExtractionResult(product_name=_make_field("Brand Front"))
    ext2 = ExtractionResult(mrp=_make_field("₹ 100.00"))
    ext3 = ExtractionResult(net_quantity=_make_field("50 g"))

    mock_provider = AsyncMock()
    mock_provider.extract.side_effect = [ext1, ext2, ext3]
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    files = [
        ("images", ("front.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("back.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("side.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    data = {"panel_labels": ["Front Panel", "Back Panel", "Side Panel"]}

    response = client.post("/api/verify", files=files, data=data)
    assert response.status_code == 200
    res = response.json()

    assert res["image_count"] == 3
    assert res["panel_labels"] == ["Front Panel", "Back Panel", "Side Panel"]
    assert len(res["per_image_extractions"]) == 3


@patch("backend.app.api.extract.get_settings")
@patch("backend.app.api.verify.get_ocr_provider")
def test_sequential_inspections_isolated_panel_count(mock_get_provider, mock_settings):
    """Regression: Verifying 2 panels followed by 1 panel leaves no residual panels."""
    mock_settings.return_value.GEMINI_API_KEY = "test-key"

    ext = ExtractionResult(product_name=_make_field("Product"))

    mock_provider = AsyncMock()
    mock_provider.extract.return_value = ext
    mock_provider.model_name = "mock-gemini"
    mock_get_provider.return_value = mock_provider

    # Request 1: 2 panels
    files_2 = [
        ("images", ("f1.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
        ("images", ("f2.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    res1 = client.post("/api/verify", files=files_2, data={"panel_labels": ["P1", "P2"]}).json()
    assert res1["image_count"] == 2

    # Request 2: 1 panel
    files_1 = [
        ("images", ("single.jpg", io.BytesIO(DUMMY_JPEG), "image/jpeg")),
    ]
    res2 = client.post("/api/verify", files=files_1, data={"panel_labels": ["Single Panel"]}).json()
    assert res2["image_count"] == 1
    assert res2["panel_labels"] == ["Single Panel"]


