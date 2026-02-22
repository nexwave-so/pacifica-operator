#!/usr/bin/env python3
"""
Real-time Trading Performance Monitor

Tracks key metrics to validate risk management improvements:
- Trade count per symbol per day
- Win rate tracking
- Blacklist violations
- Position size distribution
- Daily P&L

Usage:
    python scripts/monitor_trading_performance.py
    python scripts/monitor_trading_performance.py --days 7
"""

import asyncio
import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy import select, func, and_
from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Order, Position


# Symbol blacklist (should match risk_manager.py)
BLACKLISTED_SYMBOLS = {'XPL', 'ASTER', 'FARTCOIN', 'PENGU', 'CRV', 'SUI'}


async def get_daily_trade_stats(days: int = 1) -> Dict:
    """Get trade statistics for the last N days"""

    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get all orders since cutoff
        query = select(Order).where(
            Order.created_at >= cutoff,
            Order.status.in_(['filled', 'submitted'])
        ).order_by(Order.created_at.desc())

        result = await session.execute(query)
        orders = result.scalars().all()

        # Calculate stats
        stats = {
            'total_trades': len(orders),
            'trades_by_symbol': defaultdict(int),
            'trades_by_day': defaultdict(int),
            'blacklist_violations': [],
            'position_sizes': [],
            'symbols_traded': set(),
        }

        for order in orders:
            # Count by symbol
            stats['trades_by_symbol'][order.symbol] += 1
            stats['symbols_traded'].add(order.symbol)

            # Count by day
            day_key = order.created_at.strftime('%Y-%m-%d')
            stats['trades_by_day'][day_key] += 1

            # Check blacklist violations
            if order.symbol.upper() in BLACKLISTED_SYMBOLS:
                stats['blacklist_violations'].append({
                    'symbol': order.symbol,
                    'time': order.created_at,
                    'order_id': order.order_id,
                })

            # Track position sizes
            position_size_usd = order.amount * order.price
            stats['position_sizes'].append({
                'symbol': order.symbol,
                'size_usd': position_size_usd,
                'time': order.created_at,
            })

        return stats


async def get_pnl_stats(days: int = 1) -> Dict:
    """Get P&L statistics"""

    async with AsyncSessionLocal() as session:
        cutoff = datetime.utcnow() - timedelta(days=days)

        # Get realized P&L from closed positions
        query = select(
            func.sum(Position.realized_pnl).label('realized_pnl'),
            func.count(Position.id).label('closed_positions'),
            func.sum(func.case((Position.realized_pnl > 0, 1), else_=0)).label('winners'),
            func.sum(func.case((Position.realized_pnl < 0, 1), else_=0)).label('losers'),
        ).where(
            Position.updated_at >= cutoff,
            Position.realized_pnl.isnot(None),
            Position.realized_pnl != 0,
        )

        result = await session.execute(query)
        row = result.one()

        # Get unrealized P&L from open positions
        query_open = select(
            func.sum(Position.unrealized_pnl).label('unrealized_pnl'),
            func.count(Position.id).label('open_positions'),
        ).where(
            Position.strategy_id.isnot(None)
        )

        result_open = await session.execute(query_open)
        row_open = result_open.one()

        realized_pnl = float(row.realized_pnl or 0)
        unrealized_pnl = float(row_open.unrealized_pnl or 0)
        total_pnl = realized_pnl + unrealized_pnl

        winners = int(row.winners or 0)
        losers = int(row.losers or 0)
        total_closed = winners + losers
        win_rate = (winners / total_closed * 100) if total_closed > 0 else 0

        return {
            'realized_pnl': realized_pnl,
            'unrealized_pnl': unrealized_pnl,
            'total_pnl': total_pnl,
            'closed_positions': total_closed,
            'open_positions': int(row_open.open_positions or 0),
            'winners': winners,
            'losers': losers,
            'win_rate': win_rate,
        }


def print_report(trade_stats: Dict, pnl_stats: Dict, days: int):
    """Print formatted monitoring report"""

    print("=" * 80)
    print(f"NEXWAVE TRADING PERFORMANCE MONITOR - {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Period: Last {days} day(s)")
    print("=" * 80)

    # Trade Statistics
    print("\n📊 TRADE STATISTICS")
    print("-" * 80)
    print(f"Total Trades: {trade_stats['total_trades']}")
    print(f"Unique Symbols: {len(trade_stats['symbols_traded'])}")
    print(f"Trades per Day: {trade_stats['total_trades'] / days:.1f} avg")

    # Trades by day
    if trade_stats['trades_by_day']:
        print("\nTrades by Day:")
        for day in sorted(trade_stats['trades_by_day'].keys()):
            count = trade_stats['trades_by_day'][day]
            print(f"  {day}: {count:3d} trades")

    # Top traded symbols
    if trade_stats['trades_by_symbol']:
        print("\nTop Traded Symbols:")
        sorted_symbols = sorted(
            trade_stats['trades_by_symbol'].items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        for symbol, count in sorted_symbols:
            violation = "❌ BLACKLISTED" if symbol.upper() in BLACKLISTED_SYMBOLS else ""
            print(f"  {symbol:10s}: {count:3d} trades {violation}")

    # P&L Statistics
    print("\n💰 P&L STATISTICS")
    print("-" * 80)
    print(f"Realized P&L:   ${pnl_stats['realized_pnl']:>10.2f}")
    print(f"Unrealized P&L: ${pnl_stats['unrealized_pnl']:>10.2f}")
    print(f"Total P&L:      ${pnl_stats['total_pnl']:>10.2f}")
    print(f"\nClosed Positions: {pnl_stats['closed_positions']}")
    print(f"Open Positions:   {pnl_stats['open_positions']}")
    print(f"Win Rate:         {pnl_stats['win_rate']:.1f}% ({pnl_stats['winners']}/{pnl_stats['closed_positions']})")

    # Risk Management Checks
    print("\n🛡️  RISK MANAGEMENT CHECKS")
    print("-" * 80)

    # Check 1: Blacklist violations
    violations = trade_stats['blacklist_violations']
    if violations:
        print(f"❌ BLACKLIST VIOLATIONS: {len(violations)} trades")
        for v in violations[:5]:  # Show first 5
            print(f"   {v['time'].strftime('%Y-%m-%d %H:%M')} | {v['symbol']:10s} | Order: {v['order_id']}")
        if len(violations) > 5:
            print(f"   ... and {len(violations) - 5} more")
    else:
        print("✅ NO BLACKLIST VIOLATIONS")

    # Check 2: Position size distribution
    position_sizes = trade_stats['position_sizes']
    if position_sizes:
        sizes = [p['size_usd'] for p in position_sizes]
        min_size = min(sizes)
        max_size = max(sizes)
        avg_size = sum(sizes) / len(sizes)
        under_50 = sum(1 for s in sizes if s < 50)

        print(f"\n📏 POSITION SIZES")
        print(f"   Min:  ${min_size:>8.2f}")
        print(f"   Avg:  ${avg_size:>8.2f}")
        print(f"   Max:  ${max_size:>8.2f}")

        if under_50 > 0:
            print(f"   ❌ {under_50} trades under $50 minimum")
            # Show examples
            under_50_trades = [p for p in position_sizes if p['size_usd'] < 50][:3]
            for p in under_50_trades:
                print(f"      {p['time'].strftime('%Y-%m-%d %H:%M')} | {p['symbol']:10s} | ${p['size_usd']:.2f}")
        else:
            print(f"   ✅ All trades meet $50 minimum")

    # Check 3: Trade frequency (per symbol per day)
    if trade_stats['trades_by_symbol']:
        max_trades_symbol = max(trade_stats['trades_by_symbol'].values())
        max_trades_per_day = max_trades_symbol / days

        print(f"\n⏱️  TRADE FREQUENCY")
        print(f"   Max trades per symbol: {max_trades_symbol} ({max_trades_per_day:.1f}/day)")

        if max_trades_per_day > 10:
            # Find which symbols exceeded limit
            exceeding = [
                (sym, count) for sym, count in trade_stats['trades_by_symbol'].items()
                if count / days > 10
            ]
            print(f"   ❌ {len(exceeding)} symbols exceeded 10 trades/day limit:")
            for sym, count in sorted(exceeding, key=lambda x: x[1], reverse=True)[:5]:
                print(f"      {sym:10s}: {count:3d} trades ({count/days:.1f}/day)")
        else:
            print(f"   ✅ All symbols within 10 trades/day limit")

    # Performance Targets
    print("\n🎯 PERFORMANCE TARGETS")
    print("-" * 80)

    target_win_rate = 45.0
    target_daily_pnl = 10.0
    target_trade_frequency = 20.0

    current_win_rate = pnl_stats['win_rate']
    current_daily_pnl = pnl_stats['total_pnl'] / days
    current_daily_trades = trade_stats['total_trades'] / days

    print(f"Win Rate:          {current_win_rate:>6.1f}% (target: >{target_win_rate:.0f}%)")
    if current_win_rate >= target_win_rate:
        print("                   ✅ TARGET MET")
    else:
        gap = target_win_rate - current_win_rate
        print(f"                   ⏳ Need +{gap:.1f}% to reach target")

    print(f"\nDaily P&L:         ${current_daily_pnl:>7.2f} (target: >${target_daily_pnl:.0f})")
    if current_daily_pnl >= target_daily_pnl:
        print("                   ✅ TARGET MET")
    else:
        gap = target_daily_pnl - current_daily_pnl
        print(f"                   ⏳ Need +${gap:.2f}/day to reach target")

    print(f"\nTrade Frequency:   {current_daily_trades:>6.1f}/day (target: <{target_trade_frequency:.0f})")
    if current_daily_trades <= target_trade_frequency:
        print("                   ✅ TARGET MET")
    else:
        excess = current_daily_trades - target_trade_frequency
        print(f"                   ⚠️  {excess:.1f} trades/day over target")

    print("=" * 80)


async def main():
    """Main monitoring function"""

    import argparse
    parser = argparse.ArgumentParser(description='Monitor trading performance')
    parser.add_argument('--days', type=int, default=1, help='Number of days to analyze (default: 1)')
    parser.add_argument('--watch', action='store_true', help='Continuous monitoring mode (refresh every 60s)')
    args = parser.parse_args()

    if args.watch:
        print("🔄 Continuous monitoring mode (Ctrl+C to exit)")
        print()

        while True:
            try:
                # Clear screen (works on Unix and Windows)
                os.system('clear' if os.name != 'nt' else 'cls')

                # Fetch and display stats
                trade_stats = await get_daily_trade_stats(days=args.days)
                pnl_stats = await get_pnl_stats(days=args.days)
                print_report(trade_stats, pnl_stats, args.days)

                print("\n⏳ Refreshing in 60 seconds... (Ctrl+C to exit)")
                await asyncio.sleep(60)

            except KeyboardInterrupt:
                print("\n\n✋ Monitoring stopped by user")
                break
    else:
        # Single run
        trade_stats = await get_daily_trade_stats(days=args.days)
        pnl_stats = await get_pnl_stats(days=args.days)
        print_report(trade_stats, pnl_stats, args.days)


if __name__ == '__main__':
    asyncio.run(main())
