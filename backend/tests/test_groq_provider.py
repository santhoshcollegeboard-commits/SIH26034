"""Tests for the GroqOCRProvider.

All tests mock the groq.AsyncGroq client — no real API calls or keys required.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.app.services.providers.groq_provider import GroqOCRProvider


def _make_mock_response(text: str) -> MagicMock:
    """Create a mock Groq API response with the given content text."""
    mock_choice = MagicMock()
    mock_choice.message.content = text
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]
    return mock_response


VALID_GROQ_OUTPUT = json.dumps(
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
        },
    }
)


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_valid_response(mock_client_cls):
    """Provider correctly parses a well-formed Groq response."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_response(VALID_GROQ_OUTPUT)
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert result.product_name.value == "Parle-G Biscuits"
    assert result.product_name.confidence == 0.96
    assert result.product_name.status == "extracted"
    assert result.product_name.source_region is not None
    assert result.product_name.source_region.x == 0.05
    assert result.product_name.source_region.y == 0.03

    assert result.net_quantity.value == "800 g"
    assert result.mrp.value == "MRP ₹150.00"
    assert result.month_year_of_manufacture.value == "10/2026"
    assert result.packer_name.status == "not_found"
    assert result.packer_name.value is None
    assert result.consumer_care_details.status == "unreadable"


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_partial_response(mock_client_cls):
    """Missing fields in Groq output default to not_found with None values."""
    mock_client = MagicMock()
    partial_output = json.dumps({"product_name": {"value": "Solo Product", "confidence": 0.9}})
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_response(partial_output)
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    result = await provider.extract(b"fake_image_bytes", "image/png")

    assert result.product_name.value == "Solo Product"
    assert result.product_name.status == "extracted"
    assert result.manufacturer_name.status == "not_found"
    assert result.manufacturer_name.value is None
    assert result.net_quantity.status == "not_found"
    assert result.mrp.status == "not_found"


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_string_format_fallback(mock_client_cls):
    """Fields returned as plain strings instead of dict objects are handled."""
    mock_client = MagicMock()
    string_output = json.dumps({"product_name": "Simple String Product", "mrp": ""})
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_response(string_output)
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert result.product_name.value == "Simple String Product"
    assert result.product_name.status == "extracted"
    assert result.mrp.status == "not_found"
    assert result.mrp.value is None


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_malformed_json_raises_value_error(mock_client_cls):
    """Invalid JSON from Groq raises ValueError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_response("Not JSON at all {broken")
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    with pytest.raises(ValueError, match="malformed JSON"):
        await provider.extract(b"fake_image_bytes", "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_api_error_raises_runtime_error(mock_client_cls):
    """Network/API failure raises RuntimeError."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        side_effect=Exception("Connection refused")
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    with pytest.raises(RuntimeError, match="Groq API call failed"):
        await provider.extract(b"fake_image_bytes", "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_extract_empty_response_raises_value_error(mock_client_cls):
    """Empty response choices raises ValueError."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = []
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    with pytest.raises(ValueError, match="empty response choices"):
        await provider.extract(b"fake_image_bytes", "image/jpeg")


@pytest.mark.asyncio
@patch("backend.app.services.providers.groq_provider.groq.AsyncGroq")
async def test_groq_timeout_is_applied(mock_client_cls):
    """Explicit 15-second timeout is applied to AsyncGroq client and chat completion call."""
    mock_client = MagicMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_make_mock_response(VALID_GROQ_OUTPUT)
    )
    mock_client_cls.return_value = mock_client

    provider = GroqOCRProvider(api_key="fake-groq-key")
    assert provider.timeout == 15.0
    mock_client_cls.assert_called_once_with(api_key="fake-groq-key", timeout=15.0)

    await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert mock_client.chat.completions.create.called
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs.get("timeout") == 15.0
