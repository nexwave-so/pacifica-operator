"""
Mean Reversion Short Hedge Strategy
"""
import datetime
from typing import Any, Dict, List, Optional

from nexwave.common.logger import logger
from nexwave.db.queries import get_candles
from nexwave.db.session import AsyncSessionLocal
from nexwave.strategies.base_strategy import BaseStrategy, SignalType, TradingSignal


class MRShortHedgeStrategy(BaseStrategy):
    """
    Mean Reversion Short Hedge Strategy:

    - Purpose: Hedge momentum longs when they're winning big
    - Entry: Overbought conditions (e.g., high RSI)
    - Exit: Max hold time < 24 hours
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
        self.lookback_period = 14
        self.rsi_threshold = 70  # RSI overbought threshold
        self.max_hold_duration = datetime.timedelta(hours=24)
        self.timeframe = "1h"

        logger.info(f"Initialized MRShortHedgeStrategy for {self.symbol}")

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

    def _calculate_rsi(self, candles: List[Dict[str, Any]]) -> float:
        if len(candles) < self.lookback_period:
            return 50.0

        prices = [c["close"] for c in candles]
        gains = []
        losses = []

        for i in range(1, len(prices)):
            delta = prices[i] - prices[i-1]
            if delta > 0:
                gains.append(delta)
            else:
                losses.append(abs(delta))

        avg_gain = sum(gains) / self.lookback_period if gains else 0
        avg_loss = sum(losses) / self.lookback_period if losses else 0
        
        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

    async def generate_signal(
        self, market_data: Dict[str, Any], current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal for mean reversion short hedge."""
        current_price = market_data.get("price")
        if not current_price:
            logger.warning(f"No price for {self.symbol}")
            return None

        candles = await self.get_candles()
        if len(candles) < self.lookback_period:
            logger.warning(f"Not enough candle data for {self.symbol}")
            return None

        rsi = self._calculate_rsi(candles)
        
        has_short = current_position and current_position.get("side") == "SHORT"

        # Exit
        if has_short:
            entry_time = current_position.get("timestamp") # Assuming timestamp is stored in position
            if entry_time and (datetime.datetime.now() - entry_time) > self.max_hold_duration:
                return TradingSignal(signal_type=SignalType.CLOSE_SHORT, symbol=self.symbol, price=current_price, amount=current_position.get("amount", 0.0))

        # Entry
        if not has_short and rsi > self.rsi_threshold:
            position_size = (self.portfolio_value * 0.01) / current_price  # 1% of portfolio
            return TradingSignal(
                signal_type=SignalType.SELL,
                symbol=self.symbol,
                price=current_price,
                amount=position_size,
            )

        return None
