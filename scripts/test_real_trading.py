#!/usr/bin/env python3
"""
Test real trading on Pacifica DEX
This script tests the complete order placement flow with actual wallet
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nexwave.common.config import settings
from nexwave.common.logger import logger, setup_logging
from nexwave.services.order_management.pacifica_client import PacificaClient
from nexwave.services.order_management.service import OrderManagementService
from nexwave.common.pairs import get_pair_by_symbol


async def test_wallet_connection():
    """Test wallet connection and get positions"""
    print("\n" + "="*60)
    print("TEST 1: Wallet Connection & Balance Check")
    print("="*60)
    
    try:
        client = PacificaClient()
        
        if not client.keypair:
            print("❌ FAILED: Keypair not initialized")
            print("   → Check PACIFICA_AGENT_WALLET_PRIVKEY in .env")
            return False
        
        pubkey = str(client.keypair.pubkey())
        print(f"✅ Wallet initialized: {pubkey}")
        
        # Try to get positions (this will show if we have funds)
        try:
            positions = await client.get_positions()
            print(f"✅ Successfully connected to Pacifica API")
            print(f"   → Current positions: {len(positions)}")
            
            if positions:
                print("\n   Open Positions:")
                for pos in positions:
                    print(f"     - {pos.get('symbol', 'N/A')}: {pos.get('side', 'N/A')} "
                          f"{pos.get('amount', 0)} @ ${pos.get('entry_price', 0):.2f}")
            else:
                print("   → No open positions")
            
            return True
            
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch positions: {e}")
            print("   → This might be expected if account has no positions")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_order_placement(symbol="SOL", amount=0.1, side="bid"):
    """Test placing a small real order"""
    print("\n" + "="*60)
    print("TEST 2: Real Order Placement")
    print("="*60)
    
    # Check paper trading mode
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    
    if paper_trading:
        print("⚠️  WARNING: System is in PAPER TRADING mode")
        print("   → Set PAPER_TRADING=false in .env to enable real trading")
        print("   → This test will be simulated, not real")
    else:
        print("✅ REAL TRADING MODE ENABLED")
        print("   → Orders will be placed on Pacifica DEX")
    
    # Validate pair
    pair = get_pair_by_symbol(symbol)
    if not pair:
        print(f"❌ Symbol '{symbol}' not found")
        return False
    
    if amount < pair.min_order_size:
        print(f"❌ Amount {amount} is below minimum {pair.min_order_size}")
        return False
    
    print(f"\n📋 Order Details:")
    print(f"   Symbol: {symbol}")
    print(f"   Side: {side} ({'BUY' if side == 'bid' else 'SELL'})")
    print(f"   Amount: {amount}")
    print(f"   Type: market")
    print(f"   Min Order Size: {pair.min_order_size}")
    print(f"   Max Leverage: {pair.max_leverage}x")
    
    try:
        service = OrderManagementService(paper_trading=paper_trading)
        
        import uuid
        order_request = {
            "strategy_id": "test_trading",
            "symbol": symbol.upper(),
            "side": side.lower(),
            "order_type": "market",
            "amount": amount,
            "price": None,
            "reduce_only": False,
            "client_order_id": f"test-{uuid.uuid4()}",
            "paper_trading": paper_trading,
            "metadata": {
                "source": "test_real_trading",
                "test": True,
            },
        }
        
        print(f"\n📤 Placing order...")
        order_id = await service.create_order(order_request)
        
        if order_id:
            print(f"\n✅ Order placed successfully!")
            print(f"   Order ID: {order_id}")
            
            if paper_trading:
                print("\n📝 Note: This was a PAPER TRADING order (simulated)")
            else:
                print("\n🎉 REAL ORDER PLACED ON PACIFICA DEX!")
                print("   → Check your positions on Pacifica DEX")
            
            return True
        else:
            print("\n❌ Order placement failed (returned None)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_system_readiness():
    """Check if system is ready for trading"""
    print("\n" + "="*60)
    print("TEST 0: System Readiness Check")
    print("="*60)
    
    checks = []
    
    # Check environment
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    print(f"📝 Paper Trading: {paper_trading}")
    if paper_trading:
        print("   ⚠️  Set PAPER_TRADING=false for real trading")
    else:
        print("   ✅ Real trading enabled")
        checks.append(True)
    
    # Check credentials
    print(f"\n🔑 Credentials:")
    has_privkey = bool(settings.pacifica_agent_wallet_privkey and 
                      settings.pacifica_agent_wallet_privkey.strip() and
                      settings.pacifica_agent_wallet_privkey != "your_agent_wallet_private_key")
    print(f"   Private Key: {'✅ Set' if has_privkey else '❌ Not set'}")
    print(f"   Public Key: {'✅ Set' if settings.pacifica_agent_wallet_pubkey else '❌ Not set'}")
    print(f"   API Key: {'✅ Set' if settings.pacifica_api_key else '❌ Not set'}")
    
    if has_privkey and settings.pacifica_agent_wallet_pubkey:
        checks.append(True)
    else:
        checks.append(False)
    
    # Check API URL
    print(f"\n🌐 API Configuration:")
    print(f"   API URL: {settings.pacifica_api_url}")
    print(f"   WS URL: {settings.pacifica_ws_url}")
    checks.append(True)
    
    return all(checks)


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("NEXWAVE REAL TRADING TEST")
    print("="*60)
    print("\n⚠️  WARNING: This will test REAL order placement")
    print("   Make sure you want to proceed with real trading!")
    
    setup_logging(level="INFO")
    
    # Check if user wants to proceed
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    if not paper_trading:
        print("\n⚠️  REAL TRADING MODE DETECTED")
        response = input("Continue with real trading test? (yes/no): ")
        if response.lower() != "yes":
            print("Test cancelled.")
            return 0
    
    results = []
    
    # Run tests
    results.append(("System Readiness", await test_system_readiness()))
    results.append(("Wallet Connection", await test_wallet_connection()))
    
    # Only test order placement if system is ready
    if all(r[1] for r in results):
        print("\n" + "="*60)
        print("Ready for order placement test")
        print("="*60)
        
        # Ask for order details
        symbol = input("\nEnter symbol to test (BTC/ETH/SOL, default: SOL): ").strip().upper() or "SOL"
        amount_input = input("Enter amount (default: 0.1): ").strip() or "0.1"
        try:
            amount = float(amount_input)
        except ValueError:
            amount = 0.1
        
        side = input("Enter side (bid/ask, default: bid): ").strip().lower() or "bid"
        
        results.append(("Order Placement", await test_order_placement(symbol, amount, side)))
    else:
        print("\n⚠️  System not ready for order placement")
        results.append(("Order Placement", False))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed! System is ready for trading.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

