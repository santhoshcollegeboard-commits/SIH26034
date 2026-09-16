"""Deterministic statutory compliance rules package for PackCheck.

Evaluates extracted packaging declarations against the Legal Metrology
(Packaged Commodities) Rules, 2011.
"""

from typing import Any, Dict, List, Optional

from backend.app.schemas.compliance import RuleEvaluation
from backend.app.schemas.extraction import ExtractionResult
from rules.rule_6_declarations import (
    RULE_VERSION as RULE_6_VERSION,
    STATUTORY_SOURCE as RULE_6_SOURCE,
    aggregate_disposition,
    evaluate_rule_6,
)
from rules.rule_7_pdp import (
    RULE_VERSION as RULE_7_VERSION,
    STATUTORY_SOURCE as RULE_7_SOURCE,
    evaluate_rule_7,
)
from rules.rule_8_placement import (
    RULE_VERSION as RULE_8_VERSION,
    STATUTORY_SOURCE as RULE_8_SOURCE,
    evaluate_rule_8,
)
from rules.rule_9_manner import (
    RULE_VERSION as RULE_9_VERSION,
    STATUTORY_SOURCE as RULE_9_SOURCE,
    evaluate_rule_9,
)


def evaluate_all_rules(
    extraction: ExtractionResult,
    package_metadata: Optional[Dict[str, Any]] = None,
    include_unassessable: bool = False,
) -> List[RuleEvaluation]:
    """Evaluate all implemented Legal Metrology statutory rules (Rules 6, 7, 8, and 9)."""
    meta = package_metadata or {}
    evaluations: List[RuleEvaluation] = []
    evaluations.extend(evaluate_rule_6(extraction, meta, include_unassessable))
    evaluations.extend(evaluate_rule_7(extraction, meta))
    evaluations.extend(evaluate_rule_8(extraction, meta))
    evaluations.extend(evaluate_rule_9(extraction, meta))
    return evaluations


__all__ = [
    "RULE_6_VERSION",
    "RULE_6_SOURCE",
    "RULE_7_VERSION",
    "RULE_7_SOURCE",
    "RULE_8_VERSION",
    "RULE_8_SOURCE",
    "RULE_9_VERSION",
    "RULE_9_SOURCE",
    "aggregate_disposition",
    "evaluate_rule_6",
    "evaluate_rule_7",
    "evaluate_rule_8",
    "evaluate_rule_9",
    "evaluate_all_rules",
]
