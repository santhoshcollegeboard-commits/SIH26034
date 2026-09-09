"""Deterministic Legal Metrology Rule Engine implementation.

Architecture principle:
AI/OCR strictly extracts and proposes.
Deterministic rules decide statutory compliance.
Humans resolve uncertainty.
"""

from typing import Any, Dict, List, Union

from backend.app.schemas.compliance import (
    ComplianceResult,
    OverallVerdict,
    RuleEvaluation,
    RuleStatus,
)
from backend.app.schemas.extraction import ExtractionResult
from backend.app.services.interfaces.rule_engine import RuleEngine
from backend.app.services.rules.evaluators import (
    evaluate_consumer_care,
    evaluate_country_of_origin,
    evaluate_manufacturer_details,
    evaluate_manufacturing_date,
    evaluate_mrp_declaration,
    evaluate_net_quantity_presence,
    evaluate_product_name,
    evaluate_standard_metric_units,
    evaluate_unit_sale_price,
)


class DeterministicRuleEngine(RuleEngine):
    """Deterministic Legal Metrology compliance verification engine.

    Evaluates extracted packaging declarations against the Legal Metrology
    (Packaged Commodities) Rules, 2011 and amendments.
    """

    def __init__(self) -> None:
        self.evaluators = [
            evaluate_product_name,
            evaluate_manufacturer_details,
            evaluate_country_of_origin,
            evaluate_net_quantity_presence,
            evaluate_standard_metric_units,
            evaluate_manufacturing_date,
            evaluate_mrp_declaration,
            evaluate_consumer_care,
            evaluate_unit_sale_price,
        ]

    async def evaluate_compliance(
        self,
        package_metadata: Dict[str, Any],
        extracted_declarations: Union[Dict[str, Any], ExtractionResult],
    ) -> ComplianceResult:
        """Deterministically evaluate extracted declarations against statutory criteria.

        Args:
            package_metadata: Contextual data (e.g. is_imported flag, commodity type).
            extracted_declarations: Either ExtractionResult schema or dict.

        Returns:
            ComplianceResult with per-rule evaluations and aggregated overall verdict.
        """
        # Coerce dict into ExtractionResult if needed
        if isinstance(extracted_declarations, dict):
            extraction = ExtractionResult.model_validate(extracted_declarations)
        else:
            extraction = extracted_declarations

        evaluations: List[RuleEvaluation] = []
        for evaluator in self.evaluators:
            ev = evaluator(extraction, package_metadata or {})
            evaluations.append(ev)

        # Aggregate counts
        passed_count = sum(1 for e in evaluations if e.status == RuleStatus.PASS)
        failed_count = sum(1 for e in evaluations if e.status == RuleStatus.FAIL)
        review_count = sum(
            1 for e in evaluations if e.status == RuleStatus.NOT_VERIFIABLE
        )
        not_applicable_count = sum(
            1 for e in evaluations if e.status == RuleStatus.NOT_APPLICABLE
        )

        # Deterministic Verdict Aggregation Logic:
        # 1. Any confirmed statutory failure -> FAIL
        # 2. No confirmed failure, but unreadable or single-angle missing fields -> FLAGGED_FOR_REVIEW
        # 3. All applicable checks pass and no unresolved items -> PASS
        if failed_count > 0:
            overall_verdict = OverallVerdict.FAIL
            failed_names = [e.rule_name for e in evaluations if e.status == RuleStatus.FAIL]
            summary = (
                f"Non-compliant: {failed_count} statutory rule violation(s) identified "
                f"({', '.join(failed_names)})."
            )
        elif review_count > 0:
            overall_verdict = OverallVerdict.FLAGGED_FOR_REVIEW
            review_names = [
                e.rule_name for e in evaluations if e.status == RuleStatus.NOT_VERIFIABLE
            ]
            summary = (
                f"Flagged for inspector review: {review_count} declaration(s) were unreadable or "
                f"not detected on this packaging view ({', '.join(review_names)}). "
                "No statutory violations confirmed, but human verification of other package panels is required."
            )
        else:
            overall_verdict = OverallVerdict.PASS
            summary = (
                f"Compliant: All {passed_count} applicable statutory declarations comply with "
                "the Legal Metrology (Packaged Commodities) Rules, 2011."
            )

        return ComplianceResult(
            overall_verdict=overall_verdict,
            summary=summary,
            evaluations=evaluations,
            passed_count=passed_count,
            failed_count=failed_count,
            review_count=review_count,
            not_applicable_count=not_applicable_count,
        )
