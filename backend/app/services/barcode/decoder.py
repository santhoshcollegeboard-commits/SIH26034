"""Low-level barcode decoder using zxing-cpp.

Decodes 1D and 2D barcode symbols from PIL images or raw image bytes.
Integrates directly with local GTIN validation.

Employs controlled multi-pass preprocessing to robustly detect retail barcodes
(EAN/UPC) from real-world packaging photographs where perspective, lighting,
or blur may hinder raw single-pass detection.
"""

import io
import logging
from typing import List, Optional, Set, Tuple

from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import zxingcpp

from backend.app.schemas.barcode import BarcodeFormat, BarcodeItem
from backend.app.services.barcode.validator import validate_gtin

logger = logging.getLogger(__name__)

# Map zxingcpp BarcodeFormat names to PackCheck BarcodeFormat enum
_FORMAT_MAP = {
    "EAN13": BarcodeFormat.EAN_13,
    "EAN8": BarcodeFormat.EAN_8,
    "UPCA": BarcodeFormat.UPC_A,
    "UPCE": BarcodeFormat.UPC_E,
    "Code128": BarcodeFormat.CODE_128,
    "ITF14": BarcodeFormat.ITF_14,
    "ITF": BarcodeFormat.ITF,
    "QRCode": BarcodeFormat.QR_CODE,
    "DataMatrix": BarcodeFormat.DATA_MATRIX,
}

_RETAIL_1D_FORMATS = {
    BarcodeFormat.EAN_13,
    BarcodeFormat.EAN_8,
    BarcodeFormat.UPC_A,
    BarcodeFormat.UPC_E,
    BarcodeFormat.ITF_14,
    BarcodeFormat.ITF,
    BarcodeFormat.CODE_128,
}


def map_zxing_format(zxing_fmt: zxingcpp.BarcodeFormat) -> BarcodeFormat:
    """Map a zxingcpp BarcodeFormat to PackCheck BarcodeFormat enum."""
    name = getattr(zxing_fmt, "name", str(zxing_fmt))
    return _FORMAT_MAP.get(name, BarcodeFormat.UNKNOWN)


def _has_valid_retail_gtin(items: List[BarcodeItem]) -> bool:
    """Check if any decoded item is a valid 1D retail GTIN."""
    return any(item.format in _RETAIL_1D_FORMATS and item.is_valid_gtin for item in items)


class BarcodeDecoder:
    """Decodes barcodes from image buffers and evaluates local GTIN validity."""

    @classmethod
    def _parse_detected_barcodes(
        cls,
        detected_barcodes: list,
        panel_index: Optional[int] = None,
        panel_label: Optional[str] = None,
    ) -> List[BarcodeItem]:
        """Convert zxingcpp Barcode objects into validated BarcodeItem schemas."""
        results: List[BarcodeItem] = []
        for bc in detected_barcodes:
            raw_text = bc.text or ""
            mapped_format = map_zxing_format(bc.format)

            val_res = validate_gtin(raw_text, mapped_format)
            pos_str = str(bc.position) if getattr(bc, "position", None) else None

            results.append(
                BarcodeItem(
                    raw_value=raw_text,
                    format=mapped_format,
                    gtin=val_res.normalized_gtin,
                    is_valid_gtin=val_res.is_valid,
                    validation_status=val_res.status,
                    validation_message=val_res.message,
                    position=pos_str,
                    panel_index=panel_index,
                    panel_label=panel_label,
                )
            )
        return results

    @classmethod
    def _merge_barcodes(
        cls,
        primary_items: List[BarcodeItem],
        new_items: List[BarcodeItem],
    ) -> List[BarcodeItem]:
        """Merge barcode items preserving order while deduplicating by (format, raw_value)."""
        seen: Set[Tuple[BarcodeFormat, str]] = {
            (item.format, item.raw_value.strip()) for item in primary_items
        }
        merged = list(primary_items)
        for item in new_items:
            key = (item.format, item.raw_value.strip())
            if key not in seen:
                seen.add(key)
                merged.append(item)
        return merged

    @classmethod
    def decode_pil_image(
        cls,
        pil_image: Image.Image,
        panel_index: Optional[int] = None,
        panel_label: Optional[str] = None,
    ) -> List[BarcodeItem]:
        """Decode all barcodes present in a PIL Image.

        Execution stages:
        1. Raw attempt: Run zxingcpp directly on the input image without modification.
           If a valid retail GTIN is found, return immediately for optimal performance.
        2. Multi-pass preprocessing: If raw attempt finds nothing or finds only non-GTIN
           symbologies (e.g. QR codes), progressively apply controlled enhancements:
           - Grayscale normalization
           - Autocontrast / histogram stretching
           - Contrast boost (enhance 1.8x)
           - Sharpening
           - Combined contrast + sharpening
           - Reasonable upscaling (for smaller images where barcode lines are subpixel)
           - GlobalHistogram binarizer variants
        3. Deduplication: Merge all unique detected barcodes without fabricating any values.

        Args:
            pil_image: PIL Image object.
            panel_index: Optional panel index where the image belongs.
            panel_label: Optional human-readable label for the panel.

        Returns:
            List of unique detected BarcodeItem records.
        """
        # --- Pass 0: Raw attempt ---
        try:
            raw_detected = zxingcpp.read_barcodes(pil_image)
            results = cls._parse_detected_barcodes(raw_detected, panel_index, panel_label)
        except Exception as exc:
            logger.error("zxingcpp.read_barcodes failed on raw image: %s", exc)
            results = []

        # If raw attempt already found a valid retail GTIN barcode, return immediately
        if _has_valid_retail_gtin(results):
            return results

        # --- Multi-pass Preprocessing ---
        try:
            gray = pil_image.convert("L") if pil_image.mode != "L" else pil_image
        except Exception:
            gray = pil_image

        variants: List[Tuple[str, Image.Image, Optional[object]]] = []

        # 1. Grayscale direct (if original was color)
        if pil_image.mode != "L":
            variants.append(("grayscale", gray, None))

        # 2. Autocontrast (adaptive dynamic range expansion)
        try:
            auto = ImageOps.autocontrast(gray, cutoff=1)
            variants.append(("autocontrast", auto, None))
        except Exception:
            auto = gray

        # 3. Contrast enhancement (helps with faded printing or overexposed lighting)
        try:
            contrast_boost = ImageEnhance.Contrast(gray).enhance(1.8)
            variants.append(("contrast_1.8", contrast_boost, None))
        except Exception:
            pass

        # 4. Sharpening filter (helps with slight lens softness / blur across bars)
        try:
            sharpened = gray.filter(ImageFilter.SHARPEN)
            variants.append(("sharpened", sharpened, None))
        except Exception:
            sharpened = gray

        # 5. Combined contrast + sharpening
        try:
            sharp_contrast = ImageEnhance.Contrast(sharpened).enhance(1.6)
            variants.append(("sharp_contrast", sharp_contrast, None))
        except Exception:
            pass

        # 6. Reasonable upscaling (helps with smaller barcodes whose bars blur into subpixels)
        max_dim = max(pil_image.width, pil_image.height)
        if max_dim < 2400:
            scale = min(2.0, 2400.0 / max(max_dim, 1))
            try:
                new_w = int(gray.width * scale)
                new_h = int(gray.height * scale)
                upscaled = gray.resize((new_w, new_h), Image.Resampling.LANCZOS)
                variants.append(("upscaled_lanczos", upscaled, None))
                variants.append(("upscaled_sharp", upscaled.filter(ImageFilter.SHARPEN), None))
            except Exception:
                pass

        # 7. Alternate binarizer: GlobalHistogram (handles non-uniform backgrounds)
        try:
            variants.append(
                ("global_hist_auto", auto, zxingcpp.Binarizer.GlobalHistogram)
            )
        except Exception:
            pass

        # Execute preprocessing variants sequentially; stop early when a retail GTIN is found
        for label, var_img, binarizer_opt in variants:
            try:
                kwargs = {}
                if binarizer_opt is not None:
                    kwargs["binarizer"] = binarizer_opt

                var_detected = zxingcpp.read_barcodes(var_img, **kwargs)
                if var_detected:
                    new_items = cls._parse_detected_barcodes(
                        var_detected, panel_index, panel_label
                    )
                    results = cls._merge_barcodes(results, new_items)
                    if _has_valid_retail_gtin(results):
                        logger.info("Retail GTIN barcode resolved via preprocessing pass '%s'", label)
                        return results
            except Exception as exc:
                logger.debug("Preprocessing pass '%s' encountered error: %s", label, exc)

        return results

    @classmethod
    def decode_bytes(
        cls,
        image_bytes: bytes,
        panel_index: Optional[int] = None,
        panel_label: Optional[str] = None,
    ) -> List[BarcodeItem]:
        """Decode all barcodes present in raw image bytes.

        Applies EXIF orientation normalization so smartphone camera photos
        are analyzed in their correct visual orientation.

        Args:
            image_bytes: Raw bytes of the image (JPEG, PNG, WEBP, etc.).
            panel_index: Optional panel index.
            panel_label: Optional panel label.

        Returns:
            List of detected BarcodeItem records.

        Raises:
            ValueError: If image bytes cannot be parsed as a valid image.
        """
        if not image_bytes:
            return []

        try:
            with Image.open(io.BytesIO(image_bytes)) as img:
                # Normalize smartphone camera orientation from EXIF metadata
                try:
                    img = ImageOps.exif_transpose(img) or img
                except Exception:
                    pass

                # Convert palette/CMYK to RGB if needed
                if img.mode not in ("L", "RGB", "RGBA"):
                    img = img.convert("RGB")
                return cls.decode_pil_image(
                    pil_image=img,
                    panel_index=panel_index,
                    panel_label=panel_label,
                )
        except Exception as exc:
            logger.warning("Failed to open image for barcode decoding: %s", exc)
            raise ValueError(f"Corrupted or invalid image data: {exc}") from exc
