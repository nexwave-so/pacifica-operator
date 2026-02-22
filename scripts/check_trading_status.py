#!/usr/bin/env python3
"""Check trading engine status and recent activity"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Order, Position, Tick
from sqlalchemy import select, func, desc
from nexwave.common.logger import setup_logging, logger

setup_logging(level="INFO")


async def check_status():
    """Check trading engine status"""
    
    async with AsyncSessionLocal() as session:
        # Check recent orders (last 24 hours)
        cutoff = datetime.utcnow() - timedelta(hours=24)
        recent_orders_query = (
            select(Order)
            .where(Order.created_at >= cutoff)
            .order_by(desc(Order.created_at))
            .limit(10)
        )
        result = await session.execute(recent_orders_query)
        recent_orders = result.scalars().all()
        
        print("\n" + "="*80)
        print("TRADING ENGINE STATUS CHECK")
        print("="*80)
        print(f"\nRecent Orders (last 24 hours): {len(recent_orders)}")
        if recent_orders:
            for order in recent_orders:
                print(f"  - {order.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC: "
                      f"{order.symbol} {order.side} {order.amount:.4f} @ ${order.price:.2f} "
                      f"- Status: {order.status}")
        else:
            print("  ⚠️  NO ORDERS PLACED IN LAST 24 HOURS")
        
        # Check open positions
        positions_query = select(Position)
        result = await session.execute(positions_query)
        positions = result.scalars().all()
        
        print(f"\nOpen Positions: {len(positions)}")
        if positions:
            for pos in positions:
                print(f"  - {pos.symbol} {pos.side}: {pos.amount:.4f} @ ${pos.entry_price:.2f} "
                      f"(P&L: ${pos.unrealized_pnl:.2f})")
        else:
            print("  No open positions")
        
        # Check recent market data
        recent_ticks_query = (
            select(Tick)
            .order_by(desc(Tick.time))
            .limit(5)
        )
        result = await session.execute(recent_ticks_query)
        recent_ticks = result.scalars().all()
        
        print(f"\nRecent Market Data Updates:")
        if recent_ticks:
            for tick in recent_ticks:
                print(f"  - {tick.time.strftime('%Y-%m-%d %H:%M:%S')} UTC: "
                      f"{tick.symbol} @ ${tick.price:.2f}")
        else:
            print("  ⚠️  NO RECENT MARKET DATA")
        
        # Check for failed orders
        failed_orders_query = (
            select(Order)
            .where(Order.status == "failed")
            .where(Order.created_at >= cutoff)
            .order_by(desc(Order.created_at))
            .limit(5)
        )
        result = await session.execute(failed_orders_query)
        failed_orders = result.scalars().all()
        
        if failed_orders:
            print(f"\n⚠️  FAILED ORDERS (last 24 hours): {len(failed_orders)}")
            for order in failed_orders:
                print(f"  - {order.created_at.strftime('%Y-%m-%d %H:%M:%S')} UTC: "
                      f"{order.symbol} {order.side} - {order.metadata}")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(check_status())

