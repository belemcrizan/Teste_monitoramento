"""Quatro motores de detecção independentes."""

from .churning import ChurningDetector
from .concentration import ConcentrationDetector
from .manipulation import ManipulationBehaviorDetector
from .otc import OtcComplexDetector

__all__ = [
    "ChurningDetector",
    "ConcentrationDetector",
    "ManipulationBehaviorDetector",
    "OtcComplexDetector",
]

