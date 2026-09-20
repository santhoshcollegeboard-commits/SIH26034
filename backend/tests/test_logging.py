"""Comprehensive test suite for PackCheck persistent rotating logging system.

Verifies:
1. Log file creation and directory auto-creation
2. OCR attempt logging with safe credentials (key=GEMINI_API_KEY / key=GROQ_API_KEY)
3. HTTP 429 quota exhaustion and automatic model fallback logging
4. Successful provider/model selection logging with duration_ms
5. Candidate cooldown logging with reason and duration
6. Redaction of API keys (AIza..., gsk_...) to prevent credential leakage
7. Redaction of Authorization headers, Bearer tokens, passwords, and base64 payloads
8. RotatingFileHandler configuration (maxBytes, backupCount) and rollover functionality
9. Multi-panel request correlation via request_id and panel context
10. Open Food Facts API v3 request logging (OFF_REQUEST)
11. Barcode reading & validation outcome logging (BARCODE_EVENT)
12. Fail-safe design: logging failures never crash the application
"""

import logging
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock, patch

import pytest

from backend.app.core.config import Settings, get_settings
from backend.app.core.logging import (
    LOGGER_NAME,
    PackCheckLogFormatter,
    RedactingFilter,
    format_kv,
    get_default_log_path,
    log_all_providers_exhausted,
    log_backend_exception,
    log_barcode_event,
    log_cooldown,
    log_event,
    log_extract_complete,
    log_extract_start,
    log_fallback,
    log_ocr_attempt,
    log_ocr_failure,
    log_ocr_success,
    log_off_request,
    log_shutdown,
    log_startup,
    log_verify_complete,
    log_verify_start,
    panel_idx_ctx,
    request_id_ctx,
    sanitize_log_message,
    setup_logging,
)
from backend.app.schemas.extraction import ExtractedField, ExtractionResult
from backend.app.services.interfaces.ocr import (
    AllProvidersExhaustedError,
    OCRProvider,
    ProviderQuotaExhaustedError,
    ProviderRateLimitError,
)
from backend.app.services.providers.fallback_provider import (
    ProviderCandidate,
    ResilientFallbackOCRProvider,
)


class MockLoggingProvider(OCRProvider):
    """Mock OCR provider for deterministic logging verification."""

    def __init__(
        self,
        name: str,
        side_effects: list[object] | None = None,
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
        return self.return_result


@pytest.fixture
def isolated_log_path(tmp_path: Path) -> Generator[Path, None, None]:
    """Provide an isolated log file path and reconfigure logging for test isolation."""
    test_log_file = tmp_path / "logs" / "test_packcheck.log"
    setup_logging(log_file_path=test_log_file, force_reconfigure=True)

    yield test_log_file

    # Teardown: re-attach default logging to avoid affecting other tests
    setup_logging(log_file_path=get_default_log_path(), force_reconfigure=True)


def read_log_file(path: Path) -> str:
    """Flush all handlers and read log contents cleanly."""
    for handler in logging.getLogger().handlers:
        handler.flush()
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""


# =============================================================================
# 1. Log file is created
# =============================================================================
def test_1_log_file_created(tmp_path: Path) -> None:
    nested_log_path = tmp_path / "deep" / "nested" / "packcheck.log"
    assert not nested_log_path.exists()
    assert not nested_log_path.parent.exists()

    handler = setup_logging(log_file_path=nested_log_path, force_reconfigure=True)
    assert handler is not None
    assert nested_log_path.exists()

    log_event("TEST_EVENT", test_key="test_value")
    contents = read_log_file(nested_log_path)
    assert "TEST_EVENT" in contents
    assert "test_key=test_value" in contents

    # Clean up back to default
    setup_logging(log_file_path=get_default_log_path(), force_reconfigure=True)


def test_1_default_log_path_resolution() -> None:
    path = get_default_log_path()
    assert path.name == "packcheck.log"
    assert path.parent.name == "logs"


# =============================================================================
# 2. OCR attempt is logged
# =============================================================================
@pytest.mark.asyncio
async def test_2_ocr_attempt_logged(isolated_log_path: Path) -> None:
    # Direct helper test
    log_ocr_attempt(
        provider="gemini",
        model="gemini-3.8-flash",
        key_name="GEMINI_API_KEY",
        panel=1,
        request_id="req_test_attempt",
    )

    contents = read_log_file(isolated_log_path)
    assert "OCR_ATTEMPT" in contents
    assert "provider=gemini" in contents
    assert "model=gemini-3.8-flash" in contents
    assert "key=GEMINI_API_KEY" in contents
    assert "request_id=req_test_attempt" in contents
    assert "panel=1" in contents

    # Integration test with ResilientFallbackOCRProvider
    mock_prov = MockLoggingProvider("gemini-test")
    candidates = [
        ProviderCandidate("gemini", "gemini-3.8-flash", mock_prov),
    ]
    provider = ResilientFallbackOCRProvider(candidates=candidates)
    await provider.extract(b"test_image_bytes", "image/jpeg")

    updated_contents = read_log_file(isolated_log_path)
    assert "OCR_ATTEMPT | provider=gemini model=gemini-3.8-flash key=GEMINI_API_KEY" in updated_contents


# =============================================================================
# 3. 429 and fallback are logged
# =============================================================================
@pytest.mark.asyncio
async def test_3_429_and_fallback_logged(isolated_log_path: Path) -> None:
    gemini_1 = MockLoggingProvider(
        "gemini-1",
        side_effects=[
            ProviderQuotaExhaustedError("Resource exhausted: 429 Quota Exceeded", provider="gemini", model="gemini-3.8-flash")
        ],
    )
    gemini_2 = MockLoggingProvider("gemini-2")

    candidates = [
        ProviderCandidate("gemini", "gemini-3.8-flash", gemini_1),
        ProviderCandidate("gemini", "gemini-3.7-flash", gemini_2),
    ]
    provider = ResilientFallbackOCRProvider(candidates=candidates)

    result = await provider.extract(b"fake_image", "image/jpeg")
    assert result.product_name.value == "Product from gemini-2"

    contents = read_log_file(isolated_log_path)

    # Verify 429 OCR_FAILURE logged
    assert "OCR_FAILURE" in contents
    assert "status_code=429" in contents
    assert "error_type=ProviderQuotaExhaustedError" in contents

    # Verify FALLBACK event logged
    assert "FALLBACK" in contents
    assert 'from=gemini-3.8-flash' in contents
    assert 'to=gemini-3.7-flash' in contents

    # Verify subsequent OCR_SUCCESS logged
    assert "OCR_SUCCESS" in contents
    assert "model=gemini-3.7-flash" in contents


# =============================================================================
# 4. Successful provider/model is logged
# =============================================================================
def test_4_ocr_success_logged(isolated_log_path: Path) -> None:
    log_ocr_success(
        provider="gemini",
        model="gemini-3.8-flash",
        duration_ms=480,
        request_id="req_success_456",
        panel=2,
    )

    contents = read_log_file(isolated_log_path)
    assert "OCR_SUCCESS" in contents
    assert "provider=gemini" in contents
    assert "model=gemini-3.8-flash" in contents
    assert "duration_ms=480" in contents
    assert "request_id=req_success_456" in contents
    assert "panel=2" in contents


# =============================================================================
# 5. Cooldown is logged
# =============================================================================
def test_5_cooldown_logged(isolated_log_path: Path) -> None:
    mock_prov = MockLoggingProvider("gemini-cooling")
    candidates = [ProviderCandidate("gemini", "gemini-3.8-flash", mock_prov)]
    provider = ResilientFallbackOCRProvider(candidates=candidates)

    provider.mark_cooldown("gemini:gemini-3.8-flash", reason="quota_exhausted")

    contents = read_log_file(isolated_log_path)
    assert "COOLDOWN" in contents
    assert "candidate=gemini:gemini-3.8-flash" in contents
    assert "reason=quota_exhausted" in contents
    assert "duration=" in contents
    assert "s" in contents


# =============================================================================
# 6. API keys are never written in full
# =============================================================================
def test_6_api_keys_never_written_in_full(isolated_log_path: Path) -> None:
    real_lookalike_gemini_key = "AIzaSyDa9876543210ZYXWVUTSRQPONMLKJIHG"
    real_lookalike_groq_key = "gsk_test1234567890abcdef123456789012"

    # Sanitize test directly
    sanitized_gemini = sanitize_log_message(f"Failed calling with key {real_lookalike_gemini_key}")
    assert real_lookalike_gemini_key not in sanitized_gemini
    assert "***REDACTED***" in sanitized_gemini

    sanitized_groq = sanitize_log_message(f"Error from provider key={real_lookalike_groq_key}")
    assert real_lookalike_groq_key not in sanitized_groq
    assert "***REDACTED***" in sanitized_groq

    # File log test through log_event and log_ocr_failure
    log_ocr_failure(
        provider="gemini",
        model="gemini-3.8-flash",
        error_type="APIError",
        status_code=403,
        error_msg=f"Invalid key {real_lookalike_gemini_key} or Groq {real_lookalike_groq_key}",
    )

    contents = read_log_file(isolated_log_path)
    assert real_lookalike_gemini_key not in contents
    assert real_lookalike_groq_key not in contents
    assert "***REDACTED***" in contents


# =============================================================================
# 7. Authorization headers/tokens and base64 never written
# =============================================================================
def test_7_authorization_headers_and_base64_never_written(isolated_log_path: Path) -> None:
    bearer_token = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.secretpayload.signature123"
    auth_header = 'authorization: "Bearer supersecret12345"'
    password_param = 'password="MySuperSecretPass!123"'
    base64_image = "data:image/jpeg;base64," + ("A" * 60)
    raw_base64_blob = "B" * 120

    test_message = (
        f"Request failed with {bearer_token}, header: {auth_header}, {password_param}, "
        f"payload: {base64_image} and blob: {raw_base64_blob}"
    )

    log_event("SECURITY_TEST", details=test_message)

    contents = read_log_file(isolated_log_path)

    # Sensitive values must be completely absent
    assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in contents
    assert "supersecret12345" not in contents
    assert "MySuperSecretPass!123" not in contents
    assert ("A" * 50) not in contents
    assert raw_base64_blob not in contents

    # Redaction placeholders must appear
    assert "Bearer ***REDACTED***" in contents
    assert "[IMAGE_BASE64_DATA_REDACTED]" in contents
    assert "[BASE64_DATA_REDACTED]" in contents


# =============================================================================
# 8. Log rotation configuration exists
# =============================================================================
def test_8_log_rotation_configuration(tmp_path: Path) -> None:
    settings = get_settings()
    assert settings.LOG_MAX_BYTES == 5 * 1024 * 1024
    assert settings.LOG_BACKUP_COUNT == 3

    # Test active rollover functionality with small max_bytes
    small_log = tmp_path / "rot_logs" / "rotate_test.log"
    handler = setup_logging(
        log_file_path=small_log,
        max_bytes=400,
        backup_count=2,
        force_reconfigure=True,
    )
    assert handler is not None
    assert handler.maxBytes == 400
    assert handler.backupCount == 2

    # Emit records to cross 400-byte boundary multiple times
    for i in range(25):
        log_event("ROTATION_STEP", index=i, padding="x" * 60)

    for h in logging.getLogger().handlers:
        h.flush()

    rotated_file_1 = tmp_path / "rot_logs" / "rotate_test.log.1"
    assert small_log.exists()
    assert rotated_file_1.exists()

    # Reset back to default
    setup_logging(log_file_path=get_default_log_path(), force_reconfigure=True)


# =============================================================================
# 9. Multi-panel request includes request_id and panel
# =============================================================================
def test_9_multi_panel_includes_request_id_and_panel(isolated_log_path: Path) -> None:
    req_token = request_id_ctx.set("req_multi_panel_abc123")
    panel_token = panel_idx_ctx.set(3)

    try:
        log_ocr_attempt(
            provider="gemini",
            model="gemini-3.8-flash",
            key_name="GEMINI_API_KEY",
        )
        log_ocr_success(
            provider="gemini",
            model="gemini-3.8-flash",
            duration_ms=250,
        )

        contents = read_log_file(isolated_log_path)
        assert "request_id=req_multi_panel_abc123" in contents
        assert "panel=3" in contents
    finally:
        request_id_ctx.reset(req_token)
        panel_idx_ctx.reset(panel_token)

    # After reset, new events should not have request_id or panel by default
    log_event("AFTER_RESET")
    after_contents = read_log_file(isolated_log_path)
    last_line = after_contents.strip().splitlines()[-1]
    assert "AFTER_RESET" in last_line
    assert "request_id=" not in last_line
    assert "panel=" not in last_line


# =============================================================================
# 10. Open Food Facts request logged
# =============================================================================
def test_10_open_food_facts_request_logged(isolated_log_path: Path) -> None:
    log_off_request(
        gtin="8901030999999",
        result="FOUND",
        response_time_ms=175,
        request_id="req_off_lookup",
    )

    contents = read_log_file(isolated_log_path)
    assert "OFF_REQUEST" in contents
    assert "provider=OpenFoodFacts" in contents
    assert "gtin=8901030999999" in contents
    assert "result=FOUND" in contents
    assert "response_time_ms=175" in contents
    assert "request_id=req_off_lookup" in contents


# =============================================================================
# 11. Barcode event logged
# =============================================================================
def test_11_barcode_event_logged(isolated_log_path: Path) -> None:
    log_barcode_event(
        event_type="NO_GTIN_DETECTED",
        message="No barcode found on package image",
        request_id="req_barcode_1",
    )
    log_barcode_event(
        event_type="INVALID_GTIN",
        gtin="8901030000000",
        message="Invalid GTIN check digit",
        request_id="req_barcode_2",
    )

    contents = read_log_file(isolated_log_path)
    assert "BARCODE_EVENT" in contents
    assert "status=NO_GTIN_DETECTED" in contents
    assert 'message="No barcode found on package image"' in contents
    assert "status=INVALID_GTIN" in contents
    assert "gtin=8901030000000" in contents


# =============================================================================
# 12. Logging failure does not crash the application
# =============================================================================
def test_12_logging_failure_does_not_crash_application() -> None:
    # Intentionally trigger an internal exception in the logging helper
    with patch("logging.getLogger", side_effect=RuntimeError("Logging subsystem simulated crash")):
        # These must not raise exceptions
        log_event("CRASH_TEST")
        log_ocr_attempt("gemini", "gemini-3.8-flash", "GEMINI_API_KEY")
        log_ocr_success("gemini", "gemini-3.8-flash", 100)
        log_ocr_failure("gemini", "gemini-3.8-flash", "SimulatedError")
        log_fallback("model-a", "model-b")
        log_cooldown("cand-1", "reason", "120s")
        log_all_providers_exhausted(["cand:err"])
        log_off_request("123", "FOUND", 100)
        log_barcode_event("EVENT", "123")
        log_backend_exception(ValueError("Simulated exception"))
        log_startup("PackCheck", "0.1.0", "test")
        log_shutdown("PackCheck")
        log_verify_start("req_1", 1)
        log_verify_complete("req_1", True, 100, "COMPLIANT")
        log_extract_start("req_1", 1)
        log_extract_complete("req_1", True, 100, "gemini-3.8-flash")
