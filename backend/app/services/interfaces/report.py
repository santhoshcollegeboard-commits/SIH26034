from abc import ABC, abstractmethod
from typing import Any, Dict


class ReportGenerator(ABC):
    """Abstract interface for generating Legal Metrology compliance inspection reports."""

    @abstractmethod
    async def generate_report(self, evidence_data: Dict[str, Any], format: str = "pdf") -> bytes:
        """Generate a formalized compliance inspection report certificate in requested format."""
        pass
