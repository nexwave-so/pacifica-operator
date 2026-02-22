"""
Short-Term Momentum Strategy – dominant scalper (5m default).
Reads timeframe, ATR multiples, lookback, and volume from config for OpenClaw Agent tuning.
"""
import statistics
from typing import Any, Dict, List, Optional

from nexwave.common.config import settings
from nexwave.common.logger import logger
from nexwave.db.queries import get_candles
from nexwave.db.session import AsyncSessionLocal
from nexwave.strategies.base_strategy import BaseStrategy, SignalType, TradingSignal


class ShortTermMomentumStrategy(BaseStrategy):
    """
    Short-Term Momentum Strategy (dominant scalper; vwm_timeframe=5m default):

    - Timeframe / ATR / lookback / volume from config (vwm_*, trade_cooldown).
    - Entry: Breakout + volume confirmation.
    - Exit: Momentum reversal or take-profit/stop-loss (ATR-based).
    """

    def __init__(
        self,
        strategy_id: str,
        symbol: str,
        portfolio_value: float = 100000.0,
        paper_trading: bool = True,
    ):
        super().__init__(strategy_id, symbol, portfolio_value, paper_trading)
        self.lookback_period = getattr(settings, "vwm_lookback_period", 12)
        self.volume_lookback = min(10, self.lookback_period)
        self.breakout_threshold = getattr(settings, "vwm_breakout_threshold", 1.015)  # 1.5% default (was 5%)
        self.volume_multiplier = getattr(settings, "vwm_volume_multiplier", 2.0)
        self.timeframe = getattr(settings, "vwm_timeframe", "5m")
        self.stop_loss_atr_multiplier = getattr(settings, "vwm_stop_loss_atr_multiplier", 1.5)
        self.take_profit_atr_multiplier = getattr(settings, "vwm_take_profit_atr_multiplier", 2.5)
        self.base_position_pct = getattr(settings, "vwm_base_position_pct", 1.0)

        logger.info(
            f"Initialized ShortTermMomentumStrategy for {self.symbol} "
            f"(tf={self.timeframe} SL={self.stop_loss_atr_multiplier}x ATR TP={self.take_profit_atr_multiplier}x ATR)"
        )

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
                logger.info(f"Fetched {len(candles)} candles for {self.symbol} (tf={self.timeframe}, limit={limit or (self.lookback_period + 10)}, lookback={self.lookback_period})")
                return list(reversed(candles))
        except Exception as e:
            logger.error(f"Error fetching candles for {self.symbol}: {e}")
            return []

    def _calculate_metrics(self, candles: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate momentum and related metrics."""
        if len(candles) < self.lookback_period:
            return {}

        window = candles[-self.lookback_period :]
        volumes = [c["volume"] for c in window]
        avg_volume = statistics.mean(volumes[-self.volume_lookback :])
        current_volume = window[-1]["volume"]
        
        highest_high = max(c["high"] for c in window)
        lowest_low = min(c["low"] for c in window)

        true_ranges = []
        for i in range(1, len(window)):
            tr = max(
                window[i]["high"] - window[i]["low"],
                abs(window[i]["high"] - window[i-1]["close"]),
                abs(window[i]["low"] - window[i-1]["close"]),
            )
            true_ranges.append(tr)
        
        atr = statistics.mean(true_ranges) if true_ranges else 0

        return {
            "avg_volume": avg_volume,
            "current_volume": current_volume,
            "highest_high": highest_high,
            "lowest_low": lowest_low,
            "atr": atr
        }

    async def generate_signal(
        self, market_data: Dict[str, Any], current_position: Optional[Dict[str, Any]] = None
    ) -> Optional[TradingSignal]:
        """Generate trading signal based on short-term momentum logic."""
        current_price = market_data.get("price")
        if not current_price:
            logger.warning(f"No price for {self.symbol}")
            return None

        candles = await self.get_candles()
        if len(candles) < self.lookback_period:
            logger.warning(f"Not enough candle data for {self.symbol}")
            return None

        metrics = self._calculate_metrics(candles)
        if not metrics:
            return None
        
        avg_volume = metrics["avg_volume"]
        current_volume = metrics["current_volume"]
        highest_high = metrics["highest_high"]
        lowest_low = metrics["lowest_low"]
        atr = metrics["atr"]

        has_long = current_position and current_position.get("side") == "LONG"
        has_short = current_position and current_position.get("side") == "SHORT"
        
        # Exit Logic
        if has_long and current_price < lowest_low:
             return TradingSignal(signal_type=SignalType.CLOSE_LONG, symbol=self.symbol, price=current_price, amount=current_position.get("amount", 0.0))
        if has_short and current_price > highest_high:
            return TradingSignal(signal_type=SignalType.CLOSE_SHORT, symbol=self.symbol, price=current_price, amount=current_position.get("amount", 0.0))

        # Entry Logic
        if not has_long and not has_short:
            # Long entry
            if current_price > highest_high * self.breakout_threshold and current_volume > avg_volume * self.volume_multiplier:
                position_size = (self.portfolio_value * (self.base_position_pct / 100.0)) / current_price
                stop_loss = current_price - (atr * self.stop_loss_atr_multiplier)
                take_profit = current_price + (atr * self.take_profit_atr_multiplier)
                return TradingSignal(
                    signal_type=SignalType.BUY,
                    symbol=self.symbol,
                    price=current_price,
                    amount=position_size,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                )
            
            # Short entry (breakdown)
            if current_price < lowest_low / self.breakout_threshold and current_volume > avg_volume * self.volume_multiplier:
                position_size = (self.portfolio_value * (self.base_position_pct / 100.0)) / current_price
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
