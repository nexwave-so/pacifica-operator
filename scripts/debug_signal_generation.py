#!/usr/bin/env python3
"""Debug script to check why signals aren't being generated"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Set environment variables
os.environ.setdefault("STRATEGY_ID", "vwm_momentum_1")
os.environ.setdefault("PAPER_TRADING", "true")
os.environ.setdefault("PORTFOLIO_VALUE", "159")

from nexwave.services.trading_engine.engine import TradingEngine
from nexwave.common.logger import setup_logging, logger

setup_logging(level="INFO")


async def debug_signal_generation():
    """Debug signal generation for one symbol"""
    
    engine = TradingEngine(
        strategy_id=os.getenv("STRATEGY_ID", "vwm_momentum_1"),
        paper_trading=True,
        portfolio_value=float(os.getenv("PORTFOLIO_VALUE", "159")),
    )
    
    await engine.connect()
    engine.initialize_strategies()
    
    # Test with first symbol
    if not engine.strategies:
        logger.error("No strategies initialized!")
        return
    
    symbol = list(engine.strategies.keys())[0]
    strategy = engine.strategies[symbol]
    
    logger.info(f"Testing signal generation for {symbol}...")
    
    # Get market data
    market_data = await engine.get_market_data(symbol)
    if not market_data:
        logger.error(f"❌ No market data available for {symbol}")
        logger.info("This is likely the blocking issue - market data is not available")
        return
    
    logger.info(f"✅ Market data retrieved: price=${market_data.get('price', 0):.2f}")
    
    # Get current position
    current_position = await engine.get_current_position(symbol)
    if current_position:
        logger.info(f"Current position: {current_position}")
    else:
        logger.info("No current position")
    
    # Get candles
    candles = await strategy.get_candles()
    logger.info(f"Candles available: {len(candles)} (need {strategy.lookback_period})")
    
    if len(candles) < strategy.lookback_period:
        logger.error(f"❌ Not enough candles: {len(candles)} < {strategy.lookback_period}")
        logger.info("This is likely the blocking issue - insufficient candle data")
        return
    
    # Calculate metrics
    metrics = strategy.calculate_volume_weighted_momentum(candles)
    logger.info(f"VWM: {metrics['vwm']:.6f}")
    logger.info(f"Volume Ratio: {metrics['volume_ratio']:.2f} (need {strategy.volume_multiplier}x)")
    logger.info(f"Momentum Threshold: {strategy.momentum_threshold}")
    logger.info(f"ATR: {metrics['atr']:.2f}")
    
    # Check conditions
    volume_confirmed = metrics['volume_ratio'] >= strategy.volume_multiplier
    vwm_above_threshold = metrics['vwm'] > strategy.momentum_threshold
    vwm_below_threshold = metrics['vwm'] < -strategy.momentum_threshold
    
    logger.info(f"\nEntry Conditions:")
    logger.info(f"  Volume confirmed: {volume_confirmed} (ratio={metrics['volume_ratio']:.2f} >= {strategy.volume_multiplier})")
    logger.info(f"  VWM > threshold: {vwm_above_threshold} ({metrics['vwm']:.6f} > {strategy.momentum_threshold})")
    logger.info(f"  VWM < -threshold: {vwm_below_threshold} ({metrics['vwm']:.6f} < -{strategy.momentum_threshold})")
    
    # Try to generate signal
    signal = await strategy.generate_signal(market_data, current_position)
    
    if signal:
        logger.info(f"✅ Signal generated: {signal.signal_type.value}")
        logger.info(f"  Amount: {signal.amount:.6f}, Price: ${signal.price:.2f}")
        logger.info(f"  Stop Loss: ${signal.stop_loss:.2f if signal.stop_loss else 'None'}")
        logger.info(f"  Take Profit: ${signal.take_profit:.2f if signal.take_profit else 'None'}")
    else:
        logger.warning("❌ No signal generated")
        logger.info("Reasons could be:")
        logger.info("  1. VWM not above/below threshold")
        logger.info("  2. Volume not confirmed")
        logger.info("  3. Already in position and exit conditions not met")
    
    await engine.disconnect()


if __name__ == "__main__":
    asyncio.run(debug_signal_generation())

