"""
Portfolio Exposure Manager
"""
from typing import Dict, Any

from nexwave.common.logger import logger

# TODO: Move to config.py
HIGH_LONG_EXPOSURE_THRESHOLD = 0.7 
SHORT_EXPOSURE_THRESHOLD = -0.3

class ExposureManager:
    """
    Tracks and manages portfolio exposure across all strategies.
    """

    def __init__(self, portfolio_value: float):
        self.portfolio_value = portfolio_value
        self.positions: Dict[str, Any] = {}
        self.net_exposure = 0.0
        self.long_exposure = 0.0
        self.short_exposure = 0.0
        self.net_long = 0.0
        self.long_pnl_pct = 0.0
        

    def update_position(self, symbol: str, side: str, size: float, entry_price: float):
        """
        Update or add a new position.
        """
        position_value = size * entry_price
        self.positions[symbol] = {
            "side": side,
            "size": size,
            "entry_price": entry_price,
            "value": position_value,
        }
        self.calculate_exposure()
        self.check_thresholds()

    def remove_position(self, symbol: str):
        """
        Remove a closed position.
        """
        if symbol in self.positions:
            del self.positions[symbol]
            self.calculate_exposure()

    def calculate_exposure(self):
        """
        Calculate net, long, and short exposure.
        """
        self.long_exposure = 0.0
        self.short_exposure = 0.0

        for position in self.positions.values():
            if position["side"] == "LONG":
                self.long_exposure += position["value"]
            else:
                self.short_exposure += position["value"]

        total_exposure = self.long_exposure + self.short_exposure
        self.net_exposure = self.long_exposure - self.short_exposure
        
        if self.portfolio_value > 0:
            self.net_long = self.net_exposure / self.portfolio_value
            

    def check_thresholds(self):
        """
        Emit events when exposure thresholds are crossed.
        """
        if self.net_long > HIGH_LONG_EXPOSURE_THRESHOLD:
            logger.info(f"High long exposure detected: {self.net_long:.2f}")
            # In a real implementation, this would emit an event
            # to a hedge trigger service.

        if self.net_exposure < SHORT_EXPOSURE_THRESHOLD * self.portfolio_value:
            logger.info(f"Short exposure threshold crossed: {self.net_exposure:.2f}")
            # Emit event to hedge trigger service.
            
    def get_exposure_state(self) -> Dict[str, float]:
        """
        Returns the current exposure state of the portfolio.
        """
        return {
            "net_exposure": self.net_exposure,
            "long_exposure": self.long_exposure,
            "short_exposure": self.short_exposure,
            "net_long": self.net_long,
            "long_pnl_pct": self.long_pnl_pct,
        }
