"""Catálogo modular de detectores independentes e explicáveis."""

from .churning import ChurningDetector
from .concentration import ConcentrationDetector
from .fixed_income import FixedIncomeMarketConductDetector
from .manipulation import ManipulationBehaviorDetector
from .observed_participation import ObservedParticipationDetector
from .otc import OtcComplexDetector
from .post_trade_response import PostTradeMarketResponseDetector
from .principal_customer import PrincipalCustomerConductDetector

__all__ = [
    "ChurningDetector",
    "ConcentrationDetector",
    "FixedIncomeMarketConductDetector",
    "ManipulationBehaviorDetector",
    "ObservedParticipationDetector",
    "OtcComplexDetector",
    "PostTradeMarketResponseDetector",
    "PrincipalCustomerConductDetector",
]
