"""Test Volume-Weighted Momentum Strategy"""

import asyncio
from src.nexwave.strategies.volume_weighted_momentum_strategy import VolumeWeightedMomentumStrategy
from src.nexwave.common.logger import logger


async def test_vwm_strategy():
    """Test VWM strategy with real market data"""

    # Initialize strategy for BTC
    strategy = VolumeWeightedMomentumStrategy(
        strategy_id="vwm_test_1",
        symbol="BTC",
        portfolio_value=100000.0,
        paper_trading=True,
        lookback_period=20,
        momentum_threshold=0.002,  # 0.2%
        volume_multiplier=1.5,
        timeframe="15m"
    )

    logger.info("Testing Volume-Weighted Momentum Strategy for BTC...")

    # Simulate market data (in real usage, this comes from live feed)
    market_data = {
        "price": 103000.0,  # Current BTC price
        "timestamp": "2025-11-07T19:00:00Z"
    }

    # Generate signal
    signal = await strategy.generate_signal(market_data, current_position=None)

    if signal:
        logger.info(f"Signal Generated: {signal.signal_type.value}")
        logger.info(f"Price: ${signal.price:,.2f}")
        logger.info(f"Amount: {signal.amount:.6f}")
        logger.info(f"Confidence: {signal.confidence:.2%}")
        logger.info(f"Stop Loss: ${signal.stop_loss:,.2f}")
        logger.info(f"Take Profit: ${signal.take_profit:,.2f}")
        logger.info(f"Metadata: {signal.metadata}")

        # Calculate metrics
        if signal.stop_loss and signal.take_profit:
            risk = abs(signal.price - signal.stop_loss)
            reward = abs(signal.take_profit - signal.price)
            risk_reward = reward / risk if risk > 0 else 0
            logger.info(f"Risk/Reward Ratio: {risk_reward:.2f}")
    else:
        logger.info("No signal generated (waiting for momentum confirmation)")

    logger.info("\n" + "="*60)
    logger.info("Strategy Configuration:")
    logger.info(f"  Lookback Period: {strategy.lookback_period} candles")
    logger.info(f"  Momentum Threshold: {strategy.momentum_threshold:.2%}")
    logger.info(f"  Volume Multiplier: {strategy.volume_multiplier}x")
    logger.info(f"  Timeframe: {strategy.timeframe}")
    logger.info(f"  Position Size: {strategy.base_position_pct}%-{strategy.max_position_pct}%")
    logger.info("="*60)


if __name__ == "__main__":
    asyncio.run(test_vwm_strategy())
