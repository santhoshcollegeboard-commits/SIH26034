"""Gemini Vision OCR Provider — Phase 1 Cloud Implementation.

Uses the official google-genai SDK to call Gemini's vision model.
Isolated behind the OCRProvider abstraction so the rest of PackCheck
never calls Gemini directly.

Architecture boundary:
- This provider ONLY extracts and proposes field values.
- It does NOT make compliance decisions (no PASS/FAIL).
- Missing/unreadable values are reported honestly, never hallucinated.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Dict

from google import genai
from google.genai import types

from backend.app.schemas.extraction import (
    ExtractionResult,
    ExtractedField,
    SourceRegion,
)
from backend.app.services.interfaces.ocr import CloudOCRProvider

logger = logging.getLogger(__name__)

# The system prompt that constrains Gemini to extraction-only behavior.
EXTRACTION_SYSTEM_PROMPT = """You are a precise label-reading assistant for Legal Metrology compliance inspection of packaged commodities in India.

Your job is ONLY to extract text from the packaging image. You do NOT judge compliance.

For the given package image, extract these 11 fields:
1. product_name — Commercial brand or trade name under which the product is marketed (e.g. "Oreo", "Tata Salt", "Lay's")
2. common_or_generic_name — Common, generic, or descriptive name of the commodity itself (e.g. "Chocolate Sandwich Biscuits", "Iodised Salt", "Potato Chips"). If only a brand name is visible and NO separate generic commodity name is printed, set value to null and status to "not_found". Do NOT duplicate the brand name here.
3. manufacturer_name — Name of the manufacturer
4. manufacturer_address — Complete address of the manufacturer (premise, street, city, state, pin code)
5. packer_name — Name of the packer (if different from manufacturer)
6. importer_name — Name of the importer (if applicable, for imported goods)
7. country_of_origin — Country of origin or manufacture (e.g. "India", "Japan", "Vietnam")
8. net_quantity — Net quantity/weight/volume declaration (e.g. "500 g", "1 L")
9. mrp — Maximum Retail Price including all tax-inclusive wording (e.g. "₹120.00 (Inclusive of all taxes)", "MRP ₹85.00 incl. of all taxes"). Capture the full price declaration including any 'inclusive of all taxes' or 'incl. of all taxes' disclaimer printed on, under, or adjacent to the price numeral.
10. month_year_of_manufacture — Month and year of manufacture or packaging
11. consumer_care_details — Consumer care/helpline information (phone, email, address)

For EACH field, return a JSON object with:
- "value": the extracted text exactly as printed, or null if not found/unreadable
- "confidence": a float 0.0 to 1.0 indicating extraction confidence, or null if not found
- "source_region": {"x": int, "y": int, "width": int, "height": int} approximate bounding box in pixels, or null if not found
- "status": one of "extracted", "unreadable", or "not_found"

CRITICAL RULES:
- If a field is not visible or not present on the package, set value to null and status to "not_found". Do NOT guess.
- If a field is partially visible or blurred, set value to null and status to "unreadable". Do NOT hallucinate.
- Never fabricate values that are not clearly visible on the packaging.
- Report ONLY what you can read. This is evidence collection, not speculation.
- Do NOT make any compliance judgment. Do NOT say if the package passes or fails any rule.

Return ONLY the JSON object with the 11 fields as keys. No extra commentary."""

DEFAULT_MODEL = "gemini-flash-latest"


class GeminiOCRProvider(CloudOCRProvider):
    """Concrete Gemini Vision implementation of CloudOCRProvider.

    Uses google-genai SDK to send package images to Gemini and receive
    structured extraction results.
    """

    def __init__(self, api_key: str, model_name: str | None = None) -> None:
        super().__init__(api_key=api_key, model_name=model_name or DEFAULT_MODEL)
        self._client = genai.Client(api_key=api_key)

    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        """Send image to Gemini Vision and parse structured extraction result.

        Args:
            image_data: Raw image bytes.
            mime_type: MIME type (image/jpeg, image/png, image/webp).

        Returns:
            ExtractionResult with per-field extraction data.

        Raises:
            ValueError: If Gemini returns malformed or unparseable JSON.
            RuntimeError: If the Gemini API call fails.
        """
        try:
            aio_models = getattr(getattr(self._client, "aio", None), "models", None)
            async_generate = getattr(aio_models, "generate_content", None) if aio_models else None

            if async_generate and inspect.iscoroutinefunction(async_generate):
                # Native asynchronous Google GenAI client call
                response = await self._client.aio.models.generate_content(
                    model=self.model_name,
                    contents=[
                        types.Part.from_bytes(data=image_data, mime_type=mime_type),
                        "Extract all mandatory Legal Metrology declaration fields from this packaged commodity image.",
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=EXTRACTION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
            else:
                # Offload synchronous call to worker thread to prevent blocking event loop
                response = await asyncio.to_thread(
                    self._client.models.generate_content,
                    model=self.model_name,
                    contents=[
                        types.Part.from_bytes(data=image_data, mime_type=mime_type),
                        "Extract all mandatory Legal Metrology declaration fields from this packaged commodity image.",
                    ],
                    config=types.GenerateContentConfig(
                        system_instruction=EXTRACTION_SYSTEM_PROMPT,
                        response_mime_type="application/json",
                        temperature=0.1,
                    ),
                )
        except Exception as e:
            logger.error("Gemini API call failed: %s", e)
            raise RuntimeError(f"Gemini API call failed: {e}") from e

        # Parse the response text as JSON
        raw_text = response.text
        if not raw_text:
            raise ValueError("Gemini returned an empty response.")

        try:
            raw_data = json.loads(raw_text)
        except json.JSONDecodeError as e:
            logger.error("Gemini returned invalid JSON: %s", raw_text[:500])
            raise ValueError(f"Gemini returned malformed JSON: {e}") from e

        # Convert raw JSON into validated ExtractionResult
        return self._parse_extraction(raw_data)

    def _parse_extraction(self, raw_data: Dict[str, Any]) -> ExtractionResult:
        """Parse Gemini's raw JSON into a validated ExtractionResult.

        Handles minor variations in Gemini's output format gracefully.
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
                # Gemini sometimes returns a plain string instead of an object
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
            status = raw_field.get("status", "not_found")
            source_region_data = raw_field.get("source_region")

            source_region = None
            if source_region_data and isinstance(source_region_data, dict):
                try:
                    source_region = SourceRegion(
                        x=int(source_region_data.get("x", 0)),
                        y=int(source_region_data.get("y", 0)),
                        width=int(source_region_data.get("width", 0)),
                        height=int(source_region_data.get("height", 0)),
                    )
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
            if status not in ("extracted", "unreadable", "not_found"):
                status = "extracted" if value else "not_found"

            fields[name] = ExtractedField(
                value=value,
                confidence=confidence,
                source_region=source_region,
                status=status,
            )

        return ExtractionResult(**fields)
