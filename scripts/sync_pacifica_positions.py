#!/usr/bin/env python3
"""
Sync positions between Pacifica DEX and local database
Checks for discrepancies and offers to fix them
"""

import asyncio
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Position
from nexwave.services.order_management.pacifica_client import PacificaClient
from nexwave.common.logger import setup_logging, logger
from sqlalchemy import select, delete

setup_logging(level="INFO")


async def sync_positions():
    """Sync positions from Pacifica to database"""
    
    print("\n" + "="*80)
    print("PACIFICA <-> DATABASE POSITION SYNC")
    print("="*80)
    print()
    
    # Initialize Pacifica client
    try:
        pacifica = PacificaClient()
        logger.info("✅ Connected to Pacifica API")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Pacifica: {e}")
        return
    
    # Get positions from Pacifica
    try:
        response = await pacifica.get_positions()
        
        # Handle Pacifica response format
        pacifica_positions = []
        if isinstance(response, dict):
            if response.get('success') and response.get('data'):
                pacifica_positions = response['data']
            else:
                logger.error(f"Pacifica API error: {response.get('error', 'Unknown error')}")
                return
        elif isinstance(response, list):
            pacifica_positions = response
        
        print(f"📊 PACIFICA POSITIONS: {len(pacifica_positions)}")
        print("-" * 80)
        
        if pacifica_positions:
            for pos in pacifica_positions:
                symbol = pos.get('symbol', 'N/A')
                side = pos.get('side', 'N/A')
                amount = float(pos.get('amount', 0))
                entry_price = float(pos.get('entry_price', 0))
                
                if amount > 0:
                    print(f"  {symbol:8s} | {side:5s} | Amount: {amount:10.4f} | Entry: ${entry_price:10.4f}")
        else:
            print("  No positions on Pacifica")
        
    except Exception as e:
        logger.error(f"Error fetching Pacifica positions: {e}")
        return
    
    print()
    
    # Get positions from database
    async with AsyncSessionLocal() as session:
        db_positions_query = select(Position)
        result = await session.execute(db_positions_query)
        db_positions = result.scalars().all()
        
        print(f"💾 DATABASE POSITIONS: {len(db_positions)}")
        print("-" * 80)
        
        if db_positions:
            for pos in db_positions:
                print(f"  {pos.symbol:8s} | {pos.side:5s} | Amount: {pos.amount:10.4f} | "
                      f"Entry: ${pos.entry_price:10.4f} | PnL: ${pos.unrealized_pnl:10.2f}")
        else:
            print("  No positions in database")
        
        print()
        print("="*80)
        print("SYNC ANALYSIS")
        print("="*80)
        print()
        
        # Create lookup dictionaries
        pacifica_lookup = {}
        for pos in pacifica_positions:
            symbol = pos.get('symbol')
            amount = float(pos.get('amount', 0))
            if symbol and amount > 0:
                pacifica_lookup[symbol] = pos
        
        db_lookup = {}
        for pos in db_positions:
            db_lookup[pos.symbol] = pos
        
        # Find discrepancies
        only_in_db = set(db_lookup.keys()) - set(pacifica_lookup.keys())
        only_in_pacifica = set(pacifica_lookup.keys()) - set(db_lookup.keys())
        in_both = set(db_lookup.keys()) & set(pacifica_lookup.keys())
        
        issues_found = False
        
        # Positions only in database (ghost positions)
        if only_in_db:
            issues_found = True
            print(f"⚠️  GHOST POSITIONS (in DB but not on Pacifica): {len(only_in_db)}")
            for symbol in only_in_db:
                pos = db_lookup[symbol]
                print(f"   {symbol:8s} | {pos.side:5s} | Amount: {pos.amount:.4f} | "
                      f"Entry: ${pos.entry_price:.2f}")
            print()
        
        # Positions only on Pacifica (missing in DB)
        if only_in_pacifica:
            issues_found = True
            print(f"⚠️  MISSING POSITIONS (on Pacifica but not in DB): {len(only_in_pacifica)}")
            for symbol in only_in_pacifica:
                pos = pacifica_lookup[symbol]
                print(f"   {symbol:8s} | {pos.get('side'):5s} | "
                      f"Amount: {float(pos.get('amount')):.4f} | "
                      f"Entry: ${float(pos.get('entry_price')):.2f}")
            print()
        
        # Positions in both but with different amounts
        mismatched = []
        for symbol in in_both:
            pac_pos = pacifica_lookup[symbol]
            db_pos = db_lookup[symbol]
            pac_amount = float(pac_pos.get('amount', 0))
            
            if abs(pac_amount - db_pos.amount) > 0.01:  # Allow for rounding
                mismatched.append((symbol, pac_amount, db_pos.amount))
        
        if mismatched:
            issues_found = True
            print(f"⚠️  AMOUNT MISMATCHES: {len(mismatched)}")
            for symbol, pac_amt, db_amt in mismatched:
                print(f"   {symbol:8s} | Pacifica: {pac_amt:.4f} | DB: {db_amt:.4f} | "
                      f"Diff: {pac_amt - db_amt:.4f}")
            print()
        
        if not issues_found:
            print("✅ All positions are in sync!")
            print()
            return
        
        # Offer to fix
        print("="*80)
        print("FIX OPTIONS")
        print("="*80)
        print()
        print("1. Remove ghost positions from database (positions not on Pacifica)")
        print("2. Add missing positions to database (positions on Pacifica)")
        print("3. Update mismatched amounts to match Pacifica")
        print("4. Do all of the above (recommended)")
        print("5. Cancel (no changes)")
        print()
        
        choice = input("Enter your choice (1-5): ").strip()
        
        if choice == "5":
            print("❌ Cancelled. No changes made.")
            return
        
        if choice in ["1", "4"]:
            # Remove ghost positions
            if only_in_db:
                print()
                print("🗑️  Removing ghost positions from database...")
                for symbol in only_in_db:
                    pos = db_lookup[symbol]
                    await session.delete(pos)
                    print(f"   ✅ Removed {symbol} ({pos.side}, {pos.amount:.4f})")
                await session.commit()
                print(f"✅ Removed {len(only_in_db)} ghost position(s)")
        
        if choice in ["2", "4"]:
            # Add missing positions
            if only_in_pacifica:
                print()
                print("➕ Adding missing positions to database...")
                for symbol in only_in_pacifica:
                    pac_pos = pacifica_lookup[symbol]
                    new_position = Position(
                        strategy_id="vwm_momentum_1",  # Default strategy
                        symbol=symbol,
                        side=pac_pos.get('side'),
                        amount=float(pac_pos.get('amount')),
                        entry_price=float(pac_pos.get('entry_price')),
                        current_price=float(pac_pos.get('entry_price')),
                        unrealized_pnl=0.0,
                        realized_pnl=0.0,
                        opened_at=datetime.utcnow(),
                        updated_at=datetime.utcnow(),
                        metadata={"synced_from_pacifica": True}
                    )
                    session.add(new_position)
                    print(f"   ✅ Added {symbol} ({pac_pos.get('side')}, "
                          f"{float(pac_pos.get('amount')):.4f})")
                await session.commit()
                print(f"✅ Added {len(only_in_pacifica)} position(s)")
        
        if choice in ["3", "4"]:
            # Update mismatched amounts
            if mismatched:
                print()
                print("🔄 Updating mismatched amounts...")
                for symbol, pac_amt, db_amt in mismatched:
                    db_pos = db_lookup[symbol]
                    db_pos.amount = pac_amt
                    db_pos.updated_at = datetime.utcnow()
                    print(f"   ✅ Updated {symbol}: {db_amt:.4f} → {pac_amt:.4f}")
                await session.commit()
                print(f"✅ Updated {len(mismatched)} position(s)")
        
        print()
        print("="*80)
        print("✅ SYNC COMPLETE!")
        print("="*80)
        print()


if __name__ == "__main__":
    asyncio.run(sync_positions())

