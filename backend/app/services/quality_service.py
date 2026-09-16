"""Deterministic Image Quality Checker implementation.

Evaluates package captures against statutory and operational readiness criteria:
1. Resolution: Adequate pixel density for fine Legal Metrology numerals (Rule 6).
2. Sharpness / Blur: Focus check via discrete Laplacian variance.
3. Lighting / Exposure: Luminance check to detect dark captures or severe glare.
4. Framing / Aspect Ratio: Rejection of collapsed or corrupted dimensions.

The quality gate protects the pipeline by rejecting poor images BEFORE calling
any AI/OCR service (zero cloud/compute cost for unreadable captures).
"""

import io
import logging
from typing import Any, Dict, List

import numpy as np
from PIL import Image, UnidentifiedImageError

from backend.app.services.interfaces.quality import ImageQualityChecker

logger = logging.getLogger(__name__)


class StandardImageQualityChecker(ImageQualityChecker):
    """Concrete deterministic implementation of ImageQualityChecker.
    
    Uses in-memory PIL and NumPy calculations for sub-20ms evaluation.
    """

    # Operational thresholds for Legal Metrology packaging inspection
    MIN_WIDTH: int = 300
    MIN_HEIGHT: int = 300
    MIN_TOTAL_PIXELS: int = 90_000  # 300 x 300

    MIN_SHARPNESS: float = 50.0      # Laplacian variance threshold
    MIN_BRIGHTNESS: float = 25.0     # Mean grayscale luminance lower bound (underexposed)
    MAX_BRIGHTNESS: float = 245.0    # Mean grayscale luminance upper bound (overexposed / glare)

    MIN_ASPECT_RATIO: float = 0.1    # Prevent collapsed 1-pixel slivers
    MAX_ASPECT_RATIO: float = 10.0

    async def assess_quality(self, image_data: bytes) -> Dict[str, Any]:
        """Analyze image quality parameters and return an assessment score and pass/fail flags.

        Args:
            image_data: Raw bytes of uploaded package image.

        Returns:
            Dict conforming to QualityAssessment schema.
        """
        reasons: List[str] = []
        details: Dict[str, Any] = {}

        # 1. Attempt image decoding
        try:
            image = Image.open(io.BytesIO(image_data))
            image.load()
        except (UnidentifiedImageError, OSError, Exception) as e:
            logger.warning("Quality gate could not decode image: %s", e)
            return {
                "is_acceptable": False,
                "overall_score": 0.0,
                "reasons": ["Uploaded file is corrupted or not a valid decodable image."],
                "details": {
                    "decodable": False,
                    "error": str(e),
                },
            }

        width, height = image.size
        total_pixels = width * height
        aspect_ratio = float(width) / float(height) if height > 0 else 0.0

        # 2. Resolution check
        res_passed = (
            width >= self.MIN_WIDTH
            and height >= self.MIN_HEIGHT
            and total_pixels >= self.MIN_TOTAL_PIXELS
        )
        if not res_passed:
            reasons.append(
                f"Insufficient image resolution: {width}x{height} pixels "
                f"({total_pixels:,} total pixels). Minimum required: "
                f"{self.MIN_WIDTH}x{self.MIN_HEIGHT} ({self.MIN_TOTAL_PIXELS:,} pixels)."
            )

        details["resolution"] = {
            "width": width,
            "height": height,
            "total_pixels": total_pixels,
            "min_width": self.MIN_WIDTH,
            "min_height": self.MIN_HEIGHT,
            "passed": res_passed,
        }

        # 3. Framing / Aspect ratio check
        framing_passed = self.MIN_ASPECT_RATIO <= aspect_ratio <= self.MAX_ASPECT_RATIO
        if not framing_passed:
            reasons.append(
                f"Extreme aspect ratio ({aspect_ratio:.2f}). Package framing is distorted or cropped."
            )

        details["framing"] = {
            "aspect_ratio": round(aspect_ratio, 3),
            "min_ratio": self.MIN_ASPECT_RATIO,
            "max_ratio": self.MAX_ASPECT_RATIO,
            "passed": framing_passed,
        }

        # 4. Exposure & Sharpness checks (via grayscale array)
        try:
            gray_img = image.convert("L")
            arr = np.array(gray_img, dtype=np.float32)

            # Brightness (mean luminance 0-255)
            mean_brightness = float(np.mean(arr))
            brightness_passed = self.MIN_BRIGHTNESS <= mean_brightness <= self.MAX_BRIGHTNESS

            if mean_brightness < self.MIN_BRIGHTNESS:
                reasons.append(
                    f"Image is severely underexposed / too dark "
                    f"(mean luminance: {mean_brightness:.1f}, minimum: {self.MIN_BRIGHTNESS})."
                )
            elif mean_brightness > self.MAX_BRIGHTNESS:
                reasons.append(
                    f"Image is severely overexposed / washed out with glare "
                    f"(mean luminance: {mean_brightness:.1f}, maximum: {self.MAX_BRIGHTNESS})."
                )

            details["brightness"] = {
                "mean_luminance": round(mean_brightness, 1),
                "min_threshold": self.MIN_BRIGHTNESS,
                "max_threshold": self.MAX_BRIGHTNESS,
                "passed": brightness_passed,
            }

            # Sharpness / Blur via discrete Laplacian variance
            # Convolve interior pixels with discrete Laplacian kernel [[0, 1, 0], [1, -4, 1], [0, 1, 0]]
            if arr.shape[0] >= 3 and arr.shape[1] >= 3:
                laplacian = (
                    arr[:-2, 1:-1]
                    + arr[2:, 1:-1]
                    + arr[1:-1, :-2]
                    + arr[1:-1, 2:]
                    - 4.0 * arr[1:-1, 1:-1]
                )
                sharpness_score = float(np.var(laplacian))
            else:
                sharpness_score = 0.0

            sharpness_passed = sharpness_score >= self.MIN_SHARPNESS
            if not sharpness_passed:
                reasons.append(
                    f"Image is excessively blurred (sharpness score: {sharpness_score:.1f}, "
                    f"minimum required: {self.MIN_SHARPNESS}). Text declarations may be unreadable."
                )

            details["sharpness"] = {
                "score": round(sharpness_score, 1),
                "threshold": self.MIN_SHARPNESS,
                "passed": sharpness_passed,
            }

        except Exception as e:
            logger.error("Error computing image array metrics: %s", e)
            brightness_passed = False
            sharpness_passed = False
            reasons.append(f"Internal error evaluating image exposure/sharpness: {e}")
            details["metric_error"] = str(e)

        # 5. Composite decision and score calculation
        is_acceptable = (
            res_passed and framing_passed and brightness_passed and sharpness_passed
        )

        # Calculate normalized composite score (0.0 to 1.0)
        res_norm = min(1.0, total_pixels / (800.0 * 800.0))
        sharp_norm = min(1.0, sharpness_score / 500.0) if "sharpness_score" in locals() else 0.0
        bright_dist = abs(mean_brightness - 128.0) if "mean_brightness" in locals() else 128.0
        bright_norm = max(0.0, 1.0 - (bright_dist / 128.0))

        raw_score = (res_norm * 0.3) + (sharp_norm * 0.4) + (bright_norm * 0.3)

        if is_acceptable:
            # Scale acceptable scores into 0.60 - 1.0 range
            overall_score = round(float(0.60 + 0.40 * raw_score), 2)
        else:
            # Scale unacceptable scores into 0.0 - 0.45 range
            overall_score = round(float(min(0.45, raw_score * 0.5)), 2)

        return {
            "is_acceptable": is_acceptable,
            "overall_score": overall_score,
            "reasons": reasons,
            "details": details,
        }
