#!/usr/bin/env python3
"""
Manually place a test order on Pacifica DEX
Useful for testing order placement without waiting for strategy signals
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
from nexwave.services.order_management.service import OrderManagementService
from nexwave.common.pairs import get_pair_by_symbol


async def place_test_order(
    symbol: str = "BTC",
    side: str = "bid",  # "bid" for buy, "ask" for sell
    amount: float = 0.001,
    order_type: str = "market",
    price: float = None,
    paper_trading: bool = None,
):
    """
    Place a test order
    
    Args:
        symbol: Trading symbol (e.g., "BTC", "ETH")
        side: "bid" (buy) or "ask" (sell)
        amount: Order amount in base currency
        order_type: "market" or "limit"
        price: Price for limit orders
        paper_trading: Override paper trading mode (None = use env var)
    """
    setup_logging(level="INFO")
    
    # Determine paper trading mode
    if paper_trading is None:
        paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    
    print("\n" + "="*60)
    print("PLACING TEST ORDER")
    print("="*60)
    print(f"Symbol: {symbol}")
    print(f"Side: {side} ({'BUY' if side == 'bid' else 'SELL'})")
    print(f"Amount: {amount}")
    print(f"Order Type: {order_type}")
    if order_type == "limit" and price:
        print(f"Price: ${price:,.2f}")
    print(f"Paper Trading: {paper_trading}")
    print("="*60 + "\n")
    
    # Validate pair
    pair = get_pair_by_symbol(symbol)
    if not pair:
        print(f"❌ Error: Symbol '{symbol}' not found in pair configuration")
        return False
    
    if not pair.is_active:
        print(f"❌ Error: Symbol '{symbol}' is not active")
        return False
    
    # Validate amount
    if amount < pair.min_order_size:
        print(f"❌ Error: Amount {amount} is below minimum order size {pair.min_order_size}")
        return False
    
    # Initialize service
    try:
        service = OrderManagementService(paper_trading=paper_trading)
        
        # Create order request
        import uuid
        order_request = {
            "strategy_id": "manual_test",
            "symbol": symbol.upper(),
            "side": side.lower(),
            "order_type": order_type.lower(),
            "amount": amount,
            "price": price,
            "reduce_only": False,
            "client_order_id": f"manual-{uuid.uuid4()}",
            "paper_trading": paper_trading,
            "metadata": {
                "source": "manual_test_script",
            },
        }
        
        # Place order
        print("📤 Placing order...")
        order_id = await service.create_order(order_request)
        
        if order_id:
            print(f"\n✅ Order placed successfully!")
            print(f"   Order ID: {order_id}")
            
            if paper_trading:
                print("\n📝 Note: This was a paper trading order (simulated)")
                print("   Set PAPER_TRADING=false to place real orders")
            else:
                print("\n⚠️  REAL ORDER PLACED ON PACIFICA DEX")
            
            return True
        else:
            print("\n❌ Order placement failed (returned None)")
            return False
            
    except Exception as e:
        print(f"\n❌ Error placing order: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Place a test order on Pacifica DEX")
    parser.add_argument("--symbol", default="BTC", help="Trading symbol (default: BTC)")
    parser.add_argument("--side", choices=["bid", "ask"], default="bid", help="Order side: bid (buy) or ask (sell)")
    parser.add_argument("--amount", type=float, default=0.001, help="Order amount (default: 0.001)")
    parser.add_argument("--type", choices=["market", "limit"], default="market", dest="order_type", help="Order type")
    parser.add_argument("--price", type=float, help="Price for limit orders")
    parser.add_argument("--paper", action="store_true", help="Force paper trading mode")
    parser.add_argument("--real", action="store_true", help="Force real trading mode (requires wallet)")
    
    args = parser.parse_args()
    
    # Determine paper trading mode
    paper_trading = None
    if args.paper:
        paper_trading = True
    elif args.real:
        paper_trading = False
    
    # Validate limit order
    if args.order_type == "limit" and not args.price:
        print("❌ Error: --price required for limit orders")
        return 1
    
    success = await place_test_order(
        symbol=args.symbol,
        side=args.side,
        amount=args.amount,
        order_type=args.order_type,
        price=args.price,
        paper_trading=paper_trading,
    )
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)

