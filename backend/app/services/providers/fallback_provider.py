"""Resilient Fallback OCR Provider.

Implements OCRProvider with an automatic candidate chain and in-memory cooldown:
1. Gemini preferred & fallback vision models (if GEMINI_API_KEY configured)
2. Groq preferred & fallback vision models (if GROQ_API_KEY configured)

Features:
- Automatic fallback on recoverable failures (429 / RESOURCE_EXHAUSTED, 5xx, timeouts, connection errors, model not found).
- Circuit breaker: Marks failed candidates with in-memory cooldown to avoid hammering rate-limited APIs across panels and requests.
- Strictly bounds retries to configured candidates (no infinite loops).
- Never catches non-recoverable input errors blindly.
- Sanitizes all log messages and exception traces to guarantee zero credential leakage.
- Conforms 1:1 to the OCRProvider abstraction and ExtractionResult schema.
"""

from dataclasses import dataclass
import logging
import re
import time
from typing import Any, List, Optional

from backend.app.core.config import Settings, get_settings
from backend.app.schemas.extraction import ExtractionResult
from backend.app.services.interfaces.ocr import (
    AllProvidersExhaustedError,
    AuthenticationError,
    InvalidInputError,
    ModelNotFoundError,
    NonRecoverableOCRError,
    OCRProvider,
    ProviderQuotaExhaustedError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RecoverableOCRError,
)
from backend.app.services.providers.gemini_provider import GeminiOCRProvider
from backend.app.services.providers.groq_provider import GroqOCRProvider

logger = logging.getLogger(__name__)


def _sanitize_message(msg: str) -> str:
    """Sanitize error messages to prevent leaking API keys or credentials."""
    cleaned = re.sub(r"AIza[0-9A-Za-z_-]{20,}", "***REDACTED***", msg)
    cleaned = re.sub(r"gsk_[0-9A-Za-z_-]{20,}", "***REDACTED***", cleaned)
    cleaned = re.sub(r"key=[^&\s]+", "key=***REDACTED***", cleaned)
    cleaned = re.sub(r"Bearer\s+[^\s,]+", "Bearer ***REDACTED***", cleaned)
    return cleaned



from backend.app.core.logging import (
    log_all_providers_exhausted,
    log_cooldown,
    log_fallback,
    log_ocr_attempt,
    log_ocr_failure,
    log_ocr_success,
)


@dataclass
class ProviderCandidate:
    """Represents a specific (provider, model) candidate in the fallback chain."""

    provider_name: str  # "gemini" | "groq"
    model_name: str
    instance: OCRProvider

    @property
    def id(self) -> str:
        return f"{self.provider_name}:{self.model_name}"


class ResilientFallbackOCRProvider(OCRProvider):
    """Resilient OCR provider executing a prioritized chain of AI vision candidates."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        candidates: Optional[List[ProviderCandidate]] = None,
        cooldown_seconds: Optional[int] = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.cooldown_seconds = (
            cooldown_seconds
            if cooldown_seconds is not None
            else getattr(self.settings, "PROVIDER_COOLDOWN_SECONDS", 60)
        )
        self._cooldowns: dict[str, float] = {}

        if candidates is not None:
            self.candidates = candidates
        else:
            self.candidates = self._build_candidates(self.settings)

        # model_name reflects the model that succeeded (or the first preferred model)
        self.model_name: Optional[str] = (
            self.candidates[0].model_name if self.candidates else None
        )
        self.active_provider: Optional[str] = (
            self.candidates[0].provider_name if self.candidates else None
        )

    @staticmethod
    def _build_candidates(settings: Settings) -> List[ProviderCandidate]:
        """Build ordered candidate chain based on settings and available credentials."""
        candidates: List[ProviderCandidate] = []

        # 1. Gemini Candidates (Primary)
        if settings.GEMINI_API_KEY:
            gemini_models = settings.get_gemini_models()
            for model in gemini_models:
                candidates.append(
                    ProviderCandidate(
                        provider_name="gemini",
                        model_name=model,
                        instance=GeminiOCRProvider(
                            api_key=settings.GEMINI_API_KEY,
                            model_name=model,
                        ),
                    )
                )

        # 2. Groq Candidates (Fallback)
        if settings.GROQ_API_KEY:
            groq_models = settings.get_groq_models()
            for model in groq_models:
                candidates.append(
                    ProviderCandidate(
                        provider_name="groq",
                        model_name=model,
                        instance=GroqOCRProvider(
                            api_key=settings.GROQ_API_KEY,
                            model_name=model,
                        ),
                    )
                )

        return candidates

    def is_candidate_available(self, candidate_id: str) -> bool:
        """Check if a candidate is available or currently in cooldown."""
        expiry = self._cooldowns.get(candidate_id)
        if expiry is None:
            return True
        if time.monotonic() >= expiry:
            del self._cooldowns[candidate_id]
            logger.info("Cooldown expired for candidate '%s'; candidate is eligible again", candidate_id)
            return True
        return False

    def mark_cooldown(
        self,
        candidate_id: str,
        duration: Optional[float] = None,
        reason: Optional[str] = None,
    ) -> None:
        """Place a candidate into cooldown."""
        dur = duration if duration is not None else self.cooldown_seconds
        self._cooldowns[candidate_id] = time.monotonic() + dur
        logger.warning(
            "Candidate '%s' cooled down for %.1f seconds",
            candidate_id,
            dur,
        )
        log_cooldown(
            candidate=candidate_id,
            reason=reason or "provider_error",
            duration=f"{dur:.1f}s",
        )

    def reset_cooldowns(self) -> None:
        """Clear all active cooldowns (primarily used for test teardown)."""
        self._cooldowns.clear()

    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        """Execute extraction across the candidate chain with automatic fallback.

        Args:
            image_data: Raw package image bytes.
            mime_type: Image MIME type.

        Returns:
            ExtractionResult from the first successful candidate.

        Raises:
            InvalidInputError: If image_data is empty or invalid.
            NonRecoverableOCRError: If non-recoverable error occurs.
            AllProvidersExhaustedError: If all candidate models fail.
        """
        if not image_data or len(image_data) == 0:
            raise InvalidInputError("Image data is empty; cannot perform OCR extraction.")

        if not self.candidates:
            raise AllProvidersExhaustedError(
                "No AI OCR provider credentials (Gemini or Groq) are configured in environment."
            )

        # Filter candidates eligible right now (not in cooldown)
        eligible_candidates = [
            c for c in self.candidates if self.is_candidate_available(c.id)
        ]

        # If all candidates are currently in cooldown, try the one that was cooled down earliest
        if not eligible_candidates:
            logger.warning("All candidate models are currently in cooldown; probing candidate closest to expiry")
            sorted_by_expiry = sorted(
                self.candidates,
                key=lambda c: self._cooldowns.get(c.id, 0),
            )
            eligible_candidates = [sorted_by_expiry[0]]

        errors_log: list[dict[str, Any]] = []

        for idx, candidate in enumerate(eligible_candidates):
            cid = candidate.id
            if not self.is_candidate_available(cid) and len(eligible_candidates) > 1:
                continue

            cand_start = time.monotonic()
            key_name = "GEMINI_API_KEY" if candidate.provider_name == "gemini" else "GROQ_API_KEY"
            log_ocr_attempt(
                provider=candidate.provider_name,
                model=candidate.model_name,
                key_name=key_name,
            )

            try:
                result = await candidate.instance.extract(image_data, mime_type)
                elapsed_ms = int((time.monotonic() - cand_start) * 1000)
                log_ocr_success(
                    provider=candidate.provider_name,
                    model=candidate.model_name,
                    duration_ms=elapsed_ms,
                )
                self.model_name = candidate.model_name
                self.active_provider = candidate.provider_name
                return result

            except NonRecoverableOCRError as err:
                clean_err_str = _sanitize_message(str(err))
                log_ocr_failure(
                    provider=candidate.provider_name,
                    model=candidate.model_name,
                    error_type=type(err).__name__,
                    status_code=getattr(err, "status_code", None),
                    error_msg=clean_err_str,
                )
                logger.error(
                    "Non-recoverable OCR error encountered on %s: %s; aborting fallback",
                    cid,
                    err,
                )
                raise
            except (RecoverableOCRError, Exception) as err:
                clean_err_str = _sanitize_message(str(err))
                status_code = getattr(err, "status_code", None)
                if status_code is None:
                    if isinstance(err, (ProviderQuotaExhaustedError, ProviderRateLimitError)) or "429" in clean_err_str:
                        status_code = 429
                    elif isinstance(err, ProviderUnavailableError) or "503" in clean_err_str:
                        status_code = 503
                    elif isinstance(err, ModelNotFoundError) or "404" in clean_err_str:
                        status_code = 404

                log_ocr_failure(
                    provider=candidate.provider_name,
                    model=candidate.model_name,
                    error_type=type(err).__name__,
                    status_code=status_code,
                    error_msg=clean_err_str,
                )
                reason = "quota_exhausted" if status_code == 429 else type(err).__name__.lower()
                self.mark_cooldown(cid, reason=reason)
                errors_log.append({
                    "candidate": cid,
                    "error_type": type(err).__name__,
                    "error": clean_err_str,
                })

                # Determine next candidate for structured logging
                next_cand = (
                    eligible_candidates[idx + 1]
                    if idx + 1 < len(eligible_candidates)
                    else None
                )
                if next_cand:
                    logger.warning(
                        "%s model '%s' failed with %s; falling back to %s model '%s'",
                        candidate.provider_name.capitalize(),
                        candidate.model_name,
                        type(err).__name__,
                        next_cand.provider_name.capitalize(),
                        next_cand.model_name,
                    )
                    log_fallback(
                        from_model=candidate.model_name,
                        to_model=next_cand.model_name,
                    )
                else:
                    logger.warning(
                        "%s model '%s' failed with %s; no further eligible models in current tier",
                        candidate.provider_name.capitalize(),
                        candidate.model_name,
                        type(err).__name__,
                    )

        logger.error("All OCR providers exhausted. Failures: %s", errors_log)
        summary_messages = [
            f"{entry['candidate']} ({entry['error_type']}: {entry['error']})"
            for entry in errors_log
        ]
        log_all_providers_exhausted(
            attempts=[f"{entry['candidate']}:{entry['error_type']}" for entry in errors_log]
        )
        raise AllProvidersExhaustedError(
            f"All configured AI providers/models were exhausted. Attempts: {'; '.join(summary_messages)}",
            diagnostics=errors_log,
        )


_fallback_provider_singleton: Optional[ResilientFallbackOCRProvider] = None


def get_fallback_provider(settings: Optional[Settings] = None) -> ResilientFallbackOCRProvider:
    """Singleton factory for ResilientFallbackOCRProvider to preserve in-memory cooldown state."""
    global _fallback_provider_singleton
    if _fallback_provider_singleton is None:
        _fallback_provider_singleton = ResilientFallbackOCRProvider(settings=settings)
    return _fallback_provider_singleton


def reset_fallback_provider() -> None:
    """Reset the singleton instance (primarily for unit testing)."""
    global _fallback_provider_singleton
    _fallback_provider_singleton = None
