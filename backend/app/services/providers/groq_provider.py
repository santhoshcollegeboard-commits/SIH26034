"""Groq Vision OCR Provider — Phase 1 Cloud Implementation.

Uses the official Groq Python SDK to call Groq's multimodal vision model (e.g. qwen/qwen3.8-27b).
Isolated behind the OCRProvider abstraction so the rest of PackCheck
never calls Groq directly.

Architecture boundary:
- This provider ONLY extracts and proposes field values.
- It does NOT make compliance decisions (no PASS/FAIL).
- Missing/unreadable values are reported honestly, never hallucinated.
"""

import asyncio
import base64
import json
import logging
import re
from typing import Any, Dict

import groq

from backend.app.schemas.extraction import (
    ExtractionResult,
    ExtractedField,
    SourceRegion,
)
from backend.app.services.interfaces.ocr import (
    AuthenticationError,
    CloudOCRProvider,
    ModelNotFoundError,
    ProviderRateLimitError,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RecoverableOCRError,
)
from backend.app.services.providers.gemini_provider import EXTRACTION_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen/qwen3.8-27b"


class GroqOCRProvider(CloudOCRProvider):
    """Concrete Groq Vision implementation of CloudOCRProvider.

    Uses groq.AsyncGroq SDK to send package images to Groq and receive
    structured extraction results.
    """

    def __init__(self, api_key: str, model_name: str | None = None) -> None:
        super().__init__(api_key=api_key, model_name=model_name or DEFAULT_MODEL)
        self._client = groq.AsyncGroq(api_key=api_key)

    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        """Send image to Groq Vision and parse structured extraction result.

        Args:
            image_data: Raw image bytes.
            mime_type: MIME type (image/jpeg, image/png, image/webp).

        Returns:
            ExtractionResult with per-field extraction data.

        Raises:
            ValueError: If Groq returns malformed or unparseable JSON.
            RuntimeError: If the Groq API call fails.
        """
        try:
            base64_image = base64.b64encode(image_data).decode("utf-8")
            data_url = f"data:{mime_type};base64,{base64_image}"

            response = await self._client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": EXTRACTION_SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Extract all mandatory Legal Metrology declaration fields from this packaged commodity image.",
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": data_url,
                                },
                            },
                        ],
                    },
                ],
                response_format={"type": "json_object"},
                temperature=0.1,
            )
        except Exception as e:
            raw_msg = str(e)
            clean_msg = re.sub(r"gsk_[0-9A-Za-z_-]{30,}", "***REDACTED***", raw_msg)
            clean_msg = re.sub(r"key=[^&\s]+", "key=***REDACTED***", clean_msg)
            logger.error("Groq API call failed (%s): %s", self.model_name, clean_msg)

            code = getattr(e, "status_code", None) or getattr(e, "code", None)
            err_lower = raw_msg.lower()

            if isinstance(e, groq.RateLimitError) or code == 429 or "rate limit" in err_lower or "429" in err_lower:
                raise ProviderRateLimitError(
                    f"Groq API call failed ({self.model_name}) - rate limit exceeded: {clean_msg}",
                    provider="groq",
                    model=self.model_name,
                ) from e

            if isinstance(e, groq.NotFoundError) or code == 404 or "not found" in err_lower or "model_not_found" in err_lower:
                raise ModelNotFoundError(
                    f"Groq API call failed ({self.model_name}) - model not found or unsupported: {clean_msg}",
                    provider="groq",
                    model=self.model_name,
                ) from e

            if (
                isinstance(e, (groq.InternalServerError, groq.APIConnectionError))
                or code in (500, 502, 503, 504)
                or "unavailable" in err_lower
                or "service unavailable" in err_lower
                or "bad gateway" in err_lower
            ):
                raise ProviderUnavailableError(
                    f"Groq API call failed ({self.model_name}) - service unavailable: {clean_msg}",
                    provider="groq",
                    model=self.model_name,
                ) from e

            if isinstance(e, groq.APITimeoutError) or isinstance(e, (asyncio.TimeoutError, TimeoutError)) or "timeout" in err_lower:
                raise ProviderTimeoutError(
                    f"Groq API call failed ({self.model_name}) - request timed out: {clean_msg}",
                    provider="groq",
                    model=self.model_name,
                ) from e

            if (
                isinstance(e, (groq.AuthenticationError, groq.PermissionDeniedError))
                or code in (401, 403)
                or "authentication" in err_lower
                or "unauthorized" in err_lower
                or "invalid api key" in err_lower
            ):
                raise AuthenticationError(
                    f"Groq API call failed ({self.model_name}) - authentication failed: {clean_msg}",
                    provider="groq",
                    model=self.model_name,
                ) from e

            raise RecoverableOCRError(
                f"Groq API call failed ({self.model_name}): {clean_msg}",
                provider="groq",
                model=self.model_name,
            ) from e

        # Extract content from response
        if not response.choices:
            raise ValueError("Groq returned an empty response choices list.")

        raw_text = response.choices[0].message.content
        if not raw_text:
            raise ValueError("Groq returned an empty response content.")

        try:
            raw_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("Groq returned invalid JSON: %s", raw_text[:500])
            raise ValueError(f"Groq returned malformed JSON: {e}") from e

        # Convert raw JSON into validated ExtractionResult
        return self._parse_extraction(raw_data)

    def _parse_extraction(self, raw_data: Dict[str, Any]) -> ExtractionResult:
        """Parse Groq's raw JSON into a validated ExtractionResult.

        Handles minor variations in output format gracefully.
        """
        field_names = [
            "product_name",
            "common_or_generic_name",
            "manufacturer_name",
            "manufacturer_address",
            "packer_name",
            "importer_name",
            "country_of_origin",
            "net_quantity",
            "mrp",
            "month_year_of_manufacture",
            "consumer_care_details",
        ]

        fields: Dict[str, ExtractedField] = {}

        for name in field_names:
            raw_field = raw_data.get(name)

            if raw_field is None:
                fields[name] = ExtractedField(
                    value=None, confidence=None, source_region=None, status="not_found"
                )
                continue

            if isinstance(raw_field, str):
                fields[name] = ExtractedField(
                    value=raw_field if raw_field else None,
                    confidence=None,
                    source_region=None,
                    status="extracted" if raw_field else "not_found",
                )
                continue

            if not isinstance(raw_field, dict):
                fields[name] = ExtractedField(
                    value=None, confidence=None, source_region=None, status="not_found"
                )
                continue

            # Parse the structured field object
            value = raw_field.get("value")
            confidence = raw_field.get("confidence")
            status = raw_field.get("status")
            source_region_data = raw_field.get("source_region")

            source_region = None
            if source_region_data and isinstance(source_region_data, list) and len(source_region_data) == 4:
                try:
                    ymin, xmin, ymax, xmax = [float(v) for v in source_region_data]
                    if 0 <= ymin <= ymax <= 1000 and 0 <= xmin <= xmax <= 1000:
                        source_region = SourceRegion(
                            x=xmin / 1000.0,
                            y=ymin / 1000.0,
                            width=(xmax - xmin) / 1000.0,
                            height=(ymax - ymin) / 1000.0,
                        )
                except (ValueError, TypeError):
                    source_region = None
            elif source_region_data and isinstance(source_region_data, dict):
                try:
                    # Support dictionary bounding box format if model provides {x, y, width, height}
                    # or {ymin, xmin, ymax, xmax}
                    if "ymin" in source_region_data and "ymax" in source_region_data:
                        ymin = float(source_region_data["ymin"])
                        xmin = float(source_region_data.get("xmin", 0))
                        ymax = float(source_region_data["ymax"])
                        xmax = float(source_region_data.get("xmax", 0))
                        if 0 <= ymin <= ymax <= 1000 and 0 <= xmin <= xmax <= 1000:
                            source_region = SourceRegion(
                                x=xmin / 1000.0,
                                y=ymin / 1000.0,
                                width=(xmax - xmin) / 1000.0,
                                height=(ymax - ymin) / 1000.0,
                            )
                    elif "x" in source_region_data and "y" in source_region_data:
                        x = float(source_region_data["x"])
                        y = float(source_region_data["y"])
                        w = float(source_region_data.get("width", 0))
                        h = float(source_region_data.get("height", 0))
                        # Normalize if given as 0-1000
                        if x > 1 or y > 1 or w > 1 or h > 1:
                            x, y, w, h = x / 1000.0, y / 1000.0, w / 1000.0, h / 1000.0
                        source_region = SourceRegion(x=x, y=y, width=w, height=h)
                except (ValueError, TypeError):
                    source_region = None

            # Validate confidence is in range
            if confidence is not None:
                try:
                    confidence = float(confidence)
                    confidence = max(0.0, min(1.0, confidence))
                except (ValueError, TypeError):
                    confidence = None

            # Normalize status
            if not status or status not in ("extracted", "unreadable", "not_found"):
                status = "extracted" if value else "not_found"

            fields[name] = ExtractedField(
                value=value,
                confidence=confidence,
                source_region=source_region,
                status=status,
            )

        return ExtractionResult(**fields)
