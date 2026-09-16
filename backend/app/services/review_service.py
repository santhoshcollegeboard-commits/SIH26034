"""Review Service implementing the backend foundation for human-in-the-loop review.

Core Architecture Axiom:
AI extracts/proposes -> deterministic rules decide -> human resolves uncertainty.

The reviewer resolves evidence and observation uncertainty.
The reviewer does NOT directly decide statutory compliance status.
The DeterministicRuleEngine evaluates updated observations to produce the final disposition.
"""

from copy import deepcopy
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional

from backend.app.schemas.common import SourceRegion
from backend.app.schemas.compliance import (
    ComplianceVerdict,
    InspectionResult,
    RuleEvaluation,
)
from backend.app.schemas.extraction import ExtractionResult
from backend.app.schemas.review import (
    ALLOWED_REVIEW_FIELDS,
    FieldCorrection,
    FieldProvenance,
    ReviewAction,
    ReviewItem,
    ReviewItemsResponse,
    ReviewSubmissionResponse,
)
from backend.app.services.rule_engine_service import DeterministicRuleEngine

logger = logging.getLogger(__name__)

# Statutory reference mapping and verification guidance for statutory rules
RULE_METADATA_MAP: Dict[str, Dict[str, Any]] = {
    # Rule 6
    "LMR-2011-R06-01A-MFR-NAME": {
        "statutory_reference": "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "manufacturer_name",
        "what_to_verify": "Verify the manufacturer, packer, or importer name on the package label.",
    },
    "LMR-2011-R06-01A-MFR-ADDR": {
        "statutory_reference": "Rule 6(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "manufacturer_address",
        "what_to_verify": "Verify the complete physical address with PIN code on the package label.",
    },
    "LMR-2011-R06-01A-PACKER": {
        "statutory_reference": "Rule 6(1)(a) proviso of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "packer_name",
        "what_to_verify": "Verify packer name and address where commodity is packed by a third party.",
    },
    "LMR-2011-R06-01A-IMPORTER": {
        "statutory_reference": "Rule 6(1)(a) proviso of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "importer_name",
        "what_to_verify": "Verify importer name and address for imported packaged commodities.",
    },
    "LMR-2011-R06-01B-PROD-NAME": {
        "statutory_reference": "Rule 6(1)(b) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "product_name",
        "what_to_verify": "Verify the generic or common name of the commodity on the principal display panel.",
    },
    "LMR-2011-R06-01C-NET-QTY": {
        "statutory_reference": "Rule 6(1)(c) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "net_quantity",
        "what_to_verify": "Verify that net quantity is stated in standard legal metric units (g, kg, ml, l) with correct numerical representation.",
    },
    "LMR-2011-R06-01D-MFG-DATE": {
        "statutory_reference": "Rule 6(1)(d) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "month_year_of_manufacture",
        "what_to_verify": "Verify the month and year of manufacture, packing, or import (in MM/YYYY or Month YYYY format).",
    },
    "LMR-2011-R06-01E-MRP": {
        "statutory_reference": "Rule 6(1)(e) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "mrp",
        "what_to_verify": "Verify that Maximum Retail Price (MRP) is clearly stated in Indian Rupees inclusive of all taxes.",
    },
    "LMR-2011-R06-01F-DIMENSIONS": {
        "statutory_reference": "Rule 6(1)(f) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": None,
        "what_to_verify": "Verify package dimensions or size if relevant to commodity classification.",
    },
    "LMR-2011-R06-02-CONSUMER-CARE": {
        "statutory_reference": "Rule 6(2) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "consumer_care_details",
        "what_to_verify": "Verify presence of consumer care name/designation, phone number, email, and postal address.",
    },
    # Rule 7
    "LMR-2011-R07-01-PDP-AREA": {
        "statutory_reference": "Rule 7(1) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": None,
        "what_to_verify": "Verify total area of the Principal Display Panel (PDP) against package dimensions.",
    },
    "LMR-2011-R07-02-NUMERAL-HEIGHT": {
        "statutory_reference": "Rule 7(2) Table-I / Table-II of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "net_quantity",
        "what_to_verify": "Verify that physical numeral height of net quantity meets the statutory minimum in millimeters (Table-I/II).",
    },
    # Rule 8
    "LMR-2011-R08-01-PDP-LOCATION": {
        "statutory_reference": "Rule 8(1) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": None,
        "what_to_verify": "Verify that all mandatory declarations appear grouped together conspicuously.",
    },
    "LMR-2011-R08-01-FREE-SPACE": {
        "statutory_reference": "Rule 8(3) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "net_quantity",
        "what_to_verify": "Verify adequate clear surrounding space around net quantity declaration.",
    },
    # Rule 9
    "LMR-2011-R09-04-LANGUAGE": {
        "statutory_reference": "Rule 9(1)(a) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "product_name",
        "what_to_verify": "Verify that declarations are in English or Hindi (Devanagari script).",
    },
    "LMR-2011-R09-01A-LEGIBILITY": {
        "statutory_reference": "Rule 9(1)(b) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": None,
        "what_to_verify": "Verify that declarations are legible, clear, and conspicuous.",
    },
    "LMR-2011-R09-01B-CONTRAST": {
        "statutory_reference": "Rule 9(1)(b) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": None,
        "what_to_verify": "Verify sufficient visual contrast between declaration text and package background.",
    },
    "LMR-2011-R09-02-LIQUID-READ": {
        "statutory_reference": "Rule 9(2) of Legal Metrology (Packaged Commodities) Rules, 2011",
        "default_field": "net_quantity",
        "what_to_verify": "Verify declaration readability across translucent or transparent containers.",
    },
}


class ReviewService:
    """Service orchestrating human review inspection items and deterministic re-evaluation."""

    def __init__(self, rule_engine: Optional[DeterministicRuleEngine] = None) -> None:
        self.rule_engine = rule_engine or DeterministicRuleEngine()

    async def identify_review_items(
        self,
        extraction: ExtractionResult,
        inspection: Optional[InspectionResult] = None,
        package_metadata: Optional[Dict[str, Any]] = None,
        rules: Optional[List[int]] = None,
    ) -> ReviewItemsResponse:
        """Inspect rule evaluations and surface all items requiring human review.

        Exposes statutory rule details, observed values, confidence, bounding boxes
        (source_region) for UI highlighting, and actionable reviewer instructions.
        """
        meta = package_metadata or {}
        target_rules = rules if rules is not None else [6, 7, 8, 9]

        # If no inspection result is provided, evaluate rules deterministically
        if inspection is None:
            inspection = await self.rule_engine.evaluate(
                extraction=extraction,
                package_metadata=meta,
                rules=target_rules,
            )

        review_items: List[ReviewItem] = []
        for eval_record in inspection.rule_evaluations:
            if eval_record.status == ComplianceVerdict.REVIEW_REQUIRED:
                item = self._build_review_item(eval_record, extraction)
                review_items.append(item)

        total_count = len(inspection.rule_evaluations)
        review_count = len(review_items)
        requires_review = review_count > 0

        return ReviewItemsResponse(
            review_items=review_items,
            total_items=total_count,
            review_required_count=review_count,
            requires_human_review=requires_review,
            initial_disposition=inspection.overall_disposition,
        )

    def _build_review_item(
        self,
        evaluation: RuleEvaluation,
        extraction: ExtractionResult,
    ) -> ReviewItem:
        """Construct an enriched ReviewItem for an evaluation that requires review."""
        meta = RULE_METADATA_MAP.get(evaluation.rule_id, {})
        statutory_ref = meta.get(
            "statutory_reference",
            f"Statutory Rule {evaluation.rule_id} of Legal Metrology (Packaged Commodities) Rules, 2011",
        )
        target_field = meta.get("default_field")
        what_to_verify = meta.get(
            "what_to_verify",
            f"Verify physical package label evidence for rule {evaluation.rule_name}.",
        )

        observed_value = evaluation.observed_value
        confidence: Optional[float] = None
        source_region: Optional[SourceRegion] = evaluation.source_region

        # If there is an associated field on ExtractionResult, extract confidence and source region
        if target_field and hasattr(extraction, target_field):
            ext_field = getattr(extraction, target_field)
            if ext_field:
                if confidence is None:
                    confidence = ext_field.confidence
                if source_region is None:
                    source_region = ext_field.source_region
                if observed_value is None:
                    observed_value = ext_field.value

        return ReviewItem(
            rule_id=evaluation.rule_id,
            rule_version=evaluation.rule_version,
            rule_name=evaluation.rule_name,
            statutory_reference=statutory_ref,
            rule_status=ComplianceVerdict.REVIEW_REQUIRED,
            reason_for_review=evaluation.explanation,
            field_name=target_field,
            observed_value=observed_value,
            confidence=confidence,
            source_region=source_region,
            what_to_verify=what_to_verify,
        )

    async def apply_review_and_evaluate(
        self,
        original_extraction: ExtractionResult,
        corrections: List[FieldCorrection],
        package_metadata: Optional[Dict[str, Any]] = None,
        rules: Optional[List[int]] = None,
    ) -> ReviewSubmissionResponse:
        """Process human reviewer resolutions, preserve provenance, and deterministically re-evaluate.

        CRITICAL ARCHITECTURAL SAFEGUARD:
        The reviewer input does NOT set compliance status directly.
        Instead:
        Reviewer resolutions -> Updated observations -> DeterministicRuleEngine -> Final verdict.
        """
        meta = package_metadata or {}
        target_rules = rules if rules is not None else [6, 7, 8, 9]

        # 1. Determine baseline initial disposition before review
        initial_inspection = await self.rule_engine.evaluate(
            extraction=original_extraction,
            package_metadata=meta,
            rules=target_rules,
        )
        initial_disposition = initial_inspection.overall_disposition

        # 2. Build full provenance record and updated extraction dictionary
        updated_dict = original_extraction.model_dump()
        provenance: Dict[str, FieldProvenance] = {}
        now_iso = datetime.now(timezone.utc).isoformat()

        # Initialize provenance for all standard declaration fields
        for field_name in sorted(list(ALLOWED_REVIEW_FIELDS)):
            orig_field = getattr(original_extraction, field_name, None)
            if orig_field:
                provenance[field_name] = FieldProvenance(
                    field_name=field_name,
                    original_value=orig_field.value,
                    original_confidence=orig_field.confidence,
                    original_status=orig_field.status,
                    original_source_region=orig_field.source_region,
                    reviewed_value=orig_field.value,
                    reviewed_status=orig_field.status,
                    reviewed_source_region=orig_field.source_region,
                    action_taken="unmodified",
                    reviewer_notes=None,
                    reviewed_at=None,
                )

        # 3. Apply each structured reviewer correction
        for correction in corrections:
            f_name = correction.field_name
            if f_name not in ALLOWED_REVIEW_FIELDS:
                raise ValueError(f"Unknown field '{f_name}' in review corrections.")

            prov = provenance[f_name]
            prov.reviewer_notes = correction.reviewer_notes
            prov.reviewed_at = now_iso

            if correction.action == ReviewAction.CONFIRM:
                prov.action_taken = "confirmed"
                # Human confirmation establishes 100% certainty on the observed value
                prov.reviewed_value = prov.original_value
                prov.reviewed_status = prov.original_status
                if correction.source_region is not None:
                    prov.reviewed_source_region = correction.source_region
                    updated_dict[f_name]["source_region"] = correction.source_region.model_dump()
                updated_dict[f_name]["confidence"] = 1.0

            elif correction.action == ReviewAction.CORRECT:
                prov.action_taken = "corrected"
                prov.reviewed_value = correction.corrected_value
                prov.reviewed_status = "extracted"
                if correction.source_region is not None:
                    prov.reviewed_source_region = correction.source_region
                    updated_dict[f_name]["source_region"] = correction.source_region.model_dump()
                updated_dict[f_name]["value"] = correction.corrected_value
                updated_dict[f_name]["confidence"] = 1.0
                updated_dict[f_name]["status"] = "extracted"

            elif correction.action == ReviewAction.MARK_UNASSESSABLE:
                prov.action_taken = "marked_unassessable"
                prov.reviewed_value = None
                prov.reviewed_status = "unreadable"
                updated_dict[f_name]["value"] = None
                updated_dict[f_name]["confidence"] = 0.0
                updated_dict[f_name]["status"] = "unreadable"

        updated_extraction = ExtractionResult.model_validate(updated_dict)

        # 4. Deterministic Re-evaluation through RuleEngine
        new_inspection = await self.rule_engine.evaluate(
            extraction=updated_extraction,
            package_metadata=meta,
            rules=target_rules,
        )

        final_disposition = new_inspection.overall_disposition

        # 5. Extract any remaining items still requiring review
        remaining_items: List[ReviewItem] = []
        for eval_record in new_inspection.rule_evaluations:
            if eval_record.status == ComplianceVerdict.REVIEW_REQUIRED:
                item = self._build_review_item(eval_record, updated_extraction)
                remaining_items.append(item)

        requires_further_review = len(remaining_items) > 0

        summary = (
            f"Review completed. Processed {len(corrections)} field resolutions. "
            f"Disposition transitioned from {initial_disposition} to {final_disposition}. "
            f"Remaining review-required items: {len(remaining_items)}."
        )

        return ReviewSubmissionResponse(
            success=True,
            initial_disposition=initial_disposition,
            final_disposition=final_disposition,
            compliance=new_inspection,
            updated_extraction=updated_extraction,
            provenance=provenance,
            remaining_review_items=remaining_items,
            requires_further_review=requires_further_review,
            summary=summary,
        )
