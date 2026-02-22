#!/usr/bin/env python3
"""Script to close all open positions on Pacifica DEX"""

import asyncio
import sys
from src.nexwave.services.order_management.pacifica_client import PacificaClient
from src.nexwave.common.logger import logger


async def close_all_positions():
    """Close all open positions"""

    # Initialize Pacifica client
    client = PacificaClient()

    if not client.keypair:
        logger.error("Keypair not initialized. Cannot close positions.")
        return False

    try:
        # Get current positions
        logger.info("Fetching current positions...")
        positions_response = await client.get_positions()

        # Handle different response formats
        if isinstance(positions_response, dict):
            positions = positions_response.get('data', []) or positions_response.get('positions', [])
        else:
            positions = positions_response

        if not positions:
            logger.info("No open positions to close.")
            return True

        logger.info(f"Found {len(positions)} open positions:")
        for pos in positions:
            symbol = pos.get('symbol')
            side = pos.get('side')
            amount = pos.get('amount')
            pnl = pos.get('unrealized_pnl', 0)
            logger.info(f"  - {symbol}: {side} {amount} (P&L: ${pnl:.2f})")

        # Close each position
        results = []
        for pos in positions:
            symbol = pos['symbol']
            side = pos['side']
            amount = float(pos['amount'])

            # To close a position, we create an order on the opposite side with reduce_only=True
            # For ASK (short) positions, we close with BID (buy)
            # For BID (long) positions, we close with ASK (sell)
            close_side = 'bid' if side.upper() == 'ASK' else 'ask'

            logger.info(f"Closing {symbol} position: {side} {amount} → placing {close_side} order...")

            try:
                result = await client.create_market_order(
                    symbol=symbol,
                    side=close_side,
                    amount=amount,
                    reduce_only=True,  # Critical: only close existing position
                    slippage_percent=1.0  # Allow 1% slippage for market close
                )

                order_id = result.get('data', {}).get('order_id') if isinstance(result.get('data'), dict) else result.get('order_id')
                logger.info(f"  ✅ {symbol} closed (order_id={order_id})")
                results.append((symbol, True, order_id))

            except Exception as e:
                logger.error(f"  ❌ Failed to close {symbol}: {str(e)}")
                results.append((symbol, False, str(e)))

        # Summary
        successful = [r for r in results if r[1]]
        failed = [r for r in results if not r[1]]

        logger.info("\n" + "="*60)
        logger.info(f"SUMMARY: {len(successful)}/{len(positions)} positions closed")

        if successful:
            logger.info("\nSuccessfully closed:")
            for symbol, _, order_id in successful:
                logger.info(f"  ✅ {symbol} (order_id={order_id})")

        if failed:
            logger.warning("\nFailed to close:")
            for symbol, _, error in failed:
                logger.warning(f"  ❌ {symbol}: {error}")

        logger.info("="*60)

        return len(failed) == 0

    except Exception as e:
        logger.error(f"Error closing positions: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    logger.info("="*60)
    logger.info("NEXWAVE POSITION CLOSER")
    logger.info("="*60)

    success = asyncio.run(close_all_positions())

    sys.exit(0 if success else 1)
