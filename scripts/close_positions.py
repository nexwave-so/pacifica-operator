#!/usr/bin/env python3
"""
Close all open positions without TP/SL
Run this script to close positions before the TP/SL fix takes effect
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from nexwave.services.order_management.pacifica_client import PacificaClient
from nexwave.common.logger import logger


async def close_all_positions():
    """Close all open positions on Pacifica"""

    logger.info("=" * 60)
    logger.info("CLOSING ALL OPEN POSITIONS")
    logger.info("=" * 60)

    # Initialize Pacifica client
    client = PacificaClient()

    # Get current positions
    logger.info("Fetching current positions from Pacifica...")
    try:
        positions = await client.get_positions()

        # Handle different response formats
        if isinstance(positions, dict) and 'data' in positions:
            positions_list = positions['data']
        elif isinstance(positions, list):
            positions_list = positions
        else:
            logger.error(f"Unexpected positions format: {type(positions)}")
            return

        if not positions_list:
            logger.info("✅ No open positions found. Nothing to close.")
            return

        logger.info(f"Found {len(positions_list)} open position(s):")
        for pos in positions_list:
            symbol = pos.get('symbol')
            side = pos.get('side')
            amount = float(pos.get('amount', 0))
            entry_price = float(pos.get('entry_price', 0))

            if amount == 0:
                continue

            logger.info(f"  - {symbol}: {side} {amount} @ ${entry_price:.4f}")

        # Confirm before closing
        logger.warning("")
        logger.warning("⚠️  This will close ALL positions with market orders")
        logger.warning("⚠️  Positions will be closed at current market price")
        logger.warning("")

        # Close each position
        for pos in positions_list:
            symbol = pos.get('symbol')
            side = pos.get('side')
            amount = float(pos.get('amount', 0))

            if amount == 0:
                logger.debug(f"Skipping {symbol} (zero amount)")
                continue

            # Determine closing side (opposite of position side)
            # If position is "bid" (long), we need to "ask" (sell) to close
            # If position is "ask" (short), we need to "bid" (buy) to close
            close_side = "ask" if side.lower() == "bid" else "bid"

            logger.info(f"Closing {symbol} {side} position: {amount} units")

            try:
                response = await client.create_market_order(
                    symbol=symbol,
                    side=close_side,
                    amount=amount,
                    reduce_only=True,  # Critical: this ensures we only close, not open new
                    slippage_percent=0.5
                )

                if response.get('success'):
                    order_id = response.get('data', {}).get('order_id')
                    logger.info(f"✅ Closed {symbol}: order_id={order_id}")
                else:
                    logger.error(f"❌ Failed to close {symbol}: {response}")

                # Small delay between orders
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.error(f"❌ Error closing {symbol}: {e}")

        logger.info("")
        logger.info("=" * 60)
        logger.info("Position closing complete")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Failed to fetch or close positions: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(close_all_positions())
