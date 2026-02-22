"""
Hedge Trigger System
"""
from enum import Enum
from typing import Any, Dict

from nexwave.common.logger import logger


class HedgeAction(Enum):
    ACTIVATE_MR_SHORTS = "ACTIVATE_MR_SHORTS"
    ACTIVATE_MR_LONGS = "ACTIVATE_MR_LONGS"
    NONE = "NONE"


class HedgeTrigger:
    """
    Automatically activate hedges based on exposure.
    """

    def __init__(self, profit_threshold: float = 0.1, high_exposure_threshold: float = 0.7, short_threshold: float = 0.3):
        self.profit_threshold = profit_threshold
        self.high_exposure_threshold = high_exposure_threshold
        self.short_threshold = short_threshold

    def evaluate(self, exposure_state: Dict[str, Any]) -> HedgeAction:
        """
        Evaluate the exposure state and return a hedge action.
        """
        long_pnl_pct = exposure_state.get("long_pnl_pct", 0.0)
        net_long = exposure_state.get("net_long", 0.0)
        short_exposure = exposure_state.get("short_exposure", 0.0)

        # When momentum longs winning big -> activate MR shorts
        if long_pnl_pct > self.profit_threshold and net_long > self.high_exposure_threshold:
            logger.info("Hedge Trigger: High long P&L and exposure. Activating MR shorts.")
            return HedgeAction.ACTIVATE_MR_SHORTS

        # When momentum shorts open -> activate MR longs
        if short_exposure > self.short_threshold:
            logger.info("Hedge Trigger: High short exposure. Activating MR longs.")
            return HedgeAction.ACTIVATE_MR_LONGS

        return HedgeAction.NONE

    def add_circuit_breakers(self, hedge_action: HedgeAction) -> HedgeAction:
        """
        Add circuit breakers for runaway hedging.
        
        This is a placeholder for a more complex implementation.
        """
        # Example circuit breaker: prevent activating more hedges if too many are already active.
        # This would require tracking active hedges.
        
        logger.info(f"Circuit breaker checked for action: {hedge_action.value}")
        return hedge_action
