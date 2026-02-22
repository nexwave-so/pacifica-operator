"""
Position Sizer
"""
from typing import Any, Dict

from nexwave.common.logger import logger


class PositionSizer:
    """
    Calculates position sizes based on a set of rules.
    """

    def __init__(self, account_balance: float, max_positions_per_model: int = 20, max_models: int = 20):
        self.account_balance = account_balance
        self.max_positions_per_model = max_positions_per_model
        self.max_models = max_models

    def calculate_position_size(
        self, risk_per_trade: float = 0.02, stop_loss_pct: float = 0.02
    ) -> float:
        """
        Calculates the position size.

        Args:
            risk_per_trade: The percentage of the account to risk per trade.
            stop_loss_pct: The percentage of the entry price to set the stop loss.

        Returns:
            The position size in the base currency.
        """
        if stop_loss_pct <= 0:
            logger.warning("Stop loss percentage must be greater than 0.")
            return 0.0

        # Position size: 0.5-3% of account per position
        # This is a simplified calculation. A more advanced implementation would consider volatility.
        position_size_pct = max(0.005, min(risk_per_trade, 0.03))
        
        position_size = (self.account_balance * position_size_pct) / stop_loss_pct
        return position_size

    def get_max_positions(self) -> int:
        """
        Returns the maximum number of positions allowed.
        """
        return self.max_positions_per_model * self.max_models
