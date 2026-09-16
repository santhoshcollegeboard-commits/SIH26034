"""Tests for the GeminiOCRProvider.

All tests mock the google-genai client — no real API calls or keys required.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.providers.gemini_provider import GeminiOCRProvider


def _make_mock_response(text: str) -> MagicMock:
    """Create a mock Gemini API response with the given text."""
    mock_response = MagicMock()
    mock_response.text = text
    return mock_response


VALID_GEMINI_OUTPUT = json.dumps(
    {
        "product_name": {
            "value": "Parle-G Biscuits",
            "confidence": 0.96,
            "source_region": [30, 50, 75, 300],
            "status": "extracted",
        },
        "manufacturer_name": {
            "value": "Parle Products Pvt. Ltd.",
            "confidence": 0.94,
            "source_region": [180, 40, 210, 340],
            "status": "extracted",
        },
        "manufacturer_address": {
            "value": "Vile Parle (E), Mumbai - 400057",
            "confidence": 0.89,
            "source_region": [215, 40, 250, 360],
            "status": "extracted",
        },
        "packer_name": {
            "value": None,
            "confidence": None,
            "source_region": None,
            "status": "not_found",
        },
        "importer_name": {
            "value": None,
            "confidence": None,
            "source_region": None,
            "status": "not_found",
        },
        "net_quantity": {
            "value": "800 g",
            "confidence": 0.95,
            "source_region": [600, 50, 640, 150],
            "status": "extracted",
        },
        "mrp": {
            "value": "MRP ₹150.00",
            "confidence": 0.97,
            "source_region": [640, 50, 680, 220],
            "status": "extracted",
        },
        "month_year_of_manufacture": {
            "value": "10/2026",
            "confidence": 0.92,
            "source_region": [680, 50, 720, 150],
            "status": "extracted",
        },
        "consumer_care_details": {
            "value": None,
            "confidence": None,
            "source_region": [800, 40, 850, 300],
            "status": "unreadable",
        },
        "common_or_generic_name": {
            "value": "Biscuits",
            "confidence": 0.9,
            "source_region": [75, 50, 100, 200],
            "status": "extracted",
        },
        "country_of_origin": {
            "value": "India",
            "confidence": 0.88,
            "source_region": [720, 50, 750, 150],
            "status": "extracted",
        }
    }
)


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_valid_response(mock_client_cls):
    """Provider correctly parses a well-formed Gemini response."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_mock_response(VALID_GEMINI_OUTPUT)
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")
    result = await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")

    assert result.product_name.value == "Parle-G Biscuits"
    assert result.product_name.status == "extracted"
    assert result.product_name.confidence == pytest.approx(0.96)
    assert result.product_name.source_region is not None
    assert result.product_name.source_region.x == pytest.approx(0.05)

    assert result.net_quantity.value == "800 g"
    assert result.mrp.value == "MRP ₹150.00"

    assert result.packer_name.status == "not_found"
    assert result.packer_name.value is None

    assert result.consumer_care_details.status == "unreadable"
    assert result.consumer_care_details.value is None


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_malformed_json_raises(mock_client_cls):
    """Provider raises ValueError when Gemini returns invalid JSON."""
    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_mock_response(
        "This is not valid JSON at all {{{broken"
    )
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")

    with pytest.raises(ValueError, match="malformed JSON"):
        await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_empty_response_raises(mock_client_cls):
    """Provider raises ValueError when Gemini returns empty text."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = ""
    mock_client.models.generate_content.return_value = mock_response
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")

    with pytest.raises(ValueError, match="empty response"):
        await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_api_failure_raises_runtime(mock_client_cls):
    """Provider raises RuntimeError when the Gemini API call itself fails."""
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = Exception("Network timeout")
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")

    with pytest.raises(RuntimeError, match="Gemini API call failed"):
        await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_handles_plain_string_fields(mock_client_cls):
    """Provider gracefully handles Gemini returning plain strings instead of objects."""
    # Sometimes Gemini may return a field as a plain string instead of the full object
    plain_response = json.dumps(
        {
            "product_name": "Simple String Product",
            "manufacturer_name": {"value": "Proper Object", "confidence": 0.9, "status": "extracted"},
            "net_quantity": "",
        }
    )

    mock_client = MagicMock()
    mock_client.models.generate_content.return_value = _make_mock_response(plain_response)
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")
    result = await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")

    # Plain string should be parsed as extracted value
    assert result.product_name.value == "Simple String Product"
    assert result.product_name.status == "extracted"

    # Proper object should parse normally
    assert result.manufacturer_name.value == "Proper Object"

    # Empty string should map to not_found
    assert result.net_quantity.value is None
    assert result.net_quantity.status == "not_found"


@pytest.mark.asyncio
@patch("backend.app.services.providers.gemini_provider.genai.Client")
async def test_extract_native_async_client(mock_client_cls):
    """Provider utilizes native async client when aio.models.generate_content is an async callable."""
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        return_value=_make_mock_response(VALID_GEMINI_OUTPUT)
    )
    mock_client_cls.return_value = mock_client

    provider = GeminiOCRProvider(api_key="test-key-not-real")
    result = await provider.extract(b"\xff\xd8\xff\xe0" + b"\x00" * 50, "image/jpeg")

    assert result.product_name.value == "Parle-G Biscuits"
    assert result.product_name.status == "extracted"
    mock_client.aio.models.generate_content.assert_awaited_once()

