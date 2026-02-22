"""
Mean Reversion Long Hedge Strategy
"""
from typing import Any, Dict, List, Optional

from nexwave.common.logger import logger
from nexwave.db.queries import get_candles
from nexwave.db.session import AsyncSessionLocal
from nexwave.strategies.base_strategy import BaseStrategy, SignalType, TradingSignal


class MRLongHedgeStrategy(BaseStrategy):
    """
    Mean Reversion Long Hedge Strategy:

    - Purpose: Hedge momentum shorts
    - Exploits crypto's natural long bias (dips get bought)
    - No hard stop-losses
    """

    def __init__(
        self,
        strategy_id: str,
        symbol: str,
        portfolio_value: float = 100000.0,
        paper_trading: bool = True,
    ):
        super().__init__(strategy_id, symbol, portfolio_value, paper_trading)
        # TODO: Move these to config.py with `hmo_` prefix
        self.lookback_period = 20
        self.dip_threshold = 0.95  # 5% dip from the recent high
        self.take_profit_pct = 1.05  # 5% take profit
        self.timeframe = "1h"

        logger.info(f"Initialized MRLongHedgeStrategy for {self.symbol}")

    async def get_candles(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get recent candles for analysis"""
        try:
            async with AsyncSessionLocal() as session:
                candles = await get_candles(
                    session=session,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    limit=limit or (self.lookback_period + 10),
                )
                return list(reversed(candles))
        except Exception as e:
            logger.error(f"Error fetching candles for {self.symbol}: {e}")
            return []

    async def generate_signal(
        self, market_data: Dict[str, Any], current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal for mean reversion long hedge."""
        current_price = market_data.get("price")
        if not current_price:
            logger.warning(f"No price for {self.symbol}")
            return None

        candles = await self.get_candles()
        if len(candles) < self.lookback_period:
            logger.warning(f"Not enough candle data for {self.symbol}")
            return None

        highest_high = max(c["high"] for c in candles[-self.lookback_period :])
        
        has_long = current_position and current_position.get("side") == "LONG"

        # Exit
        if has_long and current_price >= current_position["entry_price"] * self.take_profit_pct:
            return TradingSignal(signal_type=SignalType.CLOSE_LONG, symbol=self.symbol, price=current_price, amount=current_position.get("amount", 0.0))

        # Entry
        if not has_long and current_price < highest_high * self.dip_threshold:
            position_size = (self.portfolio_value * 0.01) / current_price  # 1% of portfolio
            return TradingSignal(
                signal_type=SignalType.BUY,
                symbol=self.symbol,
                price=current_price,
                amount=position_size,
            )

        return None
