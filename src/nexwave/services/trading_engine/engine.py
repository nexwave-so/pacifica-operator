"""Trading Engine - Executes trading strategies"""

import asyncio
import json
import os
import uuid
from datetime import datetime
from typing import Dict, Optional, List

from nexwave.common.config import settings
from nexwave.common.logger import logger
from nexwave.common.redis_client import redis_client
from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Order, Position, Tick
from nexwave.strategies.base_strategy import BaseStrategy
from nexwave.strategies.momentum.short_term_momentum import ShortTermMomentumStrategy
from nexwave.strategies.momentum.long_term_momentum import LongTermMomentumStrategy
from nexwave.strategies.momentum.momentum_short import MomentumShortStrategy
from nexwave.strategies.mean_reversion.mr_long_hedge import MRLongHedgeStrategy
from nexwave.strategies.mean_reversion.mr_short_hedge import MRShortHedgeStrategy
from nexwave.services.portfolio.exposure_manager import ExposureManager
from nexwave.services.portfolio.position_sizer import PositionSizer
from nexwave.services.portfolio.hedge_trigger import HedgeTrigger, HedgeAction
from nexwave.services.market.regime_detector import RegimeDetector, MarketRegime
from nexwave.services.order_management.pacifica_client import PacificaClient
from .risk_manager import RiskManager


class TradingEngine:
    """Main trading engine that executes strategies"""

    def __init__(
        self,
        strategy_id: str,
        paper_trading: bool = True,
        portfolio_value: float = 100000.0,
    ):
        self.strategy_id = strategy_id
        self.paper_trading = paper_trading
        self.portfolio_value = portfolio_value
        self.strategies: Dict[str, BaseStrategy] = {}
        self.momentum_strategies: Dict[str, BaseStrategy] = {}
        self.mr_long_hedge_strategies: Dict[str, BaseStrategy] = {}
        self.mr_short_hedge_strategies: Dict[str, BaseStrategy] = {}
        self.risk_manager = RiskManager()
        self.exposure_manager = ExposureManager(portfolio_value)
        self.position_sizer = PositionSizer(portfolio_value)
        self.hedge_trigger = HedgeTrigger()
        self.regime_detector = RegimeDetector("BTC")  # Use BTC for overall market regime
        self.running = False

        # Pacifica client for direct order placement
        self.pacifica_client: Optional[PacificaClient] = None

    async def connect(self) -> None:
        """Connect to Redis and Pacifica"""

        await redis_client.connect()

        # Initialize Pacifica client for direct order placement
        try:
            self.pacifica_client = PacificaClient()
            logger.info("✅ Connected to Pacifica API for order placement")
        except Exception as e:
            logger.error(f"Failed to initialize Pacifica client: {e}")
            if not self.paper_trading:
                logger.error("Real trading requires Pacifica client. Check your API credentials.")
            self.pacifica_client = None

    async def disconnect(self) -> None:
        """Disconnect from services"""

        await redis_client.disconnect()

    def initialize_strategies(self) -> None:
        """Initialize trading strategies"""

        symbols = settings.symbol_list

        for symbol in symbols:
            # Momentum strategies
            self.momentum_strategies[f"stm_{symbol}"] = ShortTermMomentumStrategy(
                strategy_id=f"stm_{self.strategy_id}",
                symbol=symbol,
                portfolio_value=self.portfolio_value
            )
            self.momentum_strategies[f"ltm_{symbol}"] = LongTermMomentumStrategy(
                strategy_id=f"ltm_{self.strategy_id}",
                symbol=symbol,
                portfolio_value=self.portfolio_value
            )
            self.momentum_strategies[f"ms_{symbol}"] = MomentumShortStrategy(
                strategy_id=f"ms_{self.strategy_id}",
                symbol=symbol,
                portfolio_value=self.portfolio_value
            )

            # Mean reversion hedge strategies
            self.mr_long_hedge_strategies[symbol] = MRLongHedgeStrategy(
                strategy_id=f"mrlh_{self.strategy_id}",
                symbol=symbol,
                portfolio_value=self.portfolio_value
            )
            self.mr_short_hedge_strategies[symbol] = MRShortHedgeStrategy(
                strategy_id=f"mrsh_{self.strategy_id}",
                symbol=symbol,
                portfolio_value=self.portfolio_value
            )
            
            logger.info(f"Initialized all strategies for {symbol}")

        self.strategies = {
            **self.momentum_strategies, 
            **self.mr_long_hedge_strategies, 
            **self.mr_short_hedge_strategies
        }

    async def get_market_data(self, symbol: str) -> Optional[Dict]:
        """Get current market data for a symbol"""

        try:
            # Try to get latest price from Redis
            price_key = f"price:{symbol}:latest"
            price_data = await redis_client.get(price_key)

            if price_data:
                try:
                    data = json.loads(price_data)
                    return {
                        "price": float(data.get("price", 0)),
                        "bid": data.get("bid"),
                        "ask": data.get("ask"),
                        "volume": data.get("volume"),
                        "timestamp": data.get("timestamp"),
                    }
                except (json.JSONDecodeError, ValueError, KeyError):
                    pass

            # Fallback: get from database
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                from nexwave.db.models import Tick

                # Try exact symbol match first (case-sensitive)
                query = (
                    select(Tick)
                    .where(Tick.symbol == symbol)
                    .order_by(Tick.time.desc())
                    .limit(1)
                )
                result = await session.execute(query)
                tick = result.scalar_one_or_none()

                # If not found, try uppercase (for symbols like kBONK, kPEPE)
                if not tick:
                    query = (
                        select(Tick)
                        .where(Tick.symbol == symbol.upper())
                        .order_by(Tick.time.desc())
                        .limit(1)
                    )
                    result = await session.execute(query)
                    tick = result.scalar_one_or_none()

                if tick:
                    logger.debug(f"Retrieved market data for {symbol} from database (fallback)")
                    return {
                        "price": tick.price,
                        "bid": tick.bid,
                        "ask": tick.ask,
                        "volume": tick.volume,
                        "timestamp": tick.time.isoformat(),
                    }

            logger.warning(f"No market data found in Redis or database for {symbol}")
            return None

        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None

    async def create_order(self, signal) -> Optional[str]:
        """Create an order based on signal"""

        try:
            # Map signal types to order sides
            side_map = {
                "buy": "bid",
                "sell": "ask",
                "close_long": "ask",
                "close_short": "bid",
            }

            order_side = side_map.get(signal.signal_type.value, "bid")
            is_market_order = True  # Always use market orders for now

            # Risk check
            risk_check = await self.risk_manager.check_order(
                strategy_id=self.strategy_id,
                symbol=signal.symbol,
                side=order_side,
                amount=signal.amount,
                price=signal.price,
                order_type="market" if is_market_order else "limit",
            )

            if not risk_check.approved:
                logger.warning(
                    f"Order rejected by risk manager: {risk_check.reason} "
                    f"({signal.symbol} {signal.signal_type.value})"
                )
                return None

            # Create order request
            client_order_id = str(uuid.uuid4())

            # Use reduce_only for closing positions (critical for perpetuals)
            is_closing = signal.signal_type.value in ["close_long", "close_short"]

            # REAL ORDER PLACEMENT: Call Pacifica API directly
            if self.paper_trading:
                logger.info(
                    f"📝 PAPER TRADING: {order_side} {signal.symbol} "
                    f"{signal.amount:.6f} @ ${signal.price:.2f}"
                )
                return client_order_id

            # Place real order on Pacifica
            if not self.pacifica_client:
                logger.error("Pacifica client not initialized. Cannot place orders.")
                return None

            try:
                # Round amount to 2 decimal places (Pacifica lot size = 0.01)
                rounded_amount = round(signal.amount, 2)
                logger.info(f"Placing {order_side} order on Pacifica: {signal.symbol} {rounded_amount}")

                # Include TP/SL in order creation (optional - can be None)
                # Only include TP/SL if both are valid (not None and > 0)
                stop_loss = signal.stop_loss if (not is_closing and signal.stop_loss and signal.stop_loss > 0) else None
                take_profit = signal.take_profit if (not is_closing and signal.take_profit and signal.take_profit > 0) else None
                
                # Pass entry price for TP/SL validation and rounding
                response = await self.pacifica_client.create_market_order(
                    symbol=signal.symbol,
                    side=order_side,
                    amount=rounded_amount,
                    reduce_only=is_closing,
                    client_order_id=client_order_id,
                    stop_loss=stop_loss,
                    take_profit=take_profit,
                    entry_price=signal.price,  # Pass entry price for validation
                )

                # Extract Pacifica order ID
                pacifica_order_id = None
                if response.get('success'):
                    data = response.get('data', {})
                    pacifica_order_id = data.get('order_id') if isinstance(data, dict) else response.get('order_id')

                # Log order placement with TP/SL info
                tp_sl_info = ""
                if not is_closing and (signal.stop_loss or signal.take_profit):
                    sl_str = f"{signal.stop_loss:.4f}" if signal.stop_loss else "None"
                    tp_str = f"{signal.take_profit:.4f}" if signal.take_profit else "None"
                    tp_sl_info = f" | SL={sl_str}, TP={tp_str}"

                logger.info(
                    f"✅ Order placed: {signal.symbol} {order_side} {signal.amount:.4f} "
                    f"(pacifica_id={pacifica_order_id}){tp_sl_info}"
                )

                # Attach TP/SL to position using Pacifica's set_position_tpsl endpoint
                if not is_closing and pacifica_order_id and (signal.stop_loss or signal.take_profit):
                    sl_str = f"{signal.stop_loss:.4f}" if signal.stop_loss else "None"
                    tp_str = f"{signal.take_profit:.4f}" if signal.take_profit else "None"
                    logger.info(
                        f"🛡️  TP/SL included in order: {signal.symbol} "
                        f"SL={sl_str}, TP={tp_str}"
                    )

                    # Wait a moment for order to fill (market orders are fast)
                    import asyncio
                    await asyncio.sleep(2)

                    try:
                        # Attach TP/SL to the position (not just the order)
                        tpsl_response = await self.pacifica_client.set_position_tpsl(
                            symbol=signal.symbol,
                            side=order_side,  # 'bid' or 'ask'
                            stop_loss=signal.stop_loss,
                            take_profit=signal.take_profit,
                        )

                        if tpsl_response.get('success'):
                            logger.info(
                                f"✅ TP/SL successfully attached to {signal.symbol} position: "
                                f"SL={sl_str}, TP={tp_str}"
                            )
                        else:
                            logger.warning(
                                f"⚠️  TP/SL attachment failed for {signal.symbol}: "
                                f"{tpsl_response.get('error', 'Unknown error')}"
                            )
                    except Exception as tpsl_error:
                        logger.error(
                            f"❌ Error attaching TP/SL to {signal.symbol} position: {tpsl_error}"
                        )

                # Save to database
                try:
                    async with AsyncSessionLocal() as session:
                        order = Order(
                            order_id=str(pacifica_order_id) if pacifica_order_id else f"failed-{client_order_id}",
                            client_order_id=client_order_id,
                            strategy_id=self.strategy_id,
                            symbol=signal.symbol,
                            side=order_side,
                            order_type="market",
                            amount=rounded_amount,
                            price=signal.price,
                            filled_amount=0.0,
                            status="submitted" if pacifica_order_id else "failed",
                            metadata={
                                "signal_type": signal.signal_type.value,
                                "confidence": signal.confidence,
                                **signal.metadata,
                            },
                            created_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                        )
                        session.add(order)
                        await session.commit()
                        logger.info(f"💾 Order saved to database: {client_order_id}")

                        # Create position if order was successful and not closing
                        if pacifica_order_id and not is_closing:
                            # Check if position already exists
                            from sqlalchemy import select
                            result = await session.execute(
                                select(Position).where(
                                    Position.strategy_id == self.strategy_id,
                                    Position.symbol == signal.symbol
                                )
                            )
                            existing_position = result.scalar_one_or_none()

                            if existing_position:
                                # Update existing position
                                logger.info(f"Updating existing position for {signal.symbol}")
                            else:
                                # Create new position
                                position = Position(
                                    strategy_id=self.strategy_id,
                                    symbol=signal.symbol,
                                    side=order_side,
                                    amount=rounded_amount,
                                    entry_price=signal.price,
                                    current_price=signal.price,
                                    unrealized_pnl=0.0,
                                    realized_pnl=0.0,
                                    opened_at=datetime.utcnow(),
                                    updated_at=datetime.utcnow(),
                                    metadata={
                                        "order_id": str(pacifica_order_id),
                                        "signal_confidence": signal.confidence,
                                    }
                                )
                                session.add(position)
                                await session.commit()
                                logger.info(f"📊 Position created: {signal.symbol} {order_side} {rounded_amount}")

                except Exception as db_error:
                    logger.error(f"Failed to save order/position to DB: {db_error}")

                return client_order_id

            except Exception as api_error:
                logger.error(f"Pacifica API error: {api_error}")
                return None
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            return None

    async def sync_positions_from_pacifica(self) -> None:
        """Sync positions from Pacifica API to match actual exchange state"""

        if not self.pacifica_client:
            logger.debug("Pacifica client not available, skipping position sync")
            return

        if not getattr(self.pacifica_client, "keypair", None):
            logger.debug(
                "Pacifica agent wallet keypair not set (PACIFICA_AGENT_WALLET_PRIVKEY). "
                "Skipping position sync. Set the keypair in .env for live trading."
            )
            return

        try:
            # Get positions from Pacifica
            response = await self.pacifica_client.get_positions()

            # Handle Pacifica response format: {"success": true, "data": [...]}
            pacifica_positions = []
            if isinstance(response, dict):
                if response.get('success') and response.get('data') is not None:
                    pacifica_positions = response['data']
            elif isinstance(response, list):
                pacifica_positions = response

            async with AsyncSessionLocal() as session:
                from sqlalchemy import select, delete

                # Get all our current positions
                result = await session.execute(
                    select(Position).where(
                        Position.strategy_id == self.strategy_id
                    )
                )
                db_positions = result.scalars().all()

                # Create set of symbols from Pacifica (active positions)
                pacifica_symbols = {p.get('symbol') for p in pacifica_positions if float(p.get('amount', 0)) > 0}

                # Delete positions that no longer exist on Pacifica
                deleted_count = 0
                for db_pos in db_positions:
                    if db_pos.symbol not in pacifica_symbols:
                        logger.info(
                            f"🗑️  Removing closed position from database: {db_pos.symbol} "
                            f"({db_pos.amount} @ ${db_pos.entry_price:.4f})"
                        )
                        await session.delete(db_pos)
                        deleted_count += 1

                # Update or create positions from Pacifica
                updated_count = 0
                created_count = 0
                for pac_pos in pacifica_positions:
                    symbol = pac_pos.get('symbol')
                    side = pac_pos.get('side')
                    amount = float(pac_pos.get('amount', 0))
                    entry_price = float(pac_pos.get('entry_price', 0))

                    if amount == 0:
                        continue

                    # Check if we have this position in our database
                    result = await session.execute(
                        select(Position).where(
                            Position.strategy_id == self.strategy_id,
                            Position.symbol == symbol
                        )
                    )
                    existing_position = result.scalar_one_or_none()

                    if existing_position:
                        # Update with Pacifica data (source of truth)
                        existing_position.side = side
                        existing_position.amount = amount
                        existing_position.entry_price = entry_price
                        existing_position.updated_at = datetime.utcnow()
                        logger.debug(
                            f"Updated {symbol} position from Pacifica: "
                            f"{amount} @ ${entry_price:.4f}"
                        )
                        updated_count += 1
                    else:
                        # Create new position from Pacifica
                        new_position = Position(
                            strategy_id=self.strategy_id,
                            symbol=symbol,
                            side=side,
                            amount=amount,
                            entry_price=entry_price,
                            current_price=entry_price,
                            unrealized_pnl=0.0,
                            realized_pnl=0.0,
                            opened_at=datetime.utcnow(),
                            updated_at=datetime.utcnow(),
                            metadata={"synced_from_pacifica": True}
                        )
                        session.add(new_position)
                        logger.info(
                            f"✅ Created {symbol} position from Pacifica: "
                            f"{amount} @ ${entry_price:.4f}"
                        )
                        created_count += 1

                await session.commit()
                logger.info(
                    f"Position sync complete: {len(pacifica_positions)} active, "
                    f"{updated_count} updated, {created_count} created, {deleted_count} deleted"
                )

        except Exception as e:
            logger.error(f"Error syncing positions from Pacifica: {e}")

    async def update_positions(self) -> None:
        """Update all open positions with current prices and P&L"""

        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select

                # Get all open positions for this strategy
                query = select(Position).where(
                    Position.strategy_id == self.strategy_id
                )
                result = await session.execute(query)
                positions = result.scalars().all()

                if not positions:
                    logger.debug("No open positions to update")
                    return

                for position in positions:
                    try:
                        # Get current market price
                        market_data = await self.get_market_data(position.symbol)
                        if not market_data:
                            logger.debug(f"No market data for {position.symbol}, skipping P&L update")
                            continue

                        current_price = market_data.get('price', 0)
                        if current_price <= 0:
                            continue

                        # Calculate P&L based on position side
                        # For short positions (ask): profit when price goes down
                        # For long positions (bid): profit when price goes up
                        if position.side == 'ask':
                            # Short position: (entry_price - current_price) * amount
                            unrealized_pnl = (position.entry_price - current_price) * position.amount
                        else:
                            # Long position: (current_price - entry_price) * amount
                            unrealized_pnl = (current_price - position.entry_price) * position.amount

                        # Update position
                        position.current_price = current_price
                        position.unrealized_pnl = unrealized_pnl
                        position.updated_at = datetime.utcnow()

                        logger.debug(
                            f"Updated {position.symbol} position: "
                            f"entry=${position.entry_price:.4f}, current=${current_price:.4f}, "
                            f"pnl=${unrealized_pnl:.2f}"
                        )

                    except Exception as e:
                        logger.error(f"Error updating position {position.symbol}: {e}")
                        continue

                await session.commit()
                logger.info(f"Updated {len(positions)} position(s)")

        except Exception as e:
            logger.error(f"Error in update_positions: {e}")

    async def process_signals(self) -> None:
        """Process all strategies and generate orders"""

        # 1. Detect market regime
        regime = await self.regime_detector.detect_regime()
        logger.info(f"Market Regime Detected: {regime.value}")

        # 2. Process momentum strategies
        for strategy_id, strategy in self.momentum_strategies.items():
            try:
                market_data = await self.get_market_data(strategy.symbol)
                if not market_data:
                    continue

                current_position = self.exposure_manager.positions.get(strategy.symbol)
                signal = await strategy.generate_signal(market_data, current_position)

                if signal:
                    order_id = await self.create_order(signal)
                    if order_id:
                        self.exposure_manager.update_position(signal.symbol, signal.signal_type.value, signal.amount, signal.price)
                        self.risk_manager.record_trade(strategy.symbol)

            except Exception as e:
                logger.error(f"Error processing momentum strategy {strategy_id}: {e}")

        # 3. Evaluate need for hedges
        exposure_state = self.exposure_manager.get_exposure_state()
        hedge_action = self.hedge_trigger.evaluate(exposure_state)
        hedge_action = self.hedge_trigger.add_circuit_breakers(hedge_action)

        # 4. Process hedge strategies if needed
        if hedge_action == HedgeAction.ACTIVATE_MR_LONGS:
            for strategy_id, strategy in self.mr_long_hedge_strategies.items():
                try:
                    market_data = await self.get_market_data(strategy.symbol)
                    if not market_data: continue
                    
                    current_position = self.exposure_manager.positions.get(strategy.symbol)
                    signal = await strategy.generate_signal(market_data, current_position)

                    if signal:
                        order_id = await self.create_order(signal)
                        if order_id:
                            self.exposure_manager.update_position(signal.symbol, signal.signal_type.value, signal.amount, signal.price)
                
                except Exception as e:
                    logger.error(f"Error processing MR Long Hedge strategy {strategy_id}: {e}")

        elif hedge_action == HedgeAction.ACTIVATE_MR_SHORTS:
            for strategy_id, strategy in self.mr_short_hedge_strategies.items():
                try:
                    market_data = await self.get_market_data(strategy.symbol)
                    if not market_data: continue

                    current_position = self.exposure_manager.positions.get(strategy.symbol)
                    signal = await strategy.generate_signal(market_data, current_position)

                    if signal:
                        order_id = await self.create_order(signal)
                        if order_id:
                            self.exposure_manager.update_position(signal.symbol, signal.signal_type.value, signal.amount, signal.price)
                
                except Exception as e:
                    logger.error(f"Error processing MR Short Hedge strategy {strategy_id}: {e}")
    
    async def run_signal_loop(self) -> None:
        """Main signal generation loop"""

        logger.info("Starting signal generation loop (60s interval)...")

        while self.running:
            try:
                # Reload OpenClaw Agent strategy overrides (if AGENT_OVERRIDES_PATH set)
                if settings.reload_agent_overrides():
                    logger.debug("Reloaded OpenClaw Agent strategy overrides")

                # Sync positions from Pacifica (source of truth)
                await self.sync_positions_from_pacifica()

                # Update positions with current prices and P&L
                await self.update_positions()

                # Process trading signals
                logger.info("Processing signals for all strategies...")
                await self.process_signals()
                logger.info("Signal processing complete. Sleeping for 60s...")
                await asyncio.sleep(60)  # Check every minute

            except Exception as e:
                logger.error(f"Error in signal loop: {e}")
                await asyncio.sleep(10)

    async def run(self) -> None:
        """Main service entry point"""

        logger.info("Starting Trading Engine...")
        logger.info(f"Strategy ID: {self.strategy_id}")
        logger.info(f"Paper Trading: {self.paper_trading}")
        logger.info(f"Portfolio Value: ${self.portfolio_value:,.0f}")

        await self.connect()

        # Initialize strategies
        self.initialize_strategies()

        # Sync positions from Pacifica on startup
        logger.info("Syncing positions from Pacifica...")
        await self.sync_positions_from_pacifica()

        self.running = True

        # Start signal generation loop
        signal_task = asyncio.create_task(self.run_signal_loop())

        try:
            await signal_task
        except KeyboardInterrupt:
            logger.info("Shutting down Trading Engine...")
        finally:
            self.running = False
            signal_task.cancel()
            await self.disconnect()


async def run_trading_engine():
    """Entry point for Trading Engine Service"""

    import os
    from nexwave.common.logger import setup_logging

    setup_logging(level=settings.log_level)

    engine = TradingEngine(
        strategy_id=os.getenv("STRATEGY_ID", "vwm_momentum_1"),
        paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
        portfolio_value=float(os.getenv("PORTFOLIO_VALUE", "100000")),
    )

    await engine.run()


if __name__ == "__main__":
    asyncio.run(run_trading_engine())