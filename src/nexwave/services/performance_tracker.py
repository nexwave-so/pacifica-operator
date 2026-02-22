"""Performance metrics tracking for trading strategies"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
import statistics
import os

from sqlalchemy import select, func, and_

# Import only what we need to avoid heavy dependencies
try:
    from nexwave.common.logger import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)

from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Order, Position


@dataclass
class PerformanceMetrics:
    """Performance metrics snapshot"""

    # Time period
    start_date: datetime
    end_date: datetime
    period_hours: float

    # Trading activity
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int

    # Performance
    win_rate: float  # Percentage
    total_pnl: float  # USD
    avg_win: float  # USD
    avg_loss: float  # USD
    largest_win: float  # USD
    largest_loss: float  # USD
    profit_factor: float  # Total wins / Total losses

    # Risk metrics
    sharpe_ratio: Optional[float]  # Risk-adjusted return
    max_drawdown: float  # USD
    max_drawdown_pct: float  # Percentage

    # Efficiency
    avg_hold_time_hours: float
    avg_profit_per_hour: float  # USD/hour

    # Current state
    open_positions: int
    total_capital: float
    capital_deployed: float
    capital_utilization_pct: float


class PerformanceTracker:
    """Tracks and calculates trading performance metrics"""

    def __init__(self, strategy_id: str):
        self.strategy_id = strategy_id

    async def get_closed_trades(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get all closed trades (positions that have been exited)

        Note: We identify closed trades by matching opening and closing orders
        """
        try:
            async with AsyncSessionLocal() as session:
                # Get all orders for this strategy, sorted by time
                query = (
                    select(Order)
                    .where(Order.strategy_id == self.strategy_id)
                    .order_by(Order.created_at)
                )

                if start_time:
                    query = query.where(Order.created_at >= start_time)
                if end_time:
                    query = query.where(Order.created_at <= end_time)

                result = await session.execute(query)
                orders = result.scalars().all()

                # Group orders into trades (open → close pairs)
                trades = []
                open_orders = {}  # symbol -> order

                for order in orders:
                    symbol = order.symbol
                    side = order.side

                    # Check if this is an opening order (bid for long, ask for short)
                    is_opening_long = side == "bid" and symbol not in open_orders
                    is_opening_short = side == "ask" and symbol not in open_orders

                    # Check if this is a closing order (opposite side)
                    is_closing_long = side == "ask" and symbol in open_orders and open_orders[symbol].side == "bid"
                    is_closing_short = side == "bid" and symbol in open_orders and open_orders[symbol].side == "ask"

                    if is_opening_long or is_opening_short:
                        # Store opening order
                        open_orders[symbol] = order

                    elif is_closing_long or is_closing_short:
                        # We have a complete trade
                        entry_order = open_orders.pop(symbol)
                        exit_order = order

                        # Calculate P&L
                        if entry_order.side == "bid":  # Long trade
                            pnl = (exit_order.price - entry_order.price) * entry_order.amount
                        else:  # Short trade
                            pnl = (entry_order.price - exit_order.price) * entry_order.amount

                        # Calculate hold time
                        hold_time = (exit_order.created_at - entry_order.created_at).total_seconds() / 3600

                        trades.append({
                            "symbol": symbol,
                            "side": "LONG" if entry_order.side == "bid" else "SHORT",
                            "entry_price": entry_order.price,
                            "exit_price": exit_order.price,
                            "amount": entry_order.amount,
                            "pnl": pnl,
                            "pnl_pct": (pnl / (entry_order.price * entry_order.amount)) * 100,
                            "hold_time_hours": hold_time,
                            "entry_time": entry_order.created_at,
                            "exit_time": exit_order.created_at,
                            "exit_reason": exit_order.metadata.get("reason", "unknown") if exit_order.metadata else "unknown",
                        })

                return trades

        except Exception as e:
            logger.error(f"Error getting closed trades: {e}")
            return []

    async def calculate_metrics(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> PerformanceMetrics:
        """Calculate comprehensive performance metrics for a time period"""

        try:
            # Default to last 24 hours if no time specified
            if not end_time:
                end_time = datetime.utcnow()
            if not start_time:
                start_time = end_time - timedelta(hours=24)

            period_hours = (end_time - start_time).total_seconds() / 3600

            # Get closed trades
            trades = await self.get_closed_trades(start_time, end_time)

            # Calculate basic metrics
            total_trades = len(trades)
            winning_trades = len([t for t in trades if t["pnl"] > 0])
            losing_trades = len([t for t in trades if t["pnl"] < 0])
            breakeven_trades = len([t for t in trades if t["pnl"] == 0])

            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

            total_pnl = sum(t["pnl"] for t in trades)

            wins = [t["pnl"] for t in trades if t["pnl"] > 0]
            losses = [abs(t["pnl"]) for t in trades if t["pnl"] < 0]

            avg_win = statistics.mean(wins) if wins else 0.0
            avg_loss = statistics.mean(losses) if losses else 0.0
            largest_win = max(wins) if wins else 0.0
            largest_loss = max(losses) if losses else 0.0

            total_wins = sum(wins)
            total_losses = sum(losses)
            profit_factor = (total_wins / total_losses) if total_losses > 0 else 0.0

            # Calculate Sharpe ratio (risk-adjusted return)
            if len(trades) >= 2:
                returns = [t["pnl_pct"] for t in trades]
                avg_return = statistics.mean(returns)
                std_return = statistics.stdev(returns)
                # Annualized Sharpe (assuming crypto trades 24/7)
                sharpe_ratio = (avg_return / std_return) * (8760 ** 0.5) if std_return > 0 else None
            else:
                sharpe_ratio = None

            # Calculate max drawdown
            max_drawdown = 0.0
            max_drawdown_pct = 0.0
            if trades:
                cumulative_pnl = 0
                peak_pnl = 0
                for trade in sorted(trades, key=lambda t: t["exit_time"]):
                    cumulative_pnl += trade["pnl"]
                    if cumulative_pnl > peak_pnl:
                        peak_pnl = cumulative_pnl
                    drawdown = peak_pnl - cumulative_pnl
                    if drawdown > max_drawdown:
                        max_drawdown = drawdown
                        max_drawdown_pct = (drawdown / (peak_pnl + 1)) * 100 if peak_pnl > 0 else 0

            # Calculate hold time metrics
            avg_hold_time_hours = statistics.mean([t["hold_time_hours"] for t in trades]) if trades else 0.0
            avg_profit_per_hour = (total_pnl / (total_trades * avg_hold_time_hours)) if (total_trades > 0 and avg_hold_time_hours > 0) else 0.0

            # Get current portfolio state
            async with AsyncSessionLocal() as session:
                # Count open positions
                query = select(func.count(Position.symbol)).where(
                    Position.strategy_id == self.strategy_id
                )
                result = await session.execute(query)
                open_positions = result.scalar() or 0

                # Calculate capital deployed
                query = select(
                    func.sum(Position.amount * Position.current_price)
                ).where(Position.strategy_id == self.strategy_id)
                result = await session.execute(query)
                capital_deployed = result.scalar() or 0.0

                # Get total capital from environment
                import os
                total_capital = float(os.getenv("PORTFOLIO_VALUE", "100000"))

                capital_utilization_pct = (capital_deployed / total_capital * 100) if total_capital > 0 else 0.0

            return PerformanceMetrics(
                start_date=start_time,
                end_date=end_time,
                period_hours=period_hours,
                total_trades=total_trades,
                winning_trades=winning_trades,
                losing_trades=losing_trades,
                breakeven_trades=breakeven_trades,
                win_rate=win_rate,
                total_pnl=total_pnl,
                avg_win=avg_win,
                avg_loss=avg_loss,
                largest_win=largest_win,
                largest_loss=largest_loss,
                profit_factor=profit_factor,
                sharpe_ratio=sharpe_ratio,
                max_drawdown=max_drawdown,
                max_drawdown_pct=max_drawdown_pct,
                avg_hold_time_hours=avg_hold_time_hours,
                avg_profit_per_hour=avg_profit_per_hour,
                open_positions=open_positions,
                total_capital=total_capital,
                capital_deployed=capital_deployed,
                capital_utilization_pct=capital_utilization_pct,
            )

        except Exception as e:
            logger.error(f"Error calculating performance metrics: {e}")
            raise

    async def get_trade_distribution(self) -> Dict:
        """Get distribution of trades by outcome"""

        trades = await self.get_closed_trades()

        if not trades:
            return {
                "by_outcome": {},
                "by_symbol": {},
                "by_exit_reason": {},
            }

        # Group by outcome
        by_outcome = {
            "big_winner": len([t for t in trades if t["pnl"] > 3.0]),  # >$3
            "winner": len([t for t in trades if 0 < t["pnl"] <= 3.0]),  # $0-$3
            "breakeven": len([t for t in trades if t["pnl"] == 0]),
            "loser": len([t for t in trades if -2.0 <= t["pnl"] < 0]),  # -$2 to $0
            "big_loser": len([t for t in trades if t["pnl"] < -2.0]),  # <-$2
        }

        # Group by symbol
        by_symbol = {}
        for trade in trades:
            symbol = trade["symbol"]
            if symbol not in by_symbol:
                by_symbol[symbol] = {"count": 0, "total_pnl": 0, "win_rate": 0}
            by_symbol[symbol]["count"] += 1
            by_symbol[symbol]["total_pnl"] += trade["pnl"]

        # Calculate win rates per symbol
        for symbol, data in by_symbol.items():
            symbol_trades = [t for t in trades if t["symbol"] == symbol]
            wins = len([t for t in symbol_trades if t["pnl"] > 0])
            data["win_rate"] = (wins / len(symbol_trades) * 100) if symbol_trades else 0

        # Group by exit reason
        by_exit_reason = {}
        for trade in trades:
            reason = trade["exit_reason"]
            if reason not in by_exit_reason:
                by_exit_reason[reason] = 0
            by_exit_reason[reason] += 1

        return {
            "by_outcome": by_outcome,
            "by_symbol": dict(sorted(by_symbol.items(), key=lambda x: x[1]["total_pnl"], reverse=True)),
            "by_exit_reason": by_exit_reason,
        }
