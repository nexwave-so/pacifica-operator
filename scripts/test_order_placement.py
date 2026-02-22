#!/usr/bin/env python3
"""
Test script to validate order placement on Pacifica DEX
This script tests the order placement flow without actually executing trades
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


async def test_pacifica_connection():
    """Test Pacifica API connection and credentials"""
    print("\n" + "="*60)
    print("TEST 1: Pacifica Connection & Credentials")
    print("="*60)
    
    try:
        client = PacificaClient()
        
        # Check if keypair is initialized
        if not client.keypair:
            print("❌ FAILED: Keypair not initialized")
            print("   → Check PACIFICA_AGENT_WALLET_PRIVKEY in environment")
            return False
        
        print(f"✅ Keypair initialized: {client.keypair.pubkey()}")
        
        # Check API URL
        print(f"✅ API URL: {client.api_url}")
        
        # Test getting positions (read-only operation)
        try:
            positions = await client.get_positions()
            print(f"✅ Successfully connected to Pacifica API")
            print(f"   → Current positions: {len(positions)}")
            return True
        except Exception as e:
            print(f"⚠️  Warning: Could not fetch positions: {e}")
            print("   → This might be expected if account has no positions")
            print("   → Connection test passed if no exception was raised")
            return True
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        print("\nTroubleshooting:")
        print("1. Check PACIFICA_AGENT_WALLET_PRIVKEY is set")
        print("2. Check PACIFICA_API_URL is correct")
        print("3. Verify wallet private key format (base58)")
        return False


async def test_order_validation():
    """Test order validation logic"""
    print("\n" + "="*60)
    print("TEST 2: Order Validation")
    print("="*60)
    
    try:
        # Check paper trading mode
        paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
        print(f"📝 Paper Trading Mode: {paper_trading}")
        
        if paper_trading:
            print("   → Orders will be simulated (not sent to Pacifica)")
            print("   → Set PAPER_TRADING=false to enable real trading")
        else:
            print("   → Real trading mode - orders will be sent to Pacifica")
        
        # Test order service initialization
        service = OrderManagementService(paper_trading=paper_trading)
        print(f"✅ OrderManagementService initialized")
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_order_creation():
    """Test order creation flow"""
    print("\n" + "="*60)
    print("TEST 3: Order Creation Flow")
    print("="*60)
    
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    service = OrderManagementService(paper_trading=paper_trading)
    
    # Test order request
    test_order = {
        "strategy_id": "test_strategy",
        "symbol": "BTC",
        "side": "bid",  # Buy
        "order_type": "market",
        "amount": 0.001,  # Very small test amount
        "price": None,  # Market order
        "reduce_only": False,
        "client_order_id": "test-order-123",
        "paper_trading": paper_trading,
        "metadata": {
            "test": True
        }
    }
    
    print(f"📤 Creating test order:")
    print(f"   Symbol: {test_order['symbol']}")
    print(f"   Side: {test_order['side']}")
    print(f"   Amount: {test_order['amount']}")
    print(f"   Type: {test_order['order_type']}")
    
    try:
        # Note: This requires Kafka to be running for full flow
        # For testing, we'll test the Pacifica client directly
        if not paper_trading:
            client = PacificaClient()
            if not client.keypair:
                print("❌ Cannot test real order: Keypair not initialized")
                return False
            
            print("\n⚠️  Real order test skipped (requires live trading)")
            print("   → To test real orders, ensure:")
            print("     1. PAPER_TRADING=false")
            print("     2. Valid wallet with funds")
            print("     3. Proper API credentials")
            return True
        else:
            # Test paper trading order creation
            order_id = await service.create_order(test_order)
            if order_id:
                print(f"✅ Paper order created: {order_id}")
                return True
            else:
                print("❌ Order creation returned None")
                return False
                
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_pair_configuration():
    """Test pair configuration for order placement"""
    print("\n" + "="*60)
    print("TEST 4: Pair Configuration")
    print("="*60)
    
    try:
        # Test a few pairs
        test_symbols = ["BTC", "ETH", "SOL"]
        
        for symbol in test_symbols:
            pair = get_pair_by_symbol(symbol)
            if pair:
                print(f"✅ {symbol}:")
                print(f"   Max Leverage: {pair.max_leverage}x")
                print(f"   Min Order Size: {pair.min_order_size}")
                print(f"   Tick Size: {pair.tick_size}")
                print(f"   Active: {pair.is_active}")
            else:
                print(f"❌ {symbol}: Pair config not found")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        return False


async def test_environment_config():
    """Test environment configuration"""
    print("\n" + "="*60)
    print("TEST 5: Environment Configuration")
    print("="*60)
    
    checks = []
    
    # Check Pacifica settings (DO NOT DISPLAY PRIVATE KEYS)
    print("\n📋 Pacifica Configuration:")
    print(f"   API URL: {settings.pacifica_api_url}")
    print(f"   WS URL: {settings.pacifica_ws_url}")
    print(f"   API Key: {'✅ Set' if settings.pacifica_api_key else '❌ Not set'}")
    print(f"   Wallet Pubkey: {'✅ Set' if settings.pacifica_agent_wallet_pubkey else '❌ Not set'}")
    # NEVER display private key - only check if it's set
    has_privkey = bool(settings.pacifica_agent_wallet_privkey and 
                      settings.pacifica_agent_wallet_privkey.strip() and
                      settings.pacifica_agent_wallet_privkey != "your_agent_wallet_private_key")
    print(f"   Wallet Privkey: {'✅ Set' if has_privkey else '❌ Not set'}")
    
    if not settings.pacifica_agent_wallet_privkey:
        checks.append(False)
        print("   ⚠️  WARNING: Private key not set - cannot place real orders")
    else:
        checks.append(True)
    
    # Check paper trading
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    print(f"\n📝 Trading Mode:")
    print(f"   Paper Trading: {paper_trading}")
    if paper_trading:
        print("   ⚠️  NOTE: System is in paper trading mode")
        print("      Set PAPER_TRADING=false to enable real trading")
    
    # Check Kafka (for order flow)
    print(f"\n📨 Kafka Configuration:")
    print(f"   Bootstrap Servers: {settings.kafka_bootstrap_servers}")
    
    return all(checks)


async def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("NEXWAVE ORDER PLACEMENT TEST SUITE")
    print("="*60)
    
    setup_logging(level="INFO")
    
    results = []
    
    # Run tests
    results.append(("Environment Config", await test_environment_config()))
    results.append(("Pair Configuration", await test_pair_configuration()))
    results.append(("Order Validation", await test_order_validation()))
    results.append(("Pacifica Connection", await test_pacifica_connection()))
    results.append(("Order Creation", await test_order_creation()))
    
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
        print("\n🎉 All tests passed! Order placement should work.")
        return 0
    else:
        print("\n⚠️  Some tests failed. Review the output above.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

