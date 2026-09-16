"""Deterministic Rule Engine Service for Legal Metrology compliance verification.

Implements the RuleEngine interface, orchestrating deterministic statutory evaluations
against extracted packaging declarations without invoking external AI models.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from backend.app.schemas.compliance import (
    ComplianceVerdict,
    InspectionResult,
    RuleEvaluation,
)
from backend.app.schemas.extraction import ExtractionResult
from backend.app.services.interfaces.rule_engine import RuleEngine
from rules import (
    aggregate_disposition,
    evaluate_all_rules,
    evaluate_rule_6,
    evaluate_rule_7,
    evaluate_rule_8,
    evaluate_rule_9,
)


class DeterministicRuleEngine(RuleEngine):
    """Deterministic statutory compliance verification engine.

    Follows the core architecture axiom:
    AI extracts and proposes; deterministic rules decide compliance; humans resolve uncertainty.
    """

    def __init__(self, default_rules: Optional[List[int]] = None) -> None:
        self.default_rules = default_rules

    async def evaluate(
        self,
        extraction: ExtractionResult,
        package_metadata: Optional[Dict[str, Any]] = None,
        package_id: Optional[str] = None,
        include_unassessable: bool = False,
        rules: Optional[List[int]] = None,
    ) -> InspectionResult:
        """Evaluate structured ExtractionResult against statutory compliance rules.

        Args:
            extraction: Structured extraction observations from OCR stage.
            package_metadata: Optional metadata (e.g., imported flag, third-party packing, calibration).
            package_id: Optional commodity package identifier.
            include_unassessable: Whether to include clauses mapped as not assessable.
            rules: Optional list of rule numbers to evaluate (e.g. [6], [7], [8], [9], or [6, 7, 8, 9]).

        Returns:
            InspectionResult with overall disposition and list of RuleEvaluation records.
        """
        meta = package_metadata or {}
        target_rules = rules if rules is not None else meta.get("rules", self.default_rules)

        evaluations: List[RuleEvaluation] = []

        if target_rules is None:
            evaluations.extend(
                evaluate_rule_6(
                    extraction=extraction,
                    package_metadata=meta,
                    include_unassessable=include_unassessable,
                )
            )
        else:
            if 6 in target_rules:
                evaluations.extend(
                    evaluate_rule_6(
                        extraction=extraction,
                        package_metadata=meta,
                        include_unassessable=include_unassessable,
                    )
                )
            if 7 in target_rules:
                evaluations.extend(
                    evaluate_rule_7(
                        extraction=extraction,
                        package_metadata=meta,
                    )
                )
            if 8 in target_rules:
                evaluations.extend(
                    evaluate_rule_8(
                        extraction=extraction,
                        package_metadata=meta,
                    )
                )
            if 9 in target_rules:
                evaluations.extend(
                    evaluate_rule_9(
                        extraction=extraction,
                        package_metadata=meta,
                    )
                )

        overall_disposition = aggregate_disposition(evaluations)

        # Build concise audit summary
        pass_count = sum(1 for e in evaluations if e.status == ComplianceVerdict.PASS)
        fail_count = sum(1 for e in evaluations if e.status == ComplianceVerdict.FAIL)
        review_count = sum(
            1 for e in evaluations if e.status == ComplianceVerdict.REVIEW_REQUIRED
        )
        not_assessable_count = sum(
            1 for e in evaluations if e.status == ComplianceVerdict.NOT_ASSESSABLE
        )

        summary = (
            f"Disposition: {overall_disposition}. Evaluated {len(evaluations)} rules "
            f"({pass_count} PASS, {fail_count} FAIL, {review_count} REVIEW_REQUIRED, "
            f"{not_assessable_count} NOT_ASSESSABLE)."
        )

        return InspectionResult(
            overall_disposition=overall_disposition,
            rule_evaluations=evaluations,
            summary=summary,
            package_id=package_id,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
        )

    async def evaluate_compliance(
        self, package_metadata: Dict[str, Any], extracted_declarations: Union[Dict[str, Any], ExtractionResult]
    ) -> Dict[str, Any]:
        """Fulfill abstract RuleEngine contract accepting dictionaries or Pydantic models."""
        if isinstance(extracted_declarations, ExtractionResult):
            extraction = extracted_declarations
        else:
            extraction = ExtractionResult.model_validate(extracted_declarations)

        inspection_result = await self.evaluate(
            extraction=extraction,
            package_metadata=package_metadata,
            package_id=package_metadata.get("package_id") if package_metadata else None,
        )
        return inspection_result.model_dump()

    async def evaluate_all(
        self,
        extraction: ExtractionResult,
        package_metadata: Optional[Dict[str, Any]] = None,
        package_id: Optional[str] = None,
        include_unassessable: bool = False,
    ) -> InspectionResult:
        """Evaluate all implemented statutory rules (Rules 6, 7, 8, and 9)."""
        return await self.evaluate(
            extraction=extraction,
            package_metadata=package_metadata,
            package_id=package_id,
            include_unassessable=include_unassessable,
            rules=[6, 7, 8, 9],
        )
