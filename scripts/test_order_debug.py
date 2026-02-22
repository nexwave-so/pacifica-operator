#!/usr/bin/env python3
"""
Debug script to test order placement directly
"""

import asyncio
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.nexwave.common.logger import setup_logging, logger
from src.nexwave.services.order_management.pacifica_client import PacificaClient


async def test_order_placement():
    """Test order placement with detailed logging"""
    setup_logging(level="DEBUG")

    print("\n" + "="*70)
    print("ORDER PLACEMENT DEBUG TEST")
    print("="*70)

    # Check environment
    print("\n1. Environment Check:")
    print(f"   API URL: {os.getenv('PACIFICA_API_URL')}")
    print(f"   API Key: {'✅ Set' if os.getenv('PACIFICA_API_KEY') else '❌ Not set'}")
    print(f"   Wallet PubKey: {os.getenv('PACIFICA_AGENT_WALLET_PUBKEY')}")
    print(f"   Wallet PrivKey: {'✅ Set' if os.getenv('PACIFICA_AGENT_WALLET_PRIVKEY') else '❌ Not set'}")
    print(f"   Paper Trading: {os.getenv('PAPER_TRADING', 'true')}")

    # Initialize client
    print("\n2. Initializing Pacifica Client...")
    try:
        client = PacificaClient()
        if not client.keypair:
            print("   ❌ Keypair not initialized!")
            return False

        print(f"   ✅ Wallet initialized: {client.keypair.pubkey()}")
    except Exception as e:
        print(f"   ❌ Failed to initialize client: {e}")
        return False

    # Test API connectivity - get positions
    print("\n3. Testing API Connectivity (GET positions)...")
    try:
        positions = await client.get_positions()
        print(f"   ✅ Successfully connected to Pacifica API")
        print(f"   → Open positions: {len(positions)}")

        if positions:
            for pos in positions:
                print(f"     • {pos.get('symbol')}: {pos.get('side')} "
                      f"{pos.get('amount', 0)} @ ${pos.get('entry_price', 0):.2f}")
    except Exception as e:
        print(f"   ⚠️  Could not fetch positions: {e}")
        logger.exception("Position fetch error:")
        print("   → Continuing with order placement test...")

    # Test order placement
    print("\n4. Testing Order Placement (Small BTC Market Order)...")
    print("   Symbol: BTC")
    print("   Side: bid (BUY)")
    print("   Amount: 0.0001 BTC (~$10)")
    print("   Type: market")

    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    if not paper_trading:
        print("\n   ⚠️  WARNING: Paper trading is DISABLED!")
        print("   → This will place a REAL order on Pacifica DEX")
        response = input("   → Continue? (yes/no): ")
        if response.lower() != "yes":
            print("   → Order placement cancelled")
            return False

    try:
        result = await client.create_market_order(
            symbol="BTC",
            side="bid",
            amount=0.0001,
            reduce_only=False,
            slippage_percent=0.5,
        )

        print(f"\n   ✅ Order placed successfully!")
        print(f"   → Order ID: {result.get('order_id')}")
        print(f"   → Status: {result.get('status')}")
        print(f"   → Full response: {result}")

        return True

    except Exception as e:
        print(f"\n   ❌ Order placement failed!")
        print(f"   → Error: {e}")
        logger.exception("Order placement error:")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_order_placement())
    sys.exit(0 if success else 1)
