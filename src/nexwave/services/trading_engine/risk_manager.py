"""Risk management for trading engine"""

import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Set
from dataclasses import dataclass
from collections import defaultdict
from nexwave.common.config import settings
from nexwave.common.logger import logger
from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Position, Order
from sqlalchemy import select, func


@dataclass
class RiskCheckResult:
    """Result of risk management check"""

    approved: bool
    reason: str
    details: Optional[Dict] = None


class RiskManager:
    """Manages risk limits and order validation. Reads from settings on each check so Nexbot overrides apply without restart."""

    def __init__(self):
        # Trade throttling tracking (in-memory only)
        self.last_trade_time: Dict[str, datetime] = {}
        self.daily_trade_count: Dict[str, int] = defaultdict(int)
        self.last_reset_date: Optional[datetime] = None

    def _limits(self):
        """Current limits from settings (incl. Nexbot overrides)."""
        return {
            "max_position_size_usd": settings.max_position_size_usd,
            "max_leverage": settings.max_leverage,
            "daily_loss_limit_pct": settings.daily_loss_limit_pct,
            "min_order_size_usd": settings.min_order_size_usd,
            "max_order_size_usd": settings.max_order_size_usd,
            "maintenance_margin_ratio": settings.maintenance_margin_ratio,
            "min_profit_target_usd": settings.min_profit_target_usd,
            "trade_cooldown_seconds": settings.trade_cooldown_seconds,
            "max_trades_per_symbol_per_day": settings.max_trades_per_symbol_per_day,
            "symbol_blacklist": {s.strip().upper() for s in settings.symbol_blacklist.split(",") if s.strip()},
        }

    async def get_portfolio_value(self, strategy_id: str) -> float:
        """Get current portfolio value for a strategy"""
        try:
            async with AsyncSessionLocal() as session:
                # Get initial portfolio value from environment variable
                import os
                initial_cash = float(os.getenv("PORTFOLIO_VALUE", "100000"))
                
                # Get unrealized PnL from open positions
                query = select(func.sum(Position.unrealized_pnl)).where(
                    Position.strategy_id == strategy_id
                )
                result = await session.execute(query)
                unrealized_pnl = result.scalar() or 0.0
                
                # Get realized PnL from closed positions (cumulative)
                # Sum all realized PnL from positions that have been closed
                query = select(func.sum(Position.realized_pnl)).where(
                    Position.strategy_id == strategy_id,
                    Position.realized_pnl.isnot(None)
                )
                result = await session.execute(query)
                realized_pnl = result.scalar() or 0.0
                
                # Portfolio value = initial cash + unrealized PnL + realized PnL
                portfolio_value = initial_cash + unrealized_pnl + realized_pnl
                
                # Ensure portfolio value doesn't go negative (safety check)
                return max(0.0, portfolio_value)
                
        except Exception as e:
            logger.error(f"Error calculating portfolio value: {e}")
            # Fallback to default value on error
            return 100000.0

    async def get_current_positions(
        self, strategy_id: str, symbol: Optional[str] = None
    ) -> List[Dict]:
        """Get current open positions"""

        try:
            async with AsyncSessionLocal() as session:
                query = select(Position).where(Position.strategy_id == strategy_id)

                if symbol:
                    query = query.where(Position.symbol == symbol.upper())

                result = await session.execute(query)
                positions = result.scalars().all()

                return [
                    {
                        "symbol": pos.symbol,
                        "side": pos.side,
                        "amount": pos.amount,
                        "entry_price": pos.entry_price,
                        "current_price": pos.current_price,
                        "unrealized_pnl": pos.unrealized_pnl,
                    }
                    for pos in positions
                ]

        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []

    async def calculate_daily_pnl(self, strategy_id: str) -> float:
        """Calculate daily PnL for a strategy"""

        try:
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

            async with AsyncSessionLocal() as session:
                # Get realized PnL from closed positions today
                query = select(func.sum(Position.realized_pnl)).where(
                    Position.strategy_id == strategy_id,
                    Position.updated_at >= today_start,
                )

                result = await session.execute(query)
                realized_pnl = result.scalar() or 0.0

                # Get unrealized PnL from open positions
                query = select(func.sum(Position.unrealized_pnl)).where(
                    Position.strategy_id == strategy_id
                )

                result = await session.execute(query)
                unrealized_pnl = result.scalar() or 0.0

                return realized_pnl + unrealized_pnl

        except Exception as e:
            logger.error(f"Error calculating daily PnL: {e}")
            return 0.0

    def reset_daily_counts_if_needed(self) -> None:
        """Reset daily trade counts at start of new day"""
        now = datetime.utcnow()
        today = now.date()

        if self.last_reset_date is None or self.last_reset_date.date() != today:
            logger.info(f"Resetting daily trade counts (new day: {today})")
            self.daily_trade_count.clear()
            self.last_reset_date = now

    def check_symbol_blacklist(self, symbol: str) -> RiskCheckResult:
        """Check if symbol is blacklisted due to poor historical performance"""
        if symbol.upper() in self.symbol_blacklist:
            return RiskCheckResult(
                approved=False,
                reason=f"Symbol {symbol} is blacklisted (historical losses, low win rate)",
            )
        return RiskCheckResult(approved=True, reason="Symbol not blacklisted")

    def check_trade_frequency(self, symbol: str) -> RiskCheckResult:
        """Check if trade frequency limits are exceeded"""
        self.reset_daily_counts_if_needed()

        now = datetime.utcnow()
        symbol_upper = symbol.upper()

        limits = self._limits()
        # Check cooldown period (5 minutes between trades on same symbol)
        if symbol_upper in self.last_trade_time:
            time_since_last_trade = (now - self.last_trade_time[symbol_upper]).total_seconds()
            if time_since_last_trade < limits["trade_cooldown_seconds"]:
                remaining = limits["trade_cooldown_seconds"] - time_since_last_trade
                return RiskCheckResult(
                    approved=False,
                    reason=f"Trade cooldown active for {symbol}: {remaining:.0f}s remaining (min {limits['trade_cooldown_seconds']}s between trades)",
                )

        # Check daily trade limit (max 10 trades per symbol per day)
        daily_count = self.daily_trade_count.get(symbol_upper, 0)
        if daily_count >= limits["max_trades_per_symbol_per_day"]:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily trade limit reached for {symbol}: {daily_count}/{limits['max_trades_per_symbol_per_day']}",
            )

        return RiskCheckResult(approved=True, reason="Trade frequency OK")

    def record_trade(self, symbol: str) -> None:
        """Record a trade for frequency tracking"""
        self.reset_daily_counts_if_needed()

        now = datetime.utcnow()
        symbol_upper = symbol.upper()

        self.last_trade_time[symbol_upper] = now
        self.daily_trade_count[symbol_upper] += 1

        limits = self._limits()
        logger.debug(
            f"Trade recorded for {symbol}: "
            f"{self.daily_trade_count[symbol_upper]}/{limits['max_trades_per_symbol_per_day']} today"
        )

    def check_order_size(self, order_amount: float, order_price: float) -> RiskCheckResult:
        """Check if order size is within limits"""

        order_size_usd = order_amount * order_price

        if order_size_usd < self.min_order_size_usd:
            return RiskCheckResult(
                approved=False,
                reason=f"Order size too small: ${order_size_usd:.2f} < ${self.min_order_size_usd:.2f}",
            )

        if order_size_usd > self.max_order_size_usd:
            return RiskCheckResult(
                approved=False,
                reason=f"Order size too large: ${order_size_usd:.2f} > ${self.max_order_size_usd:.2f}",
            )

        return RiskCheckResult(approved=True, reason="Order size OK")

    def check_profit_viability(self, order_amount: float, order_price: float) -> RiskCheckResult:
        """
        Check if trade can realistically achieve minimum profit after fees

        Prevents entering trades where even a 5% price move wouldn't cover fees
        """
        limits = self._limits()
        order_size_usd = order_amount * order_price

        # Estimate round-trip fees (entry + exit) at 0.04% taker fee
        estimated_fees = order_size_usd * 0.0004 * 2  # 0.08% round-trip

        # Minimum profit target after fees
        min_profit_needed = limits["min_profit_target_usd"] + estimated_fees

        # Calculate required price move percentage
        required_move_pct = (min_profit_needed / order_size_usd) * 100

        # Reject if we need >5% price move just to hit minimum profit
        # (Unrealistic for most strategies except extreme volatility)
        if required_move_pct > 5.0:
            return RiskCheckResult(
                approved=False,
                reason=f"Trade requires unrealistic {required_move_pct:.2f}% price move for ${limits['min_profit_target_usd']} profit (after fees)",
                details={
                    "order_size_usd": order_size_usd,
                    "estimated_fees": estimated_fees,
                    "min_profit_needed": min_profit_needed,
                    "required_move_pct": required_move_pct,
                }
            )

        return RiskCheckResult(approved=True, reason="Profit target viable")

    async def check_position_limit(
        self, strategy_id: str, symbol: str, new_position_size_usd: float
    ) -> RiskCheckResult:
        """Check if new position exceeds position limit"""

        current_positions = await self.get_current_positions(strategy_id, symbol)

        # Calculate total position size for this symbol
        total_position_usd = 0.0
        for pos in current_positions:
            if pos["symbol"].upper() == symbol.upper():
                current_price = pos.get("current_price") or pos.get("entry_price", 0)
                total_position_usd += pos["amount"] * current_price

        # Add new position size
        total_position_usd += new_position_size_usd

        if total_position_usd > self.max_position_size_usd:
            return RiskCheckResult(
                approved=False,
                reason=f"Position limit exceeded: ${total_position_usd:,.0f} > ${self.max_position_size_usd:,.0f}",
                details={"current": total_position_usd - new_position_size_usd, "new": total_position_usd},
            )

        return RiskCheckResult(approved=True, reason="Position limit OK")

    async def check_leverage(
        self, strategy_id: str, new_position_size_usd: float
    ) -> RiskCheckResult:
        """Check if leverage exceeds maximum"""
        limits = self._limits()
        portfolio_value = await self.get_portfolio_value(strategy_id)

        # Calculate total position exposure
        current_positions = await self.get_current_positions(strategy_id)
        total_exposure_usd = sum(
            (pos.get("current_price") or pos.get("entry_price", 0)) * pos["amount"]
            for pos in current_positions
        )

        total_exposure_usd += new_position_size_usd

        # Calculate leverage
        leverage = total_exposure_usd / portfolio_value if portfolio_value > 0 else 0.0

        if leverage > limits["max_leverage"]:
            return RiskCheckResult(
                approved=False,
                reason=f"Leverage too high: {leverage:.2f}x > {limits['max_leverage']:.2f}x",
                details={"leverage": leverage, "exposure": total_exposure_usd, "portfolio": portfolio_value},
            )

        return RiskCheckResult(approved=True, reason=f"Leverage OK: {leverage:.2f}x")

    async def check_daily_loss_limit(self, strategy_id: str) -> RiskCheckResult:
        """Check if daily loss limit has been exceeded"""

        daily_pnl = await self.calculate_daily_pnl(strategy_id)
        portfolio_value = await self.get_portfolio_value(strategy_id)

        if portfolio_value <= 0:
            return RiskCheckResult(approved=False, reason="Invalid portfolio value")

        daily_loss_pct = (daily_pnl / portfolio_value) * 100

        if daily_loss_pct <= -self.daily_loss_limit_pct:
            return RiskCheckResult(
                approved=False,
                reason=f"Daily loss limit exceeded: {daily_loss_pct:.2f}% <= -{self.daily_loss_limit_pct}%",
                details={"daily_pnl": daily_pnl, "daily_pnl_pct": daily_loss_pct},
            )

        return RiskCheckResult(approved=True, reason="Daily loss limit OK")

    async def check_order(
        self,
        strategy_id: str,
        symbol: str,
        side: str,
        amount: float,
        price: float,
        order_type: str = "market",
    ) -> RiskCheckResult:
        """
        Comprehensive risk check for an order

        Returns:
            RiskCheckResult with approval status and reason
        """

        # 0. Check symbol blacklist (fail fast - prevents trading bad symbols)
        blacklist_check = self.check_symbol_blacklist(symbol)
        if not blacklist_check.approved:
            return blacklist_check

        # 1. Check trade frequency (fail fast - prevents overtrading)
        frequency_check = self.check_trade_frequency(symbol)
        if not frequency_check.approved:
            return frequency_check

        # 2. Check daily loss limit (fail fast)
        daily_loss_check = await self.check_daily_loss_limit(strategy_id)
        if not daily_loss_check.approved:
            return daily_loss_check

        # 3. Check order size
        size_check = self.check_order_size(amount, price)
        if not size_check.approved:
            return size_check

        # 4. Check profit viability (can we realistically profit after fees?)
        profit_check = self.check_profit_viability(amount, price)
        if not profit_check.approved:
            return profit_check

        # 5. Check position limit
        order_size_usd = amount * price
        position_check = await self.check_position_limit(strategy_id, symbol, order_size_usd)
        if not position_check.approved:
            return position_check

        # 6. Check leverage
        leverage_check = await self.check_leverage(strategy_id, order_size_usd)
        if not leverage_check.approved:
            return leverage_check

        # All checks passed
        return RiskCheckResult(
            approved=True,
            reason="All risk checks passed",
            details={
                "order_size_usd": order_size_usd,
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
            },
        )

