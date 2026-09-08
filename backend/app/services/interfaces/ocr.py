from abc import ABC, abstractmethod
from typing import Any, Dict

from backend.app.schemas.extraction import ExtractionResult


class OCRProvider(ABC):
    """Abstract base provider for optical character recognition & visual feature extraction.

    Architecture principle:
    AI/OCR only extracts and proposes. The rest of the application interacts
    with this interface, keeping the pipeline independent of specific AI providers.
    """

    @abstractmethod
    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        """Extract structured fields from a packaged commodity image.

        Args:
            image_data: Raw image bytes (JPEG, PNG, or WEBP).
            mime_type: MIME type of the image (e.g. 'image/jpeg').

        Returns:
            ExtractionResult with per-field values, confidence scores, and source regions.
        """
        pass


class CloudOCRProvider(OCRProvider):
    """Phase 1: Cloud-based vision and OCR provider (e.g., Gemini Vision, Groq Vision).

    Concrete implementations should subclass this and implement extract().
    """

    def __init__(self, api_key: str | None = None, model_name: str | None = None) -> None:
        self.api_key = api_key
        self.model_name = model_name


class LocalOCRProvider(OCRProvider):
    """Phase 2: Local on-device OCR/vision provider (NVIDIA RTX 4050 6GB inference).

    Stub interface - not implemented yet.
    """

    def __init__(self, model_path: str | None = None, device: str = "cuda") -> None:
        self.model_path = model_path
        self.device = device

    async def extract(self, image_data: bytes, mime_type: str) -> ExtractionResult:
        raise NotImplementedError("LocalOCRProvider will be implemented in Phase 2.")
