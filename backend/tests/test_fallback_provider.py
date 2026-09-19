"""Comprehensive test suite for the Resilient Fallback OCR Provider.

Tests all required fallback, cooldown, multi-panel, error classification,
and security properties.
"""

import asyncio
import io
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.config import Settings
from backend.app.main import app
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.services.interfaces.ocr import (
    AllProvidersExhaustedError,
    AuthenticationError,
    InvalidInputError,
    ModelNotFoundError,
    OCRProvider,
    ProviderQuotaExhaustedError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)
from backend.app.services.providers.fallback_provider import (
    ProviderCandidate,
    ResilientFallbackOCRProvider,
    reset_fallback_provider,
)


class MockProvider(OCRProvider):
    """Mock OCR provider for deterministic fallback testing."""

    def __init__(
        self,
        name: str,
        side_effects: list[Any] | None = None,
        return_result: ExtractionResult | None = None,
    ) -> None:
        self.name = name
        self.call_count = 0
        self.side_effects = list(side_effects or [])
        self.return_result = return_result or ExtractionResult(
            product_name=ExtractedField(value=f"Product from {name}", status="extracted", confidence=0.95),
            manufacturer_name=ExtractedField(value="Test Corp", status="extracted", confidence=0.9),
        )

    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        self.call_count += 1
        if self.side_effects:
            effect = self.side_effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            if isinstance(effect, type) and issubclass(effect, Exception):
                raise effect(f"Error from {self.name}")
            return effect
        return self.return_result


@pytest.fixture(autouse=True)
def clean_fallback_singleton():
    """Ensure clean fallback provider singleton state for each test."""
    reset_fallback_provider()
    yield
    reset_fallback_provider()


# =============================================================================
# 1. Primary Success: Gemini primary succeeds -> Groq is never called
# =============================================================================
@pytest.mark.asyncio
async def test_1_gemini_primary_succeeds_groq_never_called():
    gemini_mock = MockProvider("gemini-primary")
    groq_mock = MockProvider("groq-fallback")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 0
    assert result.product_name.value == "Product from gemini-primary"
    assert provider.model_name == "gemini-2.5-flash"
    assert provider.active_provider == "gemini"


# =============================================================================
# 2. Gemini 429 -> Gemini fallback model succeeds
# =============================================================================
@pytest.mark.asyncio
async def test_2_gemini_429_fallback_to_second_gemini_model():
    gemini_1 = MockProvider(
        "gemini-primary",
        side_effects=[ProviderQuotaExhaustedError("429 RESOURCE_EXHAUSTED", provider="gemini", model="gemini-2.5-flash")],
    )
    gemini_2 = MockProvider("gemini-secondary")
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_1),
        ProviderCandidate("gemini", "gemini-flash-latest", gemini_2),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_1.call_count == 1
    assert gemini_2.call_count == 1
    assert groq_mock.call_count == 0
    assert result.product_name.value == "Product from gemini-secondary"
    assert provider.model_name == "gemini-flash-latest"


# =============================================================================
# 3. Gemini 429 on all Gemini models -> Groq succeeds
# =============================================================================
@pytest.mark.asyncio
async def test_3_gemini_429_all_models_fallback_to_groq():
    gemini_1 = MockProvider(
        "gemini-1",
        side_effects=[ProviderQuotaExhaustedError("Quota exceeded", provider="gemini", model="gemini-2.5-flash")],
    )
    gemini_2 = MockProvider(
        "gemini-2",
        side_effects=[ProviderRateLimitError("Rate limited", provider="gemini", model="gemini-flash-latest")],
    )
    groq_mock = MockProvider("groq-model")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_1),
        ProviderCandidate("gemini", "gemini-flash-latest", gemini_2),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_1.call_count == 1
    assert gemini_2.call_count == 1
    assert groq_mock.call_count == 1
    assert result.product_name.value == "Product from groq-model"
    assert provider.model_name == "qwen/qwen3.8-27b"
    assert provider.active_provider == "groq"


# =============================================================================
# 4. Gemini 503 -> Groq fallback
# =============================================================================
@pytest.mark.asyncio
async def test_4_gemini_503_fallback_to_groq():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[ProviderUnavailableError("503 Service Unavailable", provider="gemini", model="gemini-2.5-flash")],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 1
    assert result.product_name.value == "Product from groq"


# =============================================================================
# 5. Gemini timeout -> Groq fallback
# =============================================================================
@pytest.mark.asyncio
async def test_5_gemini_timeout_fallback_to_groq():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[ProviderTimeoutError("Connection timed out", provider="gemini", model="gemini-2.5-flash")],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)
    result = await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 1
    assert result.product_name.value == "Product from groq"


# =============================================================================
# 6. Non-recoverable request/input error does not blindly fallback
# =============================================================================
@pytest.mark.asyncio
async def test_6_non_recoverable_error_does_not_fallback():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[InvalidInputError("Invalid image payload", provider="gemini")],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)

    with pytest.raises(InvalidInputError):
        await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 0  # Groq was NOT called


# =============================================================================
# 7. Missing Gemini key -> Groq can still operate
# =============================================================================
@pytest.mark.asyncio
async def test_7_missing_gemini_key_groq_operates():
    settings = Settings(
        GEMINI_API_KEY=None,
        GROQ_API_KEY="valid-groq-key",
    )
    provider = ResilientFallbackOCRProvider(settings=settings)

    assert len(provider.candidates) > 0
    assert all(c.provider_name == "groq" for c in provider.candidates)


# =============================================================================
# 8. Missing Groq key -> Gemini can still operate
# =============================================================================
@pytest.mark.asyncio
async def test_8_missing_groq_key_gemini_operates():
    settings = Settings(
        GEMINI_API_KEY="valid-gemini-key",
        GROQ_API_KEY=None,
    )
    provider = ResilientFallbackOCRProvider(settings=settings)

    assert len(provider.candidates) > 0
    assert all(c.provider_name == "gemini" for c in provider.candidates)


# =============================================================================
# 9. Both providers unavailable -> AllProvidersExhaustedError
# =============================================================================
@pytest.mark.asyncio
async def test_9_all_providers_fail_raises_all_exhausted():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[ProviderQuotaExhaustedError("Quota out", provider="gemini", model="gemini-2.5-flash")],
    )
    groq_mock = MockProvider(
        "groq",
        side_effects=[ProviderRateLimitError("TPM exceeded", provider="groq", model="qwen/qwen3.8-27b")],
    )

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)

    with pytest.raises(AllProvidersExhaustedError) as exc_info:
        await provider.extract(b"fake_image_bytes", "image/jpeg")

    assert "All configured AI providers/models were exhausted" in str(exc_info.value)
    assert len(exc_info.value.diagnostics) == 2


# =============================================================================
# 10. Cooldown prevents repeated calls to a failed candidate
# =============================================================================
@pytest.mark.asyncio
async def test_10_cooldown_skips_failed_candidate():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[
            ProviderQuotaExhaustedError("429 Resource exhausted", provider="gemini", model="gemini-2.5-flash"),
            ProviderQuotaExhaustedError("Should not be reached"),
        ],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates, cooldown_seconds=60)

    # 1st call: Gemini fails, falls back to Groq, marks Gemini cooldown
    res1 = await provider.extract(b"image_1", "image/jpeg")
    assert res1.product_name.value == "Product from groq"
    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 1

    # 2nd call: Gemini is in cooldown -> directly routes to Groq
    res2 = await provider.extract(b"image_2", "image/jpeg")
    assert res2.product_name.value == "Product from groq"
    assert gemini_mock.call_count == 1  # Not incremented!
    assert groq_mock.call_count == 2


# =============================================================================
# 11. Cooldown expires and candidate becomes eligible again
# =============================================================================
@pytest.mark.asyncio
async def test_11_cooldown_expires_candidate_eligible_again():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[
            ProviderQuotaExhaustedError("Temporary 429", provider="gemini", model="gemini-2.5-flash"),
            # 2nd time it succeeds:
            ExtractionResult(product_name=ExtractedField(value="Gemini Recovered", status="extracted")),
        ],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    # Use short cooldown: 0.1s
    provider = ResilientFallbackOCRProvider(candidates=candidates, cooldown_seconds=0.1)

    # Call 1 -> Gemini fails, Groq succeeds, Gemini cooled down
    await provider.extract(b"image_1", "image/jpeg")
    assert gemini_mock.call_count == 1

    # Wait for cooldown to expire
    await asyncio.sleep(0.15)

    # Call 2 -> Gemini cooldown expired -> Gemini attempted and succeeds
    res2 = await provider.extract(b"image_2", "image/jpeg")
    assert gemini_mock.call_count == 2
    assert res2.product_name.value == "Gemini Recovered"


# =============================================================================
# 12. Multi-panel request: Gemini fails panel 1 -> Groq handles panel 1 ->
#     Panel 2 skips cooled-down Gemini
# =============================================================================
@pytest.mark.asyncio
async def test_12_multipanel_skips_cooled_down_gemini():
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[
            ProviderQuotaExhaustedError("Panel 1 429", provider="gemini", model="gemini-2.5-flash"),
        ],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates, cooldown_seconds=60)

    # Simulate multi-panel: Panel 1 extraction
    panel_1_result = await provider.extract(b"panel_1_data", "image/jpeg")
    assert gemini_mock.call_count == 1
    assert groq_mock.call_count == 1
    assert panel_1_result.product_name.value == "Product from groq"

    # Panel 2 extraction: Gemini is now cooled down, goes straight to Groq
    panel_2_result = await provider.extract(b"panel_2_data", "image/jpeg")
    assert gemini_mock.call_count == 1  # Gemini was skipped
    assert groq_mock.call_count == 2
    assert panel_2_result.product_name.value == "Product from groq"


# =============================================================================
# 13. API Response reports the actual model/provider used
# =============================================================================
def test_13_api_response_reports_actual_model_used():
    client = TestClient(app)

    fake_image = io.BytesIO(b"\xff\xd8\xff\xe0" + b"\x00" * 100)
    fake_image.name = "test.jpg"

    # Mock get_ocr_provider to return ResilientFallbackOCRProvider with Groq active
    gemini_mock = MockProvider(
        "gemini",
        side_effects=[ProviderQuotaExhaustedError("429 Quota exhausted")],
    )
    groq_mock = MockProvider("groq")

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]
    resilient_provider = ResilientFallbackOCRProvider(candidates=candidates)

    with patch("backend.app.api.extract.get_ocr_provider", return_value=resilient_provider):
        response = client.post(
            "/api/extract",
            files={"image": ("test.jpg", fake_image, "image/jpeg")},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Reports the model that actually performed the extraction!
        assert data["model_used"] == "qwen/qwen3.8-27b"


# =============================================================================
# 14. API keys never appear in logs or errors
# =============================================================================
@pytest.mark.asyncio
async def test_14_api_keys_never_appear_in_errors():
    secret_key = "AIzaSySecretGeminiKey123456789012"
    groq_key = "gsk_SecretGroqKey1234567890123456789012345"

    gemini_mock = MockProvider(
        "gemini",
        side_effects=[
            ProviderQuotaExhaustedError(f"Failure with key={secret_key} and raw {secret_key}"),
        ],
    )
    groq_mock = MockProvider(
        "groq",
        side_effects=[
            ProviderRateLimitError(f"Rate limited on authorization Bearer {groq_key}"),
        ],
    )

    candidates = [
        ProviderCandidate("gemini", "gemini-2.5-flash", gemini_mock),
        ProviderCandidate("groq", "qwen/qwen3.8-27b", groq_mock),
    ]

    provider = ResilientFallbackOCRProvider(candidates=candidates)

    with pytest.raises(AllProvidersExhaustedError) as exc_info:
        await provider.extract(b"image_bytes", "image/jpeg")

    error_message = str(exc_info.value)
    # Ensure neither key appears in the error message
    assert secret_key not in error_message
    assert groq_key not in error_message


# =============================================================================
# 15. Default Model Priority Order
# =============================================================================
def test_15_default_model_priority_order():
    settings = Settings(
        GEMINI_API_KEY="test-gemini-key",
        GROQ_API_KEY="test-groq-key",
        GEMINI_MODEL="gemini-3.6-flash",
        GEMINI_MODELS="gemini-3.6-flash,gemini-3.8-flash,gemini-3.7-flash,gemini-3.5-flash",
        GROQ_MODEL="qwen/qwen3.8-27b",
        GROQ_MODELS="qwen/qwen3.8-27b",
    )
    assert settings.get_gemini_models() == [
        "gemini-3.6-flash",
        "gemini-3.8-flash",
        "gemini-3.7-flash",
        "gemini-3.5-flash",
    ]
    assert settings.get_groq_models() == [
        "qwen/qwen3.8-27b",
    ]

    provider = ResilientFallbackOCRProvider(settings=settings)
    expected_chain = [
        ("gemini", "gemini-3.6-flash"),
        ("gemini", "gemini-3.8-flash"),
        ("gemini", "gemini-3.7-flash"),
        ("gemini", "gemini-3.5-flash"),
        ("groq", "qwen/qwen3.8-27b"),
    ]
    actual_chain = [(c.provider_name, c.model_name) for c in provider.candidates]
    assert actual_chain == expected_chain
