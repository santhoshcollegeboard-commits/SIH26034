"""Multi-panel extraction aggregation service for PackCheck.

Combines per-panel OCR extraction proposals into a single unified
ExtractionResult. Tracks panel provenance, resolves complementary declarations,
and flags genuine cross-panel conflicts for inspector review.
"""

import re
from typing import Dict, List, Optional, Tuple

from backend.app.schemas.extraction import (
    CandidateField,
    ExtractedField,
    ExtractionResult,
    SourceRegion,
)


def _normalize_text(val: Optional[str]) -> str:
    """Normalize text for semantic comparison (strip whitespace, lowercase, collapse spaces)."""
    if not val:
        return ""
    # Collapse whitespace and lowercase
    cleaned = re.sub(r"\s+", " ", val.strip().lower())
    # Remove common punctuation noise for comparison
    cleaned = re.sub(r"[^\w\s₹\.]", "", cleaned)
    return cleaned


def _extract_numbers(val: str) -> List[float]:
    """Extract numeric floats from text."""
    matches = re.findall(r"\b\d+(?:\.\d+)?\b", val)
    res = []
    for m in matches:
        try:
            res.append(float(m))
        except ValueError:
            pass
    return res


def are_declarations_consistent(field_name: str, val1: str, val2: str) -> bool:
    """Determine whether two extracted strings for a given field are semantically consistent.
    
    Returns True if the strings agree, are subsets, or complement each other.
    Returns False if they represent conflicting/contradictory facts (e.g. different prices or quantities).
    """
    if not val1 or not val2:
        return True

    norm1 = _normalize_text(val1)
    norm2 = _normalize_text(val2)

    if norm1 == norm2:
        return True

    # Check substring / inclusion (e.g., "Assam Gold" in "Assam Gold CTC Black Tea")
    if norm1 in norm2 or norm2 in norm1:
        return True

    # Net quantity conflict check: different numeric quantities
    if field_name == "net_quantity":
        nums1 = _extract_numbers(val1)
        nums2 = _extract_numbers(val2)
        if nums1 and nums2 and nums1 != nums2:
            return False
        # Unit symbols check (e.g. g vs ml or kg vs l)
        u1 = re.findall(r"(?:kg|g|mg|ml|l)\b", val1, re.I)
        u2 = re.findall(r"(?:kg|g|mg|ml|l)\b", val2, re.I)
        if u1 and u2 and [x.lower() for x in u1] != [x.lower() for x in u2]:
            return False
        return True

    # MRP conflict check: different numeric prices
    if field_name == "mrp":
        nums1 = _extract_numbers(val1)
        nums2 = _extract_numbers(val2)
        if nums1 and nums2:
            # Check primary price numeral
            if abs(nums1[0] - nums2[0]) > 0.01:
                return False
        return True

    # Manufacturing date conflict check: different month or year
    if field_name == "month_year_of_manufacture":
        # Extract 4-digit years
        y1 = re.findall(r"\b20\d{2}\b", val1)
        y2 = re.findall(r"\b20\d{2}\b", val2)
        if y1 and y2 and y1 != y2:
            return False
        m1 = re.findall(r"\b(?:0?[1-9]|1[0-2])\b", val1)
        m2 = re.findall(r"\b(?:0?[1-9]|1[0-2])\b", val2)
        if m1 and m2 and m1[0] != m2[0]:
            return False
        return True

    # Country of origin: different countries
    if field_name == "country_of_origin":
        # If both mention different recognized nations
        for c1, c2 in [("india", "china"), ("india", "vietnam"), ("india", "japan"), ("usa", "india")]:
            if (c1 in norm1 and c2 in norm2) or (c2 in norm1 and c1 in norm2):
                return False
        return True

    # Default: if neither is a substring of the other, compare token overlap
    tokens1 = set(norm1.split())
    tokens2 = set(norm2.split())
    if tokens1 and tokens2:
        overlap = tokens1.intersection(tokens2)
        overlap_ratio = len(overlap) / min(len(tokens1), len(tokens2))
        if overlap_ratio >= 0.5:
            return True

    return False


class MultiPanelAggregator:
    """Aggregates multiple panel extraction results into a unified representation."""

    FIELD_NAMES = [
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

    @classmethod
    def aggregate(
        cls,
        extractions: List[ExtractionResult],
        panel_labels: Optional[List[str]] = None,
    ) -> ExtractionResult:
        """Aggregate per-panel extractions into a single unified ExtractionResult.

        Args:
            extractions: List of ExtractionResult objects from each panel.
            panel_labels: Optional user-provided or auto-generated panel labels (e.g. ['Front', 'Back']).

        Returns:
            Unified ExtractionResult with panel provenance and conflict flagging.
        """
        if not extractions:
            return ExtractionResult()

        num_panels = len(extractions)
        labels = panel_labels or [f"Panel {i + 1}" for i in range(num_panels)]

        # If only one panel was provided, tag panel info and return
        if num_panels == 1:
            return cls._tag_single_panel(extractions[0], label=labels[0] if labels else "Panel 1")

        unified_fields: Dict[str, ExtractedField] = {}

        for field_name in cls.FIELD_NAMES:
            candidates: List[CandidateField] = []
            unreadable_candidates: List[CandidateField] = []

            for idx, ext in enumerate(extractions):
                field_obj: Optional[ExtractedField] = getattr(ext, field_name, None)
                if not field_obj:
                    continue

                panel_name = labels[idx] if idx < len(labels) else f"Panel {idx + 1}"
                reg = field_obj.source_region
                if reg:
                    # Enrich region with panel metadata
                    reg = SourceRegion(
                        x=reg.x,
                        y=reg.y,
                        width=reg.width,
                        height=reg.height,
                        image_index=idx,
                        panel_label=panel_name,
                    )

                cand = CandidateField(
                    value=field_obj.value,
                    confidence=field_obj.confidence,
                    source_region=reg,
                    source_image_index=idx,
                    source_panel_label=panel_name,
                )

                if field_obj.status == "extracted" and field_obj.value and field_obj.value.strip():
                    candidates.append(cand)
                elif field_obj.status == "unreadable":
                    unreadable_candidates.append(cand)

            # Case 1: No extracted values found across any panel
            if not candidates:
                if unreadable_candidates:
                    # At least one panel detected the field but could not read it
                    first_unreadable = unreadable_candidates[0]
                    unified_fields[field_name] = ExtractedField(
                        value=None,
                        confidence=None,
                        source_region=first_unreadable.source_region,
                        status="unreadable",
                        source_image_index=first_unreadable.source_image_index,
                        source_panel_label=first_unreadable.source_panel_label,
                        all_candidates=unreadable_candidates,
                    )
                else:
                    # Not found on any panel
                    unified_fields[field_name] = ExtractedField(
                        value=None,
                        confidence=None,
                        source_region=None,
                        status="not_found",
                    )
                continue

            # Case 2: Exactly one panel extracted this field
            if len(candidates) == 1:
                cand = candidates[0]
                unified_fields[field_name] = ExtractedField(
                    value=cand.value,
                    confidence=cand.confidence,
                    source_region=cand.source_region,
                    status="extracted",
                    source_image_index=cand.source_image_index,
                    source_panel_label=cand.source_panel_label,
                    all_candidates=candidates,
                )
                continue

            # Case 3: Multiple panels extracted this field - check consistency
            primary_val = candidates[0].value or ""
            has_conflict = False
            conflicting_pairs: List[Tuple[str, str, str, str]] = []

            for other_cand in candidates[1:]:
                other_val = other_cand.value or ""
                if not are_declarations_consistent(field_name, primary_val, other_val):
                    has_conflict = True
                    conflicting_pairs.append(
                        (
                            candidates[0].source_panel_label or f"Panel {candidates[0].source_image_index + 1}",
                            primary_val,
                            other_cand.source_panel_label or f"Panel {other_cand.source_image_index + 1}",
                            other_val,
                        )
                    )

            if has_conflict:
                # Genuine conflict detected
                conflict_notes = "; ".join(
                    f"{p1}: '{v1}' vs {p2}: '{v2}'" for p1, v1, p2, v2 in conflicting_pairs
                )
                unified_fields[field_name] = ExtractedField(
                    value=f"CONFLICT: {conflict_notes}",
                    confidence=min((c.confidence for c in candidates if c.confidence is not None), default=0.5),
                    source_region=candidates[0].source_region,
                    status="conflict",
                    source_image_index=candidates[0].source_image_index,
                    source_panel_label=candidates[0].source_panel_label,
                    all_candidates=candidates,
                    conflict_details=conflict_notes,
                )
            else:
                # All candidates are consistent - select best representation
                # Preference: higher confidence, then longer string (more complete)
                best_cand = max(
                    candidates,
                    key=lambda c: (
                        c.confidence if c.confidence is not None else 0.0,
                        len(c.value or ""),
                    ),
                )
                unified_fields[field_name] = ExtractedField(
                    value=best_cand.value,
                    confidence=best_cand.confidence,
                    source_region=best_cand.source_region,
                    status="extracted",
                    source_image_index=best_cand.source_image_index,
                    source_panel_label=best_cand.source_panel_label,
                    all_candidates=candidates,
                )

        return ExtractionResult(**unified_fields)

    @classmethod
    def _tag_single_panel(
        cls, extraction: ExtractionResult, label: str = "Panel 1"
    ) -> ExtractionResult:
        """Tag a single panel's fields with image index 0 and panel label."""
        tagged_fields: Dict[str, ExtractedField] = {}
        for field_name in cls.FIELD_NAMES:
            field_obj: Optional[ExtractedField] = getattr(extraction, field_name, None)
            if not field_obj:
                tagged_fields[field_name] = ExtractedField()
                continue

            reg = field_obj.source_region
            if reg:
                reg = SourceRegion(
                    x=reg.x,
                    y=reg.y,
                    width=reg.width,
                    height=reg.height,
                    image_index=0,
                    panel_label=label,
                )

            cand = CandidateField(
                value=field_obj.value,
                confidence=field_obj.confidence,
                source_region=reg,
                source_image_index=0,
                source_panel_label=label,
            )

            tagged_fields[field_name] = ExtractedField(
                value=field_obj.value,
                confidence=field_obj.confidence,
                source_region=reg,
                status=field_obj.status,
                source_image_index=0,
                source_panel_label=label,
                all_candidates=[cand] if field_obj.status == "extracted" else None,
            )

        return ExtractionResult(**tagged_fields)
