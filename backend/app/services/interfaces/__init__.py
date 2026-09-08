from backend.app.services.interfaces.ocr import (
    OCRProvider,
    CloudOCRProvider,
    LocalOCRProvider,
)
from backend.app.services.interfaces.quality import ImageQualityChecker
from backend.app.services.interfaces.rule_engine import RuleEngine
from backend.app.services.interfaces.evidence import EvidenceRepository
from backend.app.services.interfaces.report import ReportGenerator

__all__ = [
    "OCRProvider",
    "CloudOCRProvider",
    "LocalOCRProvider",
    "ImageQualityChecker",
    "RuleEngine",
    "EvidenceRepository",
    "ReportGenerator",
]
