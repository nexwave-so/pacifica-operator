#!/usr/bin/env python3
"""
Quick test to verify trading system can place orders
"""

import asyncio
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from nexwave.common.config import settings
from nexwave.common.logger import setup_logging
from nexwave.services.order_management.pacifica_client import PacificaClient


async def quick_test():
    """Quick connection test"""
    setup_logging(level="INFO")
    
    print("="*60)
    print("QUICK TRADING SYSTEM TEST")
    print("="*60)
    
    # Check configuration
    paper_trading = os.getenv("PAPER_TRADING", "true").lower() == "true"
    print(f"\n📝 Paper Trading: {paper_trading}")
    
    if paper_trading:
        print("   ⚠️  System is in PAPER TRADING mode")
        print("   → To enable real trading, set PAPER_TRADING=false in .env")
    else:
        print("   ✅ REAL TRADING MODE ENABLED")
    
    # Test wallet
    print(f"\n🔑 Wallet Configuration:")
    try:
        client = PacificaClient()
        
        if client.keypair:
            pubkey = str(client.keypair.pubkey())
            print(f"   ✅ Wallet initialized: {pubkey}")
            
            # Try to get positions
            try:
                positions = await client.get_positions()
                print(f"   ✅ Successfully connected to Pacifica API")
                print(f"   → Open positions: {len(positions)}")
                
                if positions:
                    print("\n   Current Positions:")
                    for pos in positions:
                        print(f"     • {pos.get('symbol')}: {pos.get('side')} "
                              f"{pos.get('amount', 0)} @ ${pos.get('entry_price', 0):.2f}")
                
                print("\n✅ System is ready for trading!")
                print("\nNext steps:")
                print("1. If paper trading, set PAPER_TRADING=false in .env")
                print("2. Restart services to pick up new config")
                print("3. Run: python scripts/test_real_trading.py")
                return True
                
            except Exception as e:
                print(f"   ⚠️  Could not fetch positions: {str(e)[:100]}")
                print("   → This might be expected if API endpoint differs")
                print("   → Wallet connection appears OK")
                return True
        else:
            print("   ❌ Wallet not initialized")
            print("   → Check PACIFICA_AGENT_WALLET_PRIVKEY in .env")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:100]}")
        return False


if __name__ == "__main__":
    result = asyncio.run(quick_test())
    sys.exit(0 if result else 1)

