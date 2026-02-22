"""FastAPI application for API Gateway"""

import json
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Depends, HTTPException, status, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from nexwave.common.config import settings, STRATEGY_CONFIG_KEYS
from nexwave.common.logger import logger, setup_logging
from nexwave.common.redis_client import redis_client
from nexwave.db.session import get_db, AsyncSessionLocal
from nexwave.db.models import Tick, Order, Position
from nexwave.db.queries import get_candles as query_candles
from nexwave.schemas.market_data import TickResponse, TickData, CandleResponse, CandleData, LatestPricesResponse, LatestPrice
from nexwave.schemas.trading import CreateOrderRequest, OrderResponse, PositionsResponse, Position as PositionSchema
from nexwave.common.pairs import get_all_pairs, get_active_pairs, get_pair_by_symbol, validate_symbol
from nexwave.services.api_gateway.x402_middleware import X402Middleware

# Setup logging
setup_logging(level=settings.log_level)

app = FastAPI(
    title="Nexwave API",
    description="Autonomous Trading Agent API for Pacifica Perpetual DEX - Operated by Nexwave and an OpenClaw Agent",
    version="0.2.0",
)

# CORS middleware (must be added before x402 middleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-PAYMENT-RESPONSE", "X-PAYMENT-REQUIRED"],  # Expose x402 headers
)

# x402 Payment Middleware - Protect premium endpoints
X402_TREASURY_ADDRESS = os.getenv("X402_TREASURY_ADDRESS", "HVXrj9PFN5sLqkvWhs5quGsQHKsbaeb75sroPtTiCUWU")
X402_ENABLED = os.getenv("X402_ENABLED", "true").lower() == "true"

if X402_ENABLED:
    logger.info("x402 payments ENABLED - protecting premium endpoints")
    app.add_middleware(
        X402Middleware,
        treasury_address=X402_TREASURY_ADDRESS,
        protected_routes={
            "/api/v1/latest-prices": {
                "price_usd": "0.001",  # $0.001 USDC per request
                "description": "Real-time market prices for all 30 trading pairs on Pacifica DEX"
            }
        }
    )
else:
    logger.warning("x402 payments DISABLED - all endpoints are free")


@app.on_event("startup")
async def startup():
    """Initialize on startup"""
    logger.info("Starting API Gateway...")
    await redis_client.connect()


@app.on_event("shutdown")
async def shutdown():
    """Cleanup on shutdown"""
    logger.info("Shutting down API Gateway...")
    await redis_client.disconnect()


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


# Agent strategy config (monitor + tweak trading strategy via plain-English / Telegram)
@app.get("/api/v1/strategy-config")
async def get_strategy_config():
    """
    Return current strategy and risk parameters for Agent monitoring.
    Safe to expose (no secrets). Used by the agent to show and refine strategy.
    """
    return {
        "success": True,
        "source": "env_and_overrides",
        "overrides_path": settings.get_agent_overrides_path(),
        "config": settings.strategy_config_dict(),
    }


@app.patch("/api/v1/strategy-config")
async def patch_strategy_config(
    body: dict = Body(..., description="Partial config: only include keys to change"),
):
    """
    Merge partial strategy overrides. Writes to AGENT_OVERRIDES_PATH (or default).
    Trading engine reloads overrides every 60s, so changes apply without restart.
    Only keys in STRATEGY_CONFIG_KEYS are accepted.
    """
    allowed = {k: body[k] for k in body if k in STRATEGY_CONFIG_KEYS}
    if not allowed:
        raise HTTPException(
            status_code=400,
            detail="No valid strategy keys. Use GET /api/v1/strategy-config to see allowed keys.",
        )
    path = settings.get_agent_overrides_path()
    if not path:
        path = os.path.join(os.getcwd(), "config", "agent_strategy_overrides.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    existing = {}
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                existing = json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    existing.update(allowed)
    try:
        with open(path, "w") as f:
            json.dump(existing, f, indent=2)
    except OSError as e:
        raise HTTPException(status_code=500, detail=f"Failed to write overrides: {e}")
    settings.reload_agent_overrides()
    return {
        "success": True,
        "message": "Overrides saved. Trading engine will pick up changes within 60s.",
        "updated": list(allowed.keys()),
        "config": settings.strategy_config_dict(),
    }


# Market Data Endpoints

@app.get("/api/v1/ticks/{symbol}", response_model=TickResponse)
async def get_ticks(
    symbol: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Get tick data for a symbol"""
    try:
        query = select(Tick).where(Tick.symbol == symbol.upper())

        if start_time:
            query = query.where(Tick.time >= start_time)
        if end_time:
            query = query.where(Tick.time <= end_time)

        query = query.order_by(Tick.time.desc()).limit(limit)

        result = await db.execute(query)
        ticks = result.scalars().all()

        tick_data = [
            TickData(
                time=tick.time,
                price=tick.price,
                volume=tick.volume,
                bid=tick.bid,
                ask=tick.ask,
            )
            for tick in ticks
        ]

        return TickResponse(symbol=symbol.upper(), data=tick_data, count=len(tick_data))

    except Exception as e:
        logger.error(f"Error fetching ticks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/candles/{symbol}/{timeframe}", response_model=CandleResponse)
async def get_candles(
    symbol: str,
    timeframe: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    limit: int = Query(1000, ge=1, le=10000),
    db: AsyncSession = Depends(get_db),
):
    """Get OHLCV candles for a symbol"""
    # Map timeframe to interval
    interval_map = {
        "1m": "1 minute",
        "5m": "5 minutes",
        "15m": "15 minutes",
        "1h": "1 hour",
        "4h": "4 hours",
        "1d": "1 day",
    }

    if timeframe not in interval_map:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid timeframe. Must be one of: {list(interval_map.keys())}",
        )

    try:
        # Use continuous aggregates for efficient candle queries
        candles = await query_candles(
            session=db,
            symbol=symbol.upper(),
            timeframe=timeframe,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

        candle_data = [
            CandleData(
                time=candle["time"],
                open=candle["open"],
                high=candle["high"],
                low=candle["low"],
                close=candle["close"],
                volume=candle["volume"],
                vwap=candle["vwap"],
            )
            for candle in candles
        ]

        return CandleResponse(symbol=symbol.upper(), timeframe=timeframe, data=candle_data)

    except Exception as e:
        logger.error(f"Error fetching candles: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/pairs")
async def get_pairs(
    category: Optional[str] = Query(None),
    active_only: bool = Query(True),
):
    """Get all trading pairs"""
    try:
        from nexwave.common.pairs import PairCategory, get_pairs_by_category

        if active_only:
            pairs = get_active_pairs()
        else:
            pairs = get_all_pairs()

        if category:
            try:
                cat = PairCategory(category)
                pairs = [p for p in pairs if p.category == cat]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid category. Must be one of: {[c.value for c in PairCategory]}",
                )

        return {
            "pairs": [
                {
                    "symbol": pair.symbol,
                    "quote": pair.quote_asset,
                    "max_leverage": pair.max_leverage,
                    "min_order_size": float(pair.min_order_size),
                    "tick_size": float(pair.tick_size),
                    "display_name": pair.display_name,
                    "category": pair.category.value,
                    "whale_threshold_usd": float(pair.whale_threshold_usd) if pair.whale_threshold_usd else None,
                    "is_active": pair.is_active,
                }
                for pair in pairs
            ],
            "count": len(pairs),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching pairs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/latest-prices")
async def get_latest_prices(
    symbols: Optional[str] = Query(None, description="Comma-separated list of symbols"),
    db: AsyncSession = Depends(get_db),
):
    """Get latest prices for all or specified symbols"""
    try:
        # Get symbols list
        if symbols:
            symbol_list = [s.strip().upper() for s in symbols.split(",")]
            # Validate symbols
            invalid_symbols = [s for s in symbol_list if not validate_symbol(s)]
            if invalid_symbols:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid symbols: {', '.join(invalid_symbols)}",
                )
        else:
            from nexwave.common.pairs import get_all_symbols
            symbol_list = get_all_symbols()

        prices = []

        for symbol in symbol_list:
            query = select(Tick).where(Tick.symbol == symbol).order_by(Tick.time.desc()).limit(1)
            result = await db.execute(query)
            tick = result.scalar_one_or_none()

            if tick:
                # Get 24h old price for change calculation
                day_ago = datetime.utcnow() - timedelta(days=1)
                old_query = (
                    select(Tick)
                    .where(Tick.symbol == symbol, Tick.time <= day_ago)
                    .order_by(Tick.time.desc())
                    .limit(1)
                )
                old_result = await db.execute(old_query)
                old_tick = old_result.scalar_one_or_none()

                change_24h_pct = None
                if old_tick and old_tick.price > 0:
                    change_24h_pct = ((tick.price - old_tick.price) / old_tick.price) * 100

                pair_info = get_pair_by_symbol(symbol)
                prices.append(
                    {
                        "symbol": symbol,
                        "display_name": pair_info.display_name if pair_info else symbol,
                        "price": tick.price,
                        "time": tick.time.isoformat(),
                        "change_24h_pct": round(change_24h_pct, 2) if change_24h_pct else None,
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "category": pair_info.category.value if pair_info else None,
                    }
                )

        return {"prices": prices, "count": len(prices)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching latest prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Trading Endpoints (require authentication)

@app.post("/api/v1/orders", response_model=OrderResponse)
async def create_order(
    order: CreateOrderRequest,
    # TODO: Add authentication
    db: AsyncSession = Depends(get_db),
):
    """Create a new order"""
    # TODO: Implement order creation logic with Pacifica API
    # For now, return a placeholder
    return OrderResponse(
        order_id="placeholder",
        status="pending",
        created_at=datetime.utcnow(),
    )


@app.get("/api/v1/positions", response_model=PositionsResponse)
async def get_positions(
    strategy_id: Optional[str] = Query(None),
    # TODO: Add authentication
    db: AsyncSession = Depends(get_db),
):
    """Get current positions"""
    try:
        query = select(Position)
        if strategy_id:
            query = query.where(Position.strategy_id == strategy_id)

        result = await db.execute(query)
        positions = result.scalars().all()

        position_data = []
        for pos in positions:
            # Calculate notional value (position size in USD)
            notional = pos.amount * pos.entry_price

            # Calculate leverage from pair config (default to 3x for now)
            # Leverage = notional / margin (but Pacifica returns margin=0, so use max leverage from pair config)
            from nexwave.common.pairs import get_pair_by_symbol
            pair = get_pair_by_symbol(pos.symbol)
            leverage = pair.max_leverage if pair else 3.0

            # Calculate hold time in minutes
            from datetime import timezone
            now = datetime.now(timezone.utc)
            hold_time_min = int((now - pos.opened_at).total_seconds() / 60) if pos.opened_at else 0

            position_data.append(
                PositionSchema(
                    symbol=pos.symbol,
                    side=pos.side.upper(),
                    amount=pos.amount,
                    entry_price=pos.entry_price,
                    current_price=pos.current_price,
                    unrealized_pnl=pos.unrealized_pnl,
                    unrealized_pnl_pct=(
                        ((pos.current_price or pos.entry_price) - pos.entry_price) / pos.entry_price * 100
                        if pos.current_price
                        else None
                    ),
                    leverage=leverage,
                    notional=notional,
                    quantity=pos.amount,
                    hold_time_min=hold_time_min,
                )
            )

        return PositionsResponse(positions=position_data)

    except Exception as e:
        logger.error(f"Error fetching positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/trading/overview")
async def get_trading_overview(
    db: AsyncSession = Depends(get_db),
):
    """Get trading performance overview with P&L, volume, and win rate"""
    try:
        from datetime import timezone

        # Get all positions for active position count and total P&L
        positions_query = select(Position)
        positions_result = await db.execute(positions_query)
        positions = positions_result.scalars().all()

        active_positions = len(positions)
        total_unrealized_pnl = sum(pos.unrealized_pnl or 0 for pos in positions)
        total_realized_pnl = sum(pos.realized_pnl or 0 for pos in positions)

        # Get today's statistics
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Today's orders (volume and count)
        today_orders_query = select(
            func.count(Order.id).label('count'),
            func.sum(Order.amount * Order.price).label('volume')
        ).where(
            Order.created_at >= today_start
        )
        today_orders_result = await db.execute(today_orders_query)
        today_orders = today_orders_result.one()

        today_num_trades = int(today_orders.count or 0)
        today_volume = float(today_orders.volume or 0)

        # Today's P&L from positions opened today
        today_positions_query = select(
            func.sum(Position.unrealized_pnl).label('pnl')
        ).where(
            Position.opened_at >= today_start
        )
        today_pnl_result = await db.execute(today_positions_query)
        today_pnl = today_pnl_result.scalar() or 0

        # Calculate win rate from all positions (using unrealized P&L as proxy)
        winning_positions = sum(1 for pos in positions if (pos.unrealized_pnl or 0) > 0)
        losing_positions = sum(1 for pos in positions if (pos.unrealized_pnl or 0) < 0)
        total_positions = winning_positions + losing_positions
        win_rate = (winning_positions / total_positions * 100) if total_positions > 0 else 0

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "active_positions": active_positions,
            "total_positions": total_positions,
            "total_unrealized_pnl": round(total_unrealized_pnl, 2),
            "total_realized_pnl": round(total_realized_pnl, 2),
            "total_pnl": round(total_unrealized_pnl + total_realized_pnl, 2),
            "today": {
                "volume": round(today_volume, 2),
                "pnl": round(float(today_pnl), 2),
                "fees": 0,  # TODO: Calculate from orders when fee data available
                "num_trades": today_num_trades,
            },
            "win_rate": round(win_rate, 1),
        }

    except Exception as e:
        logger.error(f"Error fetching trading overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Analytics Endpoints

@app.get("/api/v1/performance")
async def get_performance(
    period: str = Query("24h", description="Time period: 1h, 24h, 7d, 30d, all"),
    strategy_id: str = Query("vwm_momentum_1", description="Strategy ID"),
):
    """
    Get comprehensive performance metrics for a trading strategy

    Returns win rate, P&L, Sharpe ratio, max drawdown, and more.
    """
    try:
        from nexwave.services.performance_tracker import PerformanceTracker

        tracker = PerformanceTracker(strategy_id)

        # Parse time period
        if period == "all":
            start_time = None
            end_time = None
        else:
            hours_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
            hours = hours_map.get(period, 24)
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)

        # Calculate metrics
        metrics = await tracker.calculate_metrics(start_time, end_time)
        distribution = await tracker.get_trade_distribution()

        return {
            "success": True,
            "strategy_id": strategy_id,
            "period": period,
            "metrics": {
                "start_date": metrics.start_date.isoformat() if metrics.start_date else None,
                "end_date": metrics.end_date.isoformat(),
                "period_hours": round(metrics.period_hours, 1),

                # Trading activity
                "total_trades": metrics.total_trades,
                "winning_trades": metrics.winning_trades,
                "losing_trades": metrics.losing_trades,
                "breakeven_trades": metrics.breakeven_trades,

                # Performance
                "win_rate": round(metrics.win_rate, 2),
                "total_pnl": round(metrics.total_pnl, 2),
                "avg_win": round(metrics.avg_win, 2),
                "avg_loss": round(metrics.avg_loss, 2),
                "largest_win": round(metrics.largest_win, 2),
                "largest_loss": round(metrics.largest_loss, 2),
                "profit_factor": round(metrics.profit_factor, 2),

                # Risk metrics
                "sharpe_ratio": round(metrics.sharpe_ratio, 2) if metrics.sharpe_ratio else None,
                "max_drawdown": round(metrics.max_drawdown, 2),
                "max_drawdown_pct": round(metrics.max_drawdown_pct, 2),

                # Efficiency
                "avg_hold_time_hours": round(metrics.avg_hold_time_hours, 2),
                "avg_profit_per_hour": round(metrics.avg_profit_per_hour, 2),

                # Portfolio state
                "open_positions": metrics.open_positions,
                "total_capital": round(metrics.total_capital, 2),
                "capital_deployed": round(metrics.capital_deployed, 2),
                "capital_utilization_pct": round(metrics.capital_utilization_pct, 1),
            },
            "distribution": distribution,
        }

    except Exception as e:
        logger.error(f"Error getting performance metrics: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": str(e)}
        )


@app.get("/api/analytics")
async def get_analytics(
    timeframe: str = Query("24h"),
    db: AsyncSession = Depends(get_db),
):
    """Get analytics data"""
    try:
        # Parse timeframe
        hours_map = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
        hours = hours_map.get(timeframe, 24)
        start_time = datetime.utcnow() - timedelta(hours=hours)

        # Initialize defaults
        tick_stats = None
        candle_count = 0
        market_data = []
        tick_rates = []
        whale_data = []

        # Get tick statistics
        try:
            tick_query = text("""
                SELECT
                    COUNT(*) as total_ticks,
                    COUNT(DISTINCT symbol) as unique_symbols,
                    0 as duplicates_filtered,
                    0 as outliers_filtered
                FROM ticks
                WHERE time >= :start_time
            """)
            tick_result = await db.execute(tick_query, {"start_time": start_time})
            tick_stats = tick_result.fetchone()
            await db.commit()
        except Exception as e:
            logger.error(f"Error fetching tick stats: {e}")
            await db.rollback()

        # Get candle count from TimescaleDB continuous aggregates
        try:
            candle_query = text("""
                SELECT COUNT(*) as candle_count
                FROM candles_1m
                WHERE bucket >= :start_time
            """)
            candle_result = await db.execute(candle_query, {"start_time": start_time})
            candle_stats = candle_result.fetchone()
            candle_count = int(candle_stats.candle_count) if candle_stats else 0
            await db.commit()
        except Exception as e:
            logger.debug(f"Candle data not available: {e}")
            await db.rollback()

        # Get market data for each symbol
        try:
            market_query = text("""
                SELECT DISTINCT ON (symbol)
                    symbol,
                    price,
                    volume,
                    time
                FROM ticks
                WHERE time >= :start_time
                ORDER BY symbol, time DESC
                LIMIT 10
            """)
            market_result = await db.execute(market_query, {"start_time": start_time})
            market_data = market_result.fetchall()
            await db.commit()
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            await db.rollback()

        # Get tick rates per symbol
        try:
            tick_rate_query = text("""
                SELECT
                    symbol,
                    COUNT(*) / GREATEST(EXTRACT(EPOCH FROM (MAX(time) - MIN(time))), 1) as tick_rate
                FROM ticks
                WHERE time >= :start_time
                GROUP BY symbol
                ORDER BY tick_rate DESC
                LIMIT 10
            """)
            tick_rate_result = await db.execute(tick_rate_query, {"start_time": start_time})
            tick_rates = tick_rate_result.fetchall()
            await db.commit()
        except Exception as e:
            logger.error(f"Error fetching tick rates: {e}")
            await db.rollback()

        # Get whale activities
        try:
            whale_query = text("""
                SELECT
                    symbol,
                    total_value_usd as size,
                    side,
                    detected_at as timestamp
                FROM whale_activities
                WHERE detected_at >= :start_time
                ORDER BY detected_at DESC
                LIMIT 10
            """)
            whale_result = await db.execute(whale_query, {"start_time": start_time})
            whale_data = whale_result.fetchall()
            await db.commit()
        except Exception as e:
            logger.debug(f"No whale data available: {e}")
            await db.rollback()

        # Build response
        return {
            "paperTrading": {
                "totalTrades": 0,
                "winRate": 0.0,
                "totalPnL": 0.0,
                "dailyReturn": 0.0,
                "maxDrawdown": 0.0,
                "sharpeRatio": 0.0,
            },
            "dataCollection": {
                "totalTicks": int(tick_stats.total_ticks) if tick_stats else 0,
                "duplicatesFiltered": 0,
                "outliersFiltered": 0,
                "candlesGenerated": candle_count,
                "tickRate": {
                    row.symbol: float(row.tick_rate)
                    for row in tick_rates
                },
                "errors": 0,
            },
            "marketData": {
                "symbols": [
                    {
                        "symbol": row.symbol,
                        "price": float(row.price),
                        "change24h": 0.0,
                        "volume24h": float(row.volume or 0),
                        "volatility": 0.0,
                    }
                    for row in market_data
                ]
            },
            "performance": {
                "dailyStats": []
            },
            "momentumScores": {
                "symbols": []
            },
            "whaleActivity": {
                "totalWhales": len(whale_data),
                "recentWhales": [
                    {
                        "symbol": row.symbol,
                        "size": float(row.size),
                        "side": row.side,
                        "timestamp": row.timestamp.isoformat() if row.timestamp else datetime.utcnow().isoformat(),
                    }
                    for row in whale_data
                ],
                "whaleImpact": {}
            }
        }

    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/backtest/results")
async def get_backtest_results():
    """Get backtest results"""
    return {"results": []}


@app.get("/api/v1/daily-stats")
async def get_daily_stats(
    days: int = Query(30, ge=1, le=365),
    db: AsyncSession = Depends(get_db),
):
    """Get daily P&L statistics aggregated by date"""
    try:
        from sqlalchemy import func, case
        from datetime import timedelta, date, timezone

        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=days)

        # Aggregate positions by date
        query = select(
            func.date(Position.opened_at).label('date'),
            func.count(Position.id).label('num_trades'),
            func.sum(Position.unrealized_pnl).label('pnl'),
            func.sum(Position.amount * Position.entry_price).label('volume')
        ).where(
            Position.opened_at >= start_date
        ).group_by(
            func.date(Position.opened_at)
        )

        result = await db.execute(query)
        stats_by_date = {row.date: row for row in result.all()}

        # Fill in missing dates with zero P&L to create a continuous chart
        daily_stats = []
        current_date = start_date.date()
        end_date = now.date()

        while current_date <= end_date:
            if current_date in stats_by_date:
                row = stats_by_date[current_date]
                daily_stats.append({
                    "date": current_date.isoformat(),
                    "num_trades": int(row.num_trades or 0),
                    "pnl": float(row.pnl or 0),
                    "volume": float(row.volume or 0),
                })
            else:
                # Fill missing dates with zeros
                daily_stats.append({
                    "date": current_date.isoformat(),
                    "num_trades": 0,
                    "pnl": 0.0,
                    "volume": 0.0,
                })
            current_date += timedelta(days=1)

        # Return in reverse chronological order (most recent first)
        return list(reversed(daily_stats))

    except Exception as e:
        logger.error(f"Error fetching daily stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/volume-weighted-momentum/all")
async def get_volume_weighted_momentum():
    """Get volume-weighted momentum for all symbols"""
    return {}


# WebSocket endpoint

@app.websocket("/ws/market-data")
async def websocket_market_data(websocket: WebSocket):
    """WebSocket endpoint for real-time market data"""
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        # Subscribe to market data channels
        # TODO: Parse subscription requests from client and subscribe to Redis pub/sub
        
        # For now, send periodic ping
        while True:
            try:
                await websocket.send_json({"type": "ping", "timestamp": datetime.utcnow().isoformat()})
                await asyncio.sleep(30)  # Send ping every 30 seconds
            except WebSocketDisconnect:
                break

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)

