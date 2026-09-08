from abc import ABC, abstractmethod
from typing import Any, Dict


class ImageQualityChecker(ABC):
    """Abstract interface for package image capture quality evaluation.
    
    Evaluates blur, glare, lighting, resolution, and framing before
    progressing to the extraction stage.
    """

    @abstractmethod
    async def assess_quality(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image quality parameters and return an assessment score and pass/fail flags."""
        pass
