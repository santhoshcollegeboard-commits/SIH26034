from abc import ABC, abstractmethod
from typing import Any, Dict, List


class RuleEngine(ABC):
    """Abstract interface for deterministic Legal Metrology compliance checks.
    
    Architecture principle:
    Deterministic Rules decide. Evaluates extracted proposals against
    statutory rules (Legal Metrology Packaged Commodities Rules).
    """

    @abstractmethod
    async def evaluate_compliance(
        self, package_metadata: Dict[str, Any], extracted_declarations: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate extracted declarations against deterministic compliance rules."""
        pass
