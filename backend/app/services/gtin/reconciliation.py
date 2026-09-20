"""Deterministic OCR ↔ GTIN product identity reconciliation engine.

Compares declarations proposed by OCR against authoritative GTIN product records
with conservative text and physical unit normalization (e.g. 500 g == 0.5 kg).
"""

import logging
import re
from typing import List, Optional, Tuple

from backend.app.schemas.barcode import BarcodeSummary
from backend.app.schemas.extraction import ExtractionResult
from backend.app.schemas.gtin_identity import (
    FieldComparison,
    FieldMatchStatus,
    GTINIdentityVerification,
    GTINLookupStatus,
    GTINProductRecord,
    IdentityVerificationStatus,
)
from backend.app.services.gtin.providers import GTINProvider, get_gtin_provider
from backend.app.services.gtin.selector import select_gtin_candidate

logger = logging.getLogger(__name__)


# =============================================================================
# Quantity & Unit Normalization
# =============================================================================

# Unit conversion tables to base metric units
_WEIGHT_CONVERSIONS = {
    "kg": 1000.0,
    "kgs": 1000.0,
    "kilo": 1000.0,
    "kilos": 1000.0,
    "kilogram": 1000.0,
    "kilograms": 1000.0,
    "g": 1.0,
    "gm": 1.0,
    "gms": 1.0,
    "gram": 1.0,
    "grams": 1.0,
    "mg": 0.001,
    "mgs": 0.001,
    "milligram": 0.001,
}

_VOLUME_CONVERSIONS = {
    "l": 1000.0,
    "ltr": 1000.0,
    "ltrs": 1000.0,
    "litre": 1000.0,
    "litres": 1000.0,
    "liter": 1000.0,
    "liters": 1000.0,
    "ml": 1.0,
    "mls": 1.0,
    "millilitre": 1.0,
    "millilitres": 1.0,
    "cl": 10.0,
}

_COUNT_CONVERSIONS = {
    "n": 1.0,
    "u": 1.0,
    "unit": 1.0,
    "units": 1.0,
    "pc": 1.0,
    "pcs": 1.0,
    "piece": 1.0,
    "pieces": 1.0,
}


def parse_canonical_quantity(val_str: Optional[str], unit_hint: Optional[str] = None) -> Optional[Tuple[float, str]]:
    """Parse a quantity string into a canonical normalized (numeric_val, base_unit) tuple.

    Base units:
    - Mass: 'g'
    - Volume: 'ml'
    - Count: 'units'

    Examples:
        '500 g' -> (500.0, 'g')
        '0.5 kg' -> (500.0, 'g')
        '1 L' -> (1000.0, 'ml')
        '1000 ml' -> (1000.0, 'ml')
    """
    if not val_str:
        return None

    cleaned = val_str.strip().lower()

    # Combine with unit hint if available and not present in string
    if unit_hint and not any(u in cleaned for u in ("g", "kg", "l", "ml", "n", "unit", "pc")):
        cleaned = f"{cleaned} {unit_hint.lower()}"

    # Regex to capture numeric part and trailing unit string
    m = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*([a-zA-Z]+)?", cleaned)
    if not m:
        return None

    try:
        num = float(m.group(1))
    except ValueError:
        return None

    unit = (m.group(2) or (unit_hint.lower() if unit_hint else "")).strip()
    if not unit:
        return None

    if unit in _WEIGHT_CONVERSIONS:
        return (num * _WEIGHT_CONVERSIONS[unit], "g")
    if unit in _VOLUME_CONVERSIONS:
        return (num * _VOLUME_CONVERSIONS[unit], "ml")
    if unit in _COUNT_CONVERSIONS:
        return (num * _COUNT_CONVERSIONS[unit], "units")

    return None


# =============================================================================
# Text Normalization Helpers
# =============================================================================

_STOPWORDS = {"and", "&", "of", "the", "in", "for", "with", "a", "an", "premium", "pure"}
_CORP_SUFFIXES = {
    "pvt", "ltd", "private", "limited", "llp", "inc", "corp", "corporation",
    "co", "company", "enterprises", "estates", "industries", "products"
}


def tokenize_text(text: Optional[str], remove_corp: bool = False) -> List[str]:
    """Tokenize and normalize text into lower-case alphanumeric tokens."""
    if not text:
        return []
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    tokens = [t for t in clean.split() if t and t not in _STOPWORDS]
    if remove_corp:
        tokens = [t for t in tokens if t not in _CORP_SUFFIXES]
    return tokens


# =============================================================================
# Reconciler Implementation
# =============================================================================

class GTINReconciler:
    """Reconciles OCR label declarations against authoritative GTIN product records."""

    def __init__(self, provider: Optional[GTINProvider] = None) -> None:
        self._provider = provider

    @property
    def provider(self) -> GTINProvider:
        if self._provider is not None:
            return self._provider
        return get_gtin_provider()

    async def reconcile(
        self,
        barcode_summary: Optional[BarcodeSummary],
        extraction_result: Optional[ExtractionResult],
    ) -> GTINIdentityVerification:
        """Execute full GTIN selection, product lookup, and OCR reconciliation.

        Args:
            barcode_summary: The decoded barcodes from BarcodeService.
            extraction_result: Consolidated OCR label declarations.

        Returns:
            Structured GTINIdentityVerification result.
        """
        # 1. Resolve candidate GTIN
        is_local_catalog = self.provider.__class__.__name__ == "LocalCatalogProvider"
        is_off = self.provider.__class__.__name__ == "OpenFoodFactsProvider"
        if is_local_catalog:
            provider_name = "Local Product Catalog (Prototype)"
        elif is_off:
            provider_name = "Open Food Facts"
        else:
            provider_name = "GS1 / DataKart"

        selection = select_gtin_candidate(barcode_summary)

        if not selection.selected_gtin:
            return GTINIdentityVerification(
                gtin=None,
                lookup_status=selection.status,
                product_record=None,
                overall_status=IdentityVerificationStatus.NOT_VERIFIABLE,
                field_comparisons=[],
                summary=selection.message,
                provider_name=provider_name,
            )

        target_gtin = selection.selected_gtin

        # 2. Product identity provider lookup
        try:
            product_record = await self.provider.get_product(target_gtin)
        except Exception as exc:
            logger.error("Error during GTIN provider lookup for %s: %s", target_gtin, exc)
            return GTINIdentityVerification(
                gtin=target_gtin,
                lookup_status=GTINLookupStatus.SERVICE_UNAVAILABLE,
                product_record=None,
                overall_status=IdentityVerificationStatus.NOT_VERIFIABLE,
                field_comparisons=[],
                summary=f"Product identity lookup service unavailable for GTIN {target_gtin}: {exc}",
                provider_name=provider_name,
            )

        if not product_record:
            if is_local_catalog:
                summary = (
                    f"GTIN {target_gtin} was not found in the local prototype product catalog. "
                    "Product identity could not be verified against the available product database."
                )
            elif is_off:
                summary = (
                    f"GTIN {target_gtin} was not found in Open Food Facts. "
                    "Product identity could not be verified against the available product database."
                )
            else:
                summary = (
                    f"GTIN {target_gtin} was not found in the authoritative product registry. "
                    "Cannot verify product identity against packaging declarations."
                )
            return GTINIdentityVerification(
                gtin=target_gtin,
                lookup_status=GTINLookupStatus.NOT_FOUND,
                product_record=None,
                overall_status=IdentityVerificationStatus.NOT_VERIFIABLE,
                field_comparisons=[],
                summary=summary,
                provider_name=provider_name,
            )

        # 3. Perform field-level comparisons if extraction is available
        comparisons: List[FieldComparison] = []
        if extraction_result:
            comparisons.append(self._compare_product_name(extraction_result, product_record))
            comparisons.append(self._compare_brand(extraction_result, product_record))
            comparisons.append(self._compare_net_quantity(extraction_result, product_record))
            comparisons.append(self._compare_company(extraction_result, product_record))

        # 4. Synthesize overall identity verdict
        mismatches = [c for c in comparisons if c.status == FieldMatchStatus.MISMATCH]
        matches = [c for c in comparisons if c.status == FieldMatchStatus.MATCH]
        partials = [c for c in comparisons if c.status == FieldMatchStatus.PARTIAL_MATCH]
        comparables = [c for c in comparisons if c.status != FieldMatchStatus.NOT_COMPARABLE]

        if is_local_catalog or (product_record.source and ("Prototype Catalog" in product_record.source or "Local Product Catalog" in product_record.source)):
            source_label = "local prototype product record"
        elif is_off or (product_record.source and "Open Food Facts" in product_record.source):
            source_label = "Open Food Facts product record"
        else:
            source_label = "authoritative product record"

        if not comparables:
            overall_status = IdentityVerificationStatus.NOT_VERIFIABLE
            summary = (
                f"GTIN {target_gtin} resolved to '{product_record.product_name or product_record.brand_name}', "
                "but no comparable label declarations were extracted from packaging."
            )
        elif mismatches:
            overall_status = IdentityVerificationStatus.MISMATCH
            mismatched_fields = ", ".join(c.field_name for c in mismatches)
            summary = (
                f"Identity discrepancy detected for GTIN {target_gtin}: "
                f"mismatch on [{mismatched_fields}]. Packaging declarations conflict with {source_label}."
            )
        elif matches:
            overall_status = IdentityVerificationStatus.MATCH
            matched_fields = ", ".join(c.field_name for c in matches)
            summary = (
                f"Product identity verified for GTIN {target_gtin}: "
                f"packaging declarations match {source_label} on [{matched_fields}]."
            )
        elif partials:
            overall_status = IdentityVerificationStatus.PARTIAL_MATCH
            summary = (
                f"Product identity partially matches GTIN {target_gtin} record. "
                "No direct contradictions detected, but some declaration variations exist."
            )
        else:
            overall_status = IdentityVerificationStatus.NOT_VERIFIABLE
            summary = f"Insufficient comparable data to verify identity for GTIN {target_gtin}."

        return GTINIdentityVerification(
            gtin=target_gtin,
            lookup_status=GTINLookupStatus.FOUND,
            product_record=product_record,
            overall_status=overall_status,
            field_comparisons=comparisons,
            summary=summary,
            provider_name=provider_name,
        )

    # -------------------------------------------------------------------------
    # Field-level Comparators
    # -------------------------------------------------------------------------

    def _compare_product_name(
        self, extraction: ExtractionResult, record: GTINProductRecord
    ) -> FieldComparison:
        ocr_name = (extraction.product_name.value or "").strip()
        ocr_generic = (extraction.common_or_generic_name.value or "").strip()
        gtin_name = (record.product_name or record.product_description or "").strip()

        is_local_catalog = bool(
            record.source and ("Prototype Catalog" in record.source or "Local Product Catalog" in record.source)
        )
        is_off = bool(record.source and "Open Food Facts" in record.source)
        source_record_label = (
            "Local catalog record" if is_local_catalog
            else "Open Food Facts record" if is_off
            else "Authoritative GTIN record"
        )
        source_ref_label = (
            "local catalog record" if is_local_catalog
            else "Open Food Facts" if is_off
            else "registered record"
        )

        if not ocr_name and not ocr_generic:
            return FieldComparison(
                field_name="product_name",
                ocr_value=None,
                gtin_value=gtin_name or None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message="Product name was not extracted from packaging label.",
            )

        if not gtin_name:
            return FieldComparison(
                field_name="product_name",
                ocr_value=ocr_name or ocr_generic,
                gtin_value=None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"{source_record_label} contains no product name.",
            )

        combined_ocr = f"{ocr_name} {ocr_generic}".lower()
        ocr_tokens = set(tokenize_text(combined_ocr))
        gtin_tokens = set(tokenize_text(gtin_name))

        common = ocr_tokens.intersection(gtin_tokens)
        if not ocr_tokens or not gtin_tokens:
            status = FieldMatchStatus.NOT_COMPARABLE
            msg = "Insufficient descriptive tokens for comparison."
        elif common == gtin_tokens or common == ocr_tokens or (len(common) / min(len(ocr_tokens), len(gtin_tokens)) >= 0.7):
            status = FieldMatchStatus.MATCH
            msg = f"Product title matches {source_ref_label} ('{ocr_name or ocr_generic}' vs '{gtin_name}')."
        elif len(common) >= 1 and (len(common) / min(len(ocr_tokens), len(gtin_tokens)) >= 0.3):
            status = FieldMatchStatus.PARTIAL_MATCH
            msg = f"Product title partially aligns with {source_ref_label} (common: {', '.join(common)})."
        else:
            status = FieldMatchStatus.MISMATCH
            msg = f"Product title conflicts with {source_ref_label} ('{ocr_name or ocr_generic}' vs '{gtin_name}')."

        return FieldComparison(
            field_name="product_name",
            ocr_value=ocr_name or ocr_generic,
            gtin_value=gtin_name,
            status=status,
            message=msg,
        )

    def _compare_brand(
        self, extraction: ExtractionResult, record: GTINProductRecord
    ) -> FieldComparison:
        gtin_brand = (record.brand_name or "").strip()
        ocr_product = (extraction.product_name.value or "").strip()
        is_local_catalog = bool(
            record.source and ("Prototype Catalog" in record.source or "Local Product Catalog" in record.source)
        )
        is_off = bool(record.source and "Open Food Facts" in record.source)
        source_record_label = (
            "Local catalog record" if is_local_catalog
            else "Open Food Facts record" if is_off
            else "Authoritative GTIN record"
        )
        brand_prefix = "Brand" if (is_off or is_local_catalog) else "Registered brand"

        if not gtin_brand:
            return FieldComparison(
                field_name="brand",
                ocr_value=ocr_product or None,
                gtin_value=None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"{source_record_label} contains no brand name." if (is_off or is_local_catalog) else f"{source_record_label} contains no registered brand name.",
            )

        if not ocr_product:
            return FieldComparison(
                field_name="brand",
                ocr_value=None,
                gtin_value=gtin_brand,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"No product/brand name detected on packaging to compare with {brand_prefix.lower()}.",
            )

        brand_tokens = set(tokenize_text(gtin_brand))
        ocr_tokens = set(tokenize_text(ocr_product))

        if brand_tokens.issubset(ocr_tokens):
            return FieldComparison(
                field_name="brand",
                ocr_value=ocr_product,
                gtin_value=gtin_brand,
                status=FieldMatchStatus.MATCH,
                message=f"{brand_prefix} '{gtin_brand}' is present in packaging label declaration.",
            )

        common = brand_tokens.intersection(ocr_tokens)
        if common:
            return FieldComparison(
                field_name="brand",
                ocr_value=ocr_product,
                gtin_value=gtin_brand,
                status=FieldMatchStatus.PARTIAL_MATCH,
                message=f"Partial brand match ('{gtin_brand}' vs '{ocr_product}').",
            )

        return FieldComparison(
            field_name="brand",
            ocr_value=ocr_product,
            gtin_value=gtin_brand,
            status=FieldMatchStatus.MISMATCH,
            message=f"{brand_prefix} '{gtin_brand}' not found in label product name '{ocr_product}'.",
        )

    def _compare_net_quantity(
        self, extraction: ExtractionResult, record: GTINProductRecord
    ) -> FieldComparison:
        ocr_qty_str = (extraction.net_quantity.value or "").strip()
        gtin_qty_str = (record.net_quantity or "").strip()
        gtin_unit = (record.net_quantity_unit or "").strip()

        is_local_catalog = bool(
            record.source and ("Prototype Catalog" in record.source or "Local Product Catalog" in record.source)
        )
        is_off = bool(record.source and "Open Food Facts" in record.source)
        source_record_label = (
            "Local catalog record" if is_local_catalog
            else "Open Food Facts record" if is_off
            else "Authoritative GTIN record"
        )
        source_specifies = (
            "local catalog" if is_local_catalog
            else "Open Food Facts" if is_off
            else "registry"
        )

        if not ocr_qty_str:
            return FieldComparison(
                field_name="net_quantity",
                ocr_value=None,
                gtin_value=f"{gtin_qty_str} {gtin_unit}".strip() or None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message="Net quantity declaration not extracted from packaging.",
            )

        if not gtin_qty_str:
            return FieldComparison(
                field_name="net_quantity",
                ocr_value=ocr_qty_str,
                gtin_value=None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"{source_record_label} specifies no net quantity.",
            )

        parsed_ocr = parse_canonical_quantity(ocr_qty_str)
        parsed_gtin = parse_canonical_quantity(gtin_qty_str, unit_hint=gtin_unit)

        if not parsed_ocr or not parsed_gtin:
            return FieldComparison(
                field_name="net_quantity",
                ocr_value=ocr_qty_str,
                gtin_value=f"{gtin_qty_str} {gtin_unit}".strip(),
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"Could not parse physical quantity units for comparison ('{ocr_qty_str}' vs '{gtin_qty_str} {gtin_unit}').",
            )

        ocr_val, ocr_unit = parsed_ocr
        gtin_val, gtin_unit_base = parsed_gtin

        if ocr_unit != gtin_unit_base:
            return FieldComparison(
                field_name="net_quantity",
                ocr_value=ocr_qty_str,
                gtin_value=f"{gtin_qty_str} {gtin_unit}".strip(),
                status=FieldMatchStatus.MISMATCH,
                message=f"Incompatible quantity dimensions (mass vs volume/count: '{ocr_qty_str}' vs '{gtin_qty_str} {gtin_unit}').",
            )

        # Allow 0.1% floating tolerance
        if abs(ocr_val - gtin_val) <= (0.001 * max(gtin_val, 1.0)):
            return FieldComparison(
                field_name="net_quantity",
                ocr_value=ocr_qty_str,
                gtin_value=f"{gtin_qty_str} {gtin_unit}".strip(),
                status=FieldMatchStatus.MATCH,
                message=f"Net quantities are physically equivalent ({ocr_val} {ocr_unit}).",
            )

        return FieldComparison(
            field_name="net_quantity",
            ocr_value=ocr_qty_str,
            gtin_value=f"{gtin_qty_str} {gtin_unit}".strip(),
            status=FieldMatchStatus.MISMATCH,
            message=f"Net quantity discrepancy: label declares '{ocr_qty_str}' ({ocr_val} {ocr_unit}), but {source_specifies} specifies '{gtin_qty_str} {gtin_unit}' ({gtin_val} {gtin_unit_base}).",
        )

    def _compare_company(
        self, extraction: ExtractionResult, record: GTINProductRecord
    ) -> FieldComparison:
        ocr_mfg = (extraction.manufacturer_name.value or extraction.packer_name.value or "").strip()
        gtin_company = (record.company_name or "").strip()
        is_local_catalog = bool(
            record.source and ("Prototype Catalog" in record.source or "Local Product Catalog" in record.source)
        )
        is_off = bool(record.source and "Open Food Facts" in record.source)
        source_record_label = (
            "Local catalog record" if is_local_catalog
            else "Open Food Facts record" if is_off
            else "Authoritative GTIN record"
        )
        owner_ref = "manufacturer" if is_local_catalog else "brand owner" if is_off else "registered brand owner"
        company_ref = "manufacturer" if is_local_catalog else "company" if is_off else "registered company"

        if not ocr_mfg:
            return FieldComparison(
                field_name="manufacturer",
                ocr_value=None,
                gtin_value=gtin_company or None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message="Manufacturer/packer name not extracted from packaging label.",
            )

        if not gtin_company:
            return FieldComparison(
                field_name="manufacturer",
                ocr_value=ocr_mfg,
                gtin_value=None,
                status=FieldMatchStatus.NOT_COMPARABLE,
                message=f"{source_record_label} contains no manufacturer name." if is_local_catalog else f"{source_record_label} contains no brand owner/company name." if is_off else f"{source_record_label} contains no registered company name.",
            )

        ocr_tokens = set(tokenize_text(ocr_mfg, remove_corp=True))
        gtin_tokens = set(tokenize_text(gtin_company, remove_corp=True))

        common = ocr_tokens.intersection(gtin_tokens)
        if not ocr_tokens or not gtin_tokens:
            status = FieldMatchStatus.NOT_COMPARABLE
            msg = "Insufficient tokens for company name comparison."
        elif common == gtin_tokens or common == ocr_tokens or (len(common) / min(len(ocr_tokens), len(gtin_tokens)) >= 0.7):
            status = FieldMatchStatus.MATCH
            msg = f"Manufacturer matches {owner_ref} ('{ocr_mfg}' vs '{gtin_company}')."
        elif len(common) >= 1 and (len(common) / min(len(ocr_tokens), len(gtin_tokens)) >= 0.3):
            status = FieldMatchStatus.PARTIAL_MATCH
            msg = f"Manufacturer name partially matches {company_ref} ('{ocr_mfg}' vs '{gtin_company}')."
        else:
            status = FieldMatchStatus.MISMATCH
            msg = f"Manufacturer name differs from {company_ref} ('{ocr_mfg}' vs '{gtin_company}')."

        return FieldComparison(
            field_name="manufacturer",
            ocr_value=ocr_mfg,
            gtin_value=gtin_company,
            status=status,
            message=msg,
        )


# Global reconciler instance
_gtin_reconciler: Optional[GTINReconciler] = None


def get_gtin_reconciler() -> GTINReconciler:
    """Dependency provider returning singleton GTINReconciler."""
    global _gtin_reconciler
    if _gtin_reconciler is None:
        _gtin_reconciler = GTINReconciler()
    return _gtin_reconciler


def set_gtin_reconciler(reconciler: Optional[GTINReconciler]) -> None:
    """Override the global reconciler instance (used for testing)."""
    global _gtin_reconciler
    _gtin_reconciler = reconciler
