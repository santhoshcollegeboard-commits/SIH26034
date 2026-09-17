"""High-level barcode service for PackCheck.

Coordinates decoding across single and multi-panel image uploads,
aggregates detected barcode candidates, evaluates GTIN validity,
and produces a structured, backward-compatible BarcodeSummary.
"""

import logging
from typing import List, Optional, Tuple

from backend.app.schemas.barcode import (
    BarcodeDetectionStatus,
    BarcodeItem,
    BarcodeSummary,
)
from backend.app.services.barcode.decoder import BarcodeDecoder

logger = logging.getLogger(__name__)


class BarcodeService:
    """Service orchestrating barcode detection and GTIN validation."""

    def __init__(self, decoder: Optional[BarcodeDecoder] = None) -> None:
        self.decoder = decoder or BarcodeDecoder()

    def process_package(
        self,
        images: List[Tuple[bytes, str, str]],
    ) -> BarcodeSummary:
        """Process one or more packaging panel images for barcodes.

        Args:
            images: List of tuples (image_bytes, content_type, panel_label).

        Returns:
            Structured BarcodeSummary.
        """
        if not images:
            return BarcodeSummary(
                status=BarcodeDetectionStatus.NO_BARCODE_DETECTED,
                detected=False,
                count=0,
                barcodes=[],
                primary_gtin=None,
                is_valid_gtin=None,
                message="No images provided for barcode inspection.",
            )

        all_barcodes: List[BarcodeItem] = []
        decoder_errors: List[str] = []

        for idx, (img_bytes, _mime, label) in enumerate(images):
            try:
                panel_results = self.decoder.decode_bytes(
                    image_bytes=img_bytes,
                    panel_index=idx,
                    panel_label=label,
                )
                all_barcodes.extend(panel_results)
            except Exception as exc:
                logger.warning("Barcode decoding error on panel %s: %s", label, exc)
                decoder_errors.append(f"{label}: {exc}")

        # If all panels had decoder errors and no barcodes detected
        if decoder_errors and not all_barcodes:
            return BarcodeSummary(
                status=BarcodeDetectionStatus.DECODER_ERROR,
                detected=False,
                count=0,
                barcodes=[],
                primary_gtin=None,
                is_valid_gtin=None,
                message=f"Barcode decoding failed on submitted panels: {'; '.join(decoder_errors)}",
            )

        # Case 1: No barcode detected
        if not all_barcodes:
            return BarcodeSummary(
                status=BarcodeDetectionStatus.NO_BARCODE_DETECTED,
                detected=False,
                count=0,
                barcodes=[],
                primary_gtin=None,
                is_valid_gtin=None,
                message="No readable barcode detected on the submitted packaging image(s).",
            )

        # Case 2: Exactly one barcode detected
        if len(all_barcodes) == 1:
            single = all_barcodes[0]
            return BarcodeSummary(
                status=BarcodeDetectionStatus.BARCODE_DETECTED,
                detected=True,
                count=1,
                barcodes=all_barcodes,
                primary_gtin=single.gtin,
                is_valid_gtin=single.is_valid_gtin if single.gtin else None,
                message=f"Single barcode detected ({single.format.value}): {single.validation_message}",
            )

        # Case 3: Multiple barcodes detected
        # Preserve all detected barcodes; do not guess primary GTIN without justification
        formats_summary = ", ".join(
            f"{b.format.value} ('{b.raw_value}')" for b in all_barcodes
        )
        return BarcodeSummary(
            status=BarcodeDetectionStatus.MULTIPLE_BARCODES_DETECTED,
            detected=True,
            count=len(all_barcodes),
            barcodes=all_barcodes,
            primary_gtin=None,
            is_valid_gtin=None,
            message=f"{len(all_barcodes)} barcodes detected across package panels: {formats_summary}.",
        )


# Global singleton instance
_barcode_service: Optional[BarcodeService] = None


def get_barcode_service() -> BarcodeService:
    """Dependency provider returning the singleton BarcodeService."""
    global _barcode_service
    if _barcode_service is None:
        _barcode_service = BarcodeService()
    return _barcode_service
