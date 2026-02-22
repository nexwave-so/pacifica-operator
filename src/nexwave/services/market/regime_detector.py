"""
Market Regime Detector
"""
from enum import Enum
import statistics
from typing import Any, Dict, List

from nexwave.common.logger import logger
from nexwave.db.queries import get_candles
from nexwave.db.session import AsyncSessionLocal


class MarketRegime(Enum):
    BULL = "BULL"
    BEAR = "BEAR"
    SIDEWAYS = "SIDEWAYS"


class RegimeDetector:
    """
    Classify market conditions to adjust strategy weights.
    """

    def __init__(self, symbol: str, timeframe: str = "1d"):
        self.symbol = symbol
        self.timeframe = timeframe

    async def get_candles(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent candles for analysis"""
        try:
            async with AsyncSessionLocal() as session:
                candles = await get_candles(
                    session=session,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    limit=limit,
                )
                return list(reversed(candles))
        except Exception as e:
            logger.error(f"Error fetching candles for {self.symbol}: {e}")
            return []

    async def detect_regime(self) -> MarketRegime:
        """
        Detect the current market regime.

        This is a simplified implementation using a moving average crossover.
        """
        candles = await self.get_candles()
        if len(candles) < 50:
            logger.warning("Not enough candle data to detect regime.")
            return MarketRegime.SIDEWAYS

        closes = [c["close"] for c in candles]
        
        # 20-period and 50-period moving averages
        ma_20 = statistics.mean(closes[-20:])
        ma_50 = statistics.mean(closes[-50:])

        if ma_20 > ma_50:
            return MarketRegime.BULL
        elif ma_20 < ma_50:
            return MarketRegime.BEAR
        else:
            return MarketRegime.SIDEWAYS
