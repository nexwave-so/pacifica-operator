"""Helper functions for querying candle data from continuous aggregates"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from nexwave.common.logger import logger


# Timeframe to view mapping
TIMEFRAME_VIEWS = {
    "1m": "candles_1m_ohlcv",
    "5m": "candles_5m_ohlcv",
    "15m": "candles_15m_ohlcv",
    "1h": "candles_1h_ohlcv",
    "4h": "candles_4h_ohlcv",
    "1d": "candles_1d_ohlcv",
}

# Timeframe to interval mapping for time_bucket
TIMEFRAME_INTERVALS = {
    "1m": "1 minute",
    "5m": "5 minutes",
    "15m": "15 minutes",
    "1h": "1 hour",
    "4h": "4 hours",
    "1d": "1 day",
}


async def get_candles(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    limit: int = 1000,
) -> List[Dict[str, Any]]:
    """Get OHLCV candles from continuous aggregates"""

    if timeframe not in TIMEFRAME_VIEWS:
        raise ValueError(
            f"Invalid timeframe: {timeframe}. Must be one of: {list(TIMEFRAME_VIEWS.keys())}"
        )

    view_name = TIMEFRAME_VIEWS[timeframe]

    query = f"""
        SELECT
            time,
            symbol,
            open,
            high,
            low,
            close,
            volume
        FROM {view_name}
        WHERE symbol = :symbol
    """

    # Try exact match first (for symbols like kBONK, kPEPE), then uppercase
    params: Dict[str, Any] = {"symbol": symbol}

    if start_time:
        query += " AND time >= :start_time"
        params["start_time"] = start_time

    if end_time:
        query += " AND time <= :end_time"
        params["end_time"] = end_time

    query += " ORDER BY time DESC LIMIT :limit"
    params["limit"] = limit

    try:
        result = await session.execute(text(query), params)
        rows = result.fetchall()

        # If no results with exact match, try uppercase (for other symbols)
        if not rows:
            params_upper = params.copy()
            params_upper["symbol"] = symbol.upper()
            result = await session.execute(text(query), params_upper)
            rows = result.fetchall()

        candles = []
        for row in rows:
            candles.append(
                {
                    "time": row[0],
                    "symbol": row[1],
                    "open": float(row[2]) if row[2] else None,
                    "high": float(row[3]) if row[3] else None,
                    "low": float(row[4]) if row[4] else None,
                    "close": float(row[5]) if row[5] else None,
                    "volume": float(row[6]) if row[6] else None,
                }
            )

        return candles

    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise


async def get_latest_candle(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
) -> Optional[Dict[str, Any]]:
    """Get the latest candle for a symbol"""

    candles = await get_candles(session, symbol, timeframe, limit=1)

    if candles:
        return candles[0]

    return None


async def get_candles_count(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> int:
    """Get count of candles for a symbol in time range"""

    if timeframe not in TIMEFRAME_VIEWS:
        return 0

    view_name = TIMEFRAME_VIEWS[timeframe]

    query = f"""
        SELECT COUNT(*)
        FROM {view_name}
        WHERE symbol = :symbol
    """

    # Try exact match first (for symbols like kBONK, kPEPE), then uppercase
    params: Dict[str, Any] = {"symbol": symbol}

    if start_time:
        query += " AND time >= :start_time"
        params["start_time"] = start_time

    if end_time:
        query += " AND time <= :end_time"
        params["end_time"] = end_time

    try:
        result = await session.execute(text(query), params)
        count = result.scalar()

        # If no results with exact match, try uppercase (for other symbols)
        if not count:
            params_upper = params.copy()
            params_upper["symbol"] = symbol.upper()
            result = await session.execute(text(query), params_upper)
            count = result.scalar()

        return count or 0

    except Exception as e:
        logger.error(f"Error counting candles: {e}")
        return 0


async def get_price_statistics(
    session: AsyncSession,
    symbol: str,
    timeframe: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Get price statistics (min, max, avg, first, last) for a symbol"""

    if timeframe not in TIMEFRAME_VIEWS:
        raise ValueError(f"Invalid timeframe: {timeframe}")

    view_name = TIMEFRAME_VIEWS[timeframe]

    query = f"""
        SELECT 
            MIN(low) AS min_price,
            MAX(high) AS max_price,
            AVG((high + low + close) / 3.0) AS avg_price,
            (SELECT close FROM {view_name} WHERE symbol = :symbol ORDER BY time ASC LIMIT 1) AS first_price,
            (SELECT close FROM {view_name} WHERE symbol = :symbol ORDER BY time DESC LIMIT 1) AS last_price,
            SUM(volume) AS total_volume
        FROM {view_name}
        WHERE symbol = :symbol
    """

    # Try exact match first (for symbols like kBONK, kPEPE), then uppercase
    params: Dict[str, Any] = {"symbol": symbol}

    if start_time:
        query += " AND time >= :start_time"
        params["start_time"] = start_time

    if end_time:
        query += " AND time <= :end_time"
        params["end_time"] = end_time

    try:
        result = await session.execute(text(query), params)
        row = result.first()

        # If no results with exact match, try uppercase (for other symbols)
        if not row:
            params_upper = params.copy()
            params_upper["symbol"] = symbol.upper()
            result = await session.execute(text(query), params_upper)
            row = result.first()

        if row:
            return {
                "min_price": float(row[0]) if row[0] else None,
                "max_price": float(row[1]) if row[1] else None,
                "avg_price": float(row[2]) if row[2] else None,
                "first_price": float(row[3]) if row[3] else None,
                "last_price": float(row[4]) if row[4] else None,
                "total_volume": float(row[5]) if row[5] else None,
                "price_change": (
                    (float(row[4]) - float(row[3])) / float(row[3]) * 100
                    if row[3] and row[4] and row[3] != 0
                    else None
                ),
            }

        return {}

    except Exception as e:
        logger.error(f"Error getting price statistics: {e}")
        return {}

