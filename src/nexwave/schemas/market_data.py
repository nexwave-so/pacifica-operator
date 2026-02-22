"""Market data schemas"""

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class TickData(BaseModel):
    """Tick data point"""

    time: datetime
    price: float
    volume: float
    bid: Optional[float] = None
    ask: Optional[float] = None


class TickResponse(BaseModel):
    """Tick data response"""

    symbol: str
    data: list[TickData]
    count: int


class CandleData(BaseModel):
    """OHLCV candle data"""

    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    vwap: Optional[float] = None


class CandleResponse(BaseModel):
    """Candle data response"""

    symbol: str
    timeframe: str
    data: list[CandleData]


class LatestPrice(BaseModel):
    """Latest price for a symbol"""

    price: float
    time: datetime
    change_24h_pct: Optional[float] = None


class LatestPricesResponse(BaseModel):
    """Latest prices response"""

    BTC: Optional[LatestPrice] = None
    ETH: Optional[LatestPrice] = None
    SOL: Optional[LatestPrice] = None

