from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class EvidenceRepository(ABC):
    """Abstract interface for managing auditable compliance evidence packages.
    
    Persists original package imagery, bounding box crops, rule evaluations,
    and human reviewer annotations for audit trails.
    """

    @abstractmethod
    async def save_evidence(self, session_id: str, evidence_data: Dict[str, Any]) -> str:
        """Store an evidence record and return an auditable record ID."""
        pass

    @abstractmethod
    async def get_evidence(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve an evidence record by session or record ID."""
        pass
