"""Result Service constructing report-ready inspection results from the Evidence Ledger.

Strict presentation-only layer:
- Fetches persisted inspection audit trails from EvidenceLedgerService.
- Assembles statutory traceability and decision summaries.
- Never recalculates or overrides compliance dispositions.
- Applies the centralized missing-data policy across all presentation fields.
"""

import logging
from typing import List, Optional

from backend.app.schemas.result import (
    InspectionResultReport,
    ObservationPresentation,
    ReviewActionPresentation,
    RuleEvaluationPresentation,
    TraceabilityInfo,
)
from backend.app.services.formatters import (
    EMPTY_EVIDENCE_MESSAGE,
    EMPTY_OBSERVATIONS_MESSAGE,
    EMPTY_REVIEW_ACTIONS_MESSAGE,
    EMPTY_RULE_EVALUATIONS_MESSAGE,
    MANDATORY_DECLARATION_FIELDS,
    NOT_APPLICABLE_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    NOT_RECORDED_MESSAGE,
    format_confidence,
    format_missing_value,
    format_quality_summary,
    format_source_region,
)
from backend.app.services.ledger_service import EvidenceLedgerService

logger = logging.getLogger(__name__)


class ResultService:
    """Service that retrieves and formats inspection results for reporting."""

    def __init__(self, ledger_service: Optional[EvidenceLedgerService] = None) -> None:
        self.ledger_service = ledger_service or EvidenceLedgerService()

    def get_inspection_report(self, inspection_id: str) -> InspectionResultReport:
        """Fetch a persisted inspection and construct its report-ready representation."""
        trail = self.ledger_service.get_inspection(inspection_id)

        evidence = trail.evidence[0] if trail.evidence else None
        quality = evidence.quality_assessment if evidence else None

        initial_count = sum(
            1 for e in trail.rule_evaluations if e.evaluation_stage == "initial"
        )
        post_review_count = sum(
            1 for e in trail.rule_evaluations if e.evaluation_stage == "post_review"
        )
        has_human_review = len(trail.review_actions) > 0

        engine_ver = "DeterministicRuleEngine-v1.0"
        if trail.inspection.metadata and "rule_engine" in trail.inspection.metadata:
            engine_ver = str(trail.inspection.metadata["rule_engine"])

        traceability = TraceabilityInfo(
            rule_engine_version=engine_ver,
            statutory_source="The Legal Metrology (Packaged Commodities) Rules, 2011",
            evaluated_rule_count=len(trail.rule_evaluations),
            initial_rule_count=initial_count,
            post_review_rule_count=post_review_count,
            human_review_applied=has_human_review,
        )

        # 1. Observations Presentation
        if not trail.observations:
            observations_msg = EMPTY_OBSERVATIONS_MESSAGE
            formatted_observations: List[ObservationPresentation] = []
        else:
            observations_msg = f"{len(trail.observations)} observations recorded."
            formatted_observations = []
            recorded_fields = set()
            for obs in trail.observations:
                recorded_fields.add(obs.field_name)
                is_na = (
                    obs.status == "not_applicable"
                    or (obs.value and str(obs.value).strip().lower() in ("not_applicable", "not applicable"))
                )
                if is_na:
                    val_str = NOT_APPLICABLE_MESSAGE
                    conf_str = NOT_APPLICABLE_MESSAGE
                    sr_str = NOT_APPLICABLE_MESSAGE
                    status_str = NOT_APPLICABLE_MESSAGE
                else:
                    val_str = format_missing_value(obs.value)
                    conf_str = format_confidence(obs.confidence)
                    sr_str = format_source_region(obs.source_region)
                    if obs.status in ("not_found", "not_recorded", "missing", "unrecorded"):
                        status_str = NOT_RECORDED_MESSAGE
                    else:
                        status_str = format_missing_value(obs.status, fallback=NOT_RECORDED_MESSAGE)

                formatted_observations.append(
                    ObservationPresentation(
                        observation_id=obs.observation_id,
                        inspection_id=obs.inspection_id,
                        field_name=obs.field_name,
                        value=val_str,
                        confidence=conf_str,
                        status=status_str,
                        source_region=sr_str,
                        source_type=obs.source_type,
                        parent_observation_id=obs.parent_observation_id,
                        created_at=obs.created_at,
                    )
                )

            # Rule 2: If an expected declaration has no recorded observation:
            # Value: Not available in recorded evidence, Status: Not recorded
            # (only when observations are present, otherwise empty collection Rule 8 applies)
            for m_field in MANDATORY_DECLARATION_FIELDS:
                if m_field not in recorded_fields:
                    formatted_observations.append(
                        ObservationPresentation(
                            observation_id=f"unrec_{m_field}_{trail.inspection.inspection_id[:8]}",
                            inspection_id=trail.inspection.inspection_id,
                            field_name=m_field,
                            value=NOT_AVAILABLE_MESSAGE,
                            confidence=NOT_AVAILABLE_MESSAGE,
                            status=NOT_RECORDED_MESSAGE,
                            source_region=NOT_AVAILABLE_MESSAGE,
                            source_type="unrecorded",
                            parent_observation_id=None,
                            created_at=trail.inspection.created_at,
                        )
                    )

        # 2. Rule Evaluations Presentation
        if not trail.rule_evaluations:
            rule_eval_msg = EMPTY_RULE_EVALUATIONS_MESSAGE
            formatted_rules: List[RuleEvaluationPresentation] = []
        else:
            rule_eval_msg = f"{len(trail.rule_evaluations)} rule evaluations recorded."
            formatted_rules = []
            for r in trail.rule_evaluations:
                formatted_rules.append(
                    RuleEvaluationPresentation(
                        evaluation_id=r.evaluation_id,
                        inspection_id=r.inspection_id,
                        rule_id=r.rule_id,
                        rule_version=r.rule_version,
                        rule_name=r.rule_name,
                        statutory_reference=format_missing_value(r.statutory_reference),
                        status=r.status,  # Canonical status strictly unchanged
                        observed_value=format_missing_value(r.observed_value),
                        expected_requirement=format_missing_value(r.expected_requirement),
                        explanation=format_missing_value(r.explanation),
                        source_region=format_source_region(r.source_region),
                        evidence_reference=r.evidence_reference,
                        evaluation_stage=r.evaluation_stage,
                        created_at=r.created_at,
                    )
                )

        # 3. Review Actions Presentation
        if not trail.review_actions:
            review_act_msg = EMPTY_REVIEW_ACTIONS_MESSAGE
            formatted_reviews: List[ReviewActionPresentation] = []
        else:
            review_act_msg = f"{len(trail.review_actions)} human review actions recorded."
            formatted_reviews = []
            for ra in trail.review_actions:
                action_str = ra.action.value if hasattr(ra.action, "value") else str(ra.action)
                formatted_reviews.append(
                    ReviewActionPresentation(
                        review_id=ra.review_id,
                        inspection_id=ra.inspection_id,
                        field_name=ra.field_name,
                        action=action_str,
                        original_value=format_missing_value(ra.original_value),
                        reviewed_value=format_missing_value(ra.reviewed_value),
                        original_confidence=format_confidence(ra.original_confidence),
                        source_region_before=format_source_region(ra.source_region_before),
                        source_region_after=format_source_region(ra.source_region_after),
                        reviewer_notes=format_missing_value(
                            ra.reviewer_notes, fallback="No reviewer notes recorded."
                        ),
                        created_at=ra.created_at,
                    )
                )

        # 4. Evidence & Quality Messages
        evidence_msg = (
            "Evidence record available." if evidence else EMPTY_EVIDENCE_MESSAGE
        )
        quality_msg = (
            format_quality_summary(quality) if quality else NOT_AVAILABLE_MESSAGE
        )

        # 5. Package ID and Summary scalar formatting
        package_id_str = format_missing_value(trail.inspection.package_id)
        summary_str = format_missing_value(trail.inspection.summary)

        return InspectionResultReport(
            inspection_id=trail.inspection.inspection_id,
            created_at=trail.inspection.created_at,
            package_id=package_id_str,
            overall_disposition=trail.inspection.overall_disposition,
            summary=summary_str,
            evidence=evidence,
            quality=quality,
            observations=formatted_observations,
            rule_evaluations=formatted_rules,
            review_actions=formatted_reviews,
            traceability=traceability,
            decision_trail_summary=trail.decision_trail_summary,
            evidence_message=evidence_msg,
            observations_message=observations_msg,
            rule_evaluations_message=rule_eval_msg,
            review_actions_message=review_act_msg,
            quality_assessment_message=quality_msg,
        )
