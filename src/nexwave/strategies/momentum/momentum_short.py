"""
Momentum Short Strategy
"""
import statistics
from typing import Any, Dict, List, Optional

from nexwave.common.logger import logger
from nexwave.db.queries import get_candles
from nexwave.db.session import AsyncSessionLocal
from nexwave.strategies.base_strategy import BaseStrategy, SignalType, TradingSignal


class MomentumShortStrategy(BaseStrategy):
    """
    Momentum Short Strategy:

    - For bear market exposure
    - Target: ~20% annual return, 20-30% max drawdown
    - Entry: Sustained downtrend
    - Exit: Trend reversal or take-profit/stop-loss
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
        self.lookback_period = 14 # 14 days
        self.trend_confirmation_period = 4 # 4 consecutive lower highs/lows
        self.timeframe = "1d"
        self.stop_loss_atr_multiplier = 2.0
        self.take_profit_atr_multiplier = 5.0

        logger.info(f"Initialized MomentumShortStrategy for {self.symbol}")

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

    def _is_sustained_downtrend(self, candles: List[Dict[str, Any]]) -> bool:
        """Check for N consecutive lower highs and lower lows."""
        if len(candles) < self.trend_confirmation_period:
            return False

        for i in range(len(candles) - self.trend_confirmation_period, len(candles)):
            if candles[i]['high'] >= candles[i-1]['high'] or candles[i]['low'] >= candles[i-1]['low']:
                return False
        return True

    def _calculate_atr(self, candles: List[Dict[str, Any]]) -> float:
        if not candles:
            return 0
        
        true_ranges = []
        for i in range(1, len(candles)):
            tr = max(
                candles[i]["high"] - candles[i]["low"],
                abs(candles[i]["high"] - candles[i-1]["close"]),
                abs(candles[i]["low"] - candles[i-1]["close"]),
            )
            true_ranges.append(tr)
        
        return statistics.mean(true_ranges) if true_ranges else 0

    async def generate_signal(
        self, market_data: Dict[str, Any], current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal for shorting in bearish trends."""
        current_price = market_data.get("price")
        if not current_price:
            logger.warning(f"No price for {self.symbol}")
            return None

        candles = await self.get_candles()
        if len(candles) < self.lookback_period:
            logger.warning(f"Not enough candle data for {self.symbol}")
            return None

        has_short = current_position and current_position.get("side") == "SHORT"
        
        downtrend = self._is_sustained_downtrend(candles[-self.lookback_period:])
        atr = self._calculate_atr(candles[-self.lookback_period:])

        # Exit Logic
        if has_short and not downtrend:
            return TradingSignal(signal_type=SignalType.CLOSE_SHORT, symbol=self.symbol, price=current_price, amount=current_position.get("amount", 0.0))

        # Entry Logic
        if not has_short:
            if downtrend:
                position_size = (self.portfolio_value * 0.015) / current_price # 1.5% of portfolio
                stop_loss = current_price + (atr * self.stop_loss_atr_multiplier)
                take_profit = current_price - (atr * self.take_profit_atr_multiplier)
                return TradingSignal(
                    signal_type=SignalType.SELL,
                    symbol=self.symbol,
                    price=current_price,
                    amount=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )

        return None
