#!/usr/bin/env python3
"""
Data Storage Audit Script
Verifies that all tick data and candle data are being stored correctly.
"""

import asyncio
import sys
from datetime import datetime, timedelta
from sqlalchemy import text, select, func
from sqlalchemy.ext.asyncio import AsyncSession

# Add parent directory to path
sys.path.insert(0, '/var/www/nexwave')

from nexwave.db.session import AsyncSessionLocal
from nexwave.db.models import Tick
from nexwave.common.logger import logger, setup_logging
from nexwave.common.config import settings


async def check_tick_data_storage(session: AsyncSession) -> dict:
    """Check if tick data is being stored correctly"""
    print("\n" + "="*80)
    print("AUDIT: Tick Data Storage")
    print("="*80)
    
    results = {
        "ticks_table_exists": False,
        "hypertable_status": None,
        "total_ticks": 0,
        "recent_ticks": 0,
        "ticks_by_symbol": {},
        "latest_tick_time": None,
        "issues": []
    }
    
    try:
        # Check if ticks table exists
        result = await session.execute(
            text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ticks')")
        )
        results["ticks_table_exists"] = result.scalar()
        
        if not results["ticks_table_exists"]:
            results["issues"].append("❌ TICKS TABLE DOES NOT EXIST")
            return results
        
        print("✅ Ticks table exists")
        
        # Check if ticks is a hypertable
        result = await session.execute(
            text("""
                SELECT COUNT(*) 
                FROM timescaledb_information.hypertables 
                WHERE hypertable_name = 'ticks'
            """)
        )
        hypertable_count = result.scalar()
        results["hypertable_status"] = "hypertable" if hypertable_count > 0 else "regular table"
        
        if hypertable_count == 0:
            results["issues"].append("⚠️  TICKS TABLE IS NOT A HYPERTABLE - Performance may be degraded")
        else:
            print("✅ Ticks table is a TimescaleDB hypertable")
        
        # Get total tick count
        result = await session.execute(
            text("SELECT COUNT(*) FROM ticks")
        )
        results["total_ticks"] = result.scalar()
        print(f"📊 Total ticks in database: {results['total_ticks']:,}")
        
        # Get ticks from last hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        result = await session.execute(
            text("SELECT COUNT(*) FROM ticks WHERE time >= :time"),
            {"time": one_hour_ago}
        )
        results["recent_ticks"] = result.scalar()
        print(f"📊 Ticks in last hour: {results['recent_ticks']:,}")
        
        if results["recent_ticks"] == 0:
            results["issues"].append("⚠️  NO TICKS IN THE LAST HOUR - Data ingestion may be stopped")
        
        # Get ticks by symbol
        result = await session.execute(
            text("""
                SELECT symbol, COUNT(*) as count, MAX(time) as latest
                FROM ticks
                GROUP BY symbol
                ORDER BY count DESC
            """)
        )
        
        for row in result:
            symbol = row[0]
            count = row[1]
            latest = row[2]
            results["ticks_by_symbol"][symbol] = {
                "count": count,
                "latest": latest.isoformat() if latest else None
            }
            print(f"  {symbol}: {count:,} ticks (latest: {latest})")
        
        # Get latest tick time
        result = await session.execute(
            text("SELECT MAX(time) FROM ticks")
        )
        latest_time = result.scalar()
        results["latest_tick_time"] = latest_time.isoformat() if latest_time else None
        
        if latest_time:
            time_diff = datetime.utcnow() - latest_time.replace(tzinfo=None) if latest_time.tzinfo else datetime.utcnow() - latest_time
            print(f"⏰ Latest tick time: {latest_time} ({time_diff.total_seconds():.0f} seconds ago)")
            
            if time_diff.total_seconds() > 300:  # 5 minutes
                results["issues"].append(f"⚠️  LATEST TICK IS {time_diff.total_seconds():.0f} SECONDS OLD - Data may be stale")
        
    except Exception as e:
        results["issues"].append(f"❌ ERROR CHECKING TICK DATA: {str(e)}")
        logger.error(f"Error checking tick data: {e}")
    
    return results


async def check_candle_data_generation(session: AsyncSession) -> dict:
    """Check if candle data is being generated correctly"""
    print("\n" + "="*80)
    print("AUDIT: Candle Data Generation")
    print("="*80)
    
    results = {
        "continuous_aggregates_exist": {},
        "candle_views_exist": {},
        "candle_counts": {},
        "latest_candles": {},
        "refresh_policies": {},
        "issues": []
    }
    
    timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
    view_names = {
        "1m": "candles_1m",
        "5m": "candles_5m",
        "15m": "candles_15m",
        "1h": "candles_1h",
        "4h": "candles_4h",
        "1d": "candles_1d"
    }
    ohlcv_views = {
        "1m": "candles_1m_ohlcv",
        "5m": "candles_5m_ohlcv",
        "15m": "candles_15m_ohlcv",
        "1h": "candles_1h_ohlcv",
        "4h": "candles_4h_ohlcv",
        "1d": "candles_1d_ohlcv"
    }
    
    try:
        # Check continuous aggregates
        for tf in timeframes:
            view_name = view_names[tf]
            ohlcv_view = ohlcv_views[tf]
            
            # Check if materialized view exists
            result = await session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM pg_matviews 
                        WHERE matviewname = :view_name
                    )
                """),
                {"view_name": view_name}
            )
            results["continuous_aggregates_exist"][tf] = result.scalar()
            
            # Check if OHLCV view exists
            result = await session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.views 
                        WHERE table_name = :view_name
                    )
                """),
                {"view_name": ohlcv_view}
            )
            results["candle_views_exist"][tf] = result.scalar()
            
            if results["continuous_aggregates_exist"][tf]:
                print(f"✅ {tf} continuous aggregate exists")
                
                # Check if it's a TimescaleDB continuous aggregate
                result = await session.execute(
                    text("""
                        SELECT COUNT(*) 
                        FROM timescaledb_information.continuous_aggregates 
                        WHERE view_name = :view_name
                    """),
                    {"view_name": view_name}
                )
                is_timescale_ca = result.scalar() > 0
                
                if not is_timescale_ca:
                    results["issues"].append(f"⚠️  {tf} view exists but is not a TimescaleDB continuous aggregate")
                
                # Check refresh policies
                result = await session.execute(
                    text("""
                        SELECT 
                            schedule_interval,
                            max_interval_per_job,
                            start_offset,
                            end_offset
                        FROM timescaledb_information.jobs j
                        JOIN timescaledb_information.job_stats js ON j.job_id = js.job_id
                        WHERE j.proc_name = 'policy_refresh_continuous_aggregate'
                        AND j.hypertable_name = :view_name
                    """),
                    {"view_name": view_name}
                )
                policy = result.first()
                
                if policy:
                    results["refresh_policies"][tf] = {
                        "schedule_interval": str(policy[0]) if policy[0] else None,
                        "max_interval_per_job": str(policy[1]) if policy[1] else None,
                        "start_offset": str(policy[2]) if policy[2] else None,
                        "end_offset": str(policy[3]) if policy[3] else None,
                    }
                    print(f"  📅 Refresh policy: {policy[0]} interval")
                else:
                    results["issues"].append(f"⚠️  {tf} continuous aggregate has NO REFRESH POLICY")
                    print(f"  ⚠️  No refresh policy found")
                
                # Get candle count
                if results["candle_views_exist"][tf]:
                    try:
                        result = await session.execute(
                            text(f"SELECT COUNT(*) FROM {ohlcv_view}")
                        )
                        count = result.scalar()
                        results["candle_counts"][tf] = count
                        print(f"  📊 Total candles: {count:,}")
                        
                        if count == 0:
                            results["issues"].append(f"⚠️  {tf} candles view has NO DATA - Continuous aggregate may need manual refresh")
                        
                        # Get latest candle
                        result = await session.execute(
                            text(f"""
                                SELECT MAX(time) FROM {ohlcv_view}
                            """)
                        )
                        latest = result.scalar()
                        if latest:
                            results["latest_candles"][tf] = latest.isoformat()
                            time_diff = datetime.utcnow() - (latest.replace(tzinfo=None) if latest.tzinfo else latest)
                            print(f"  ⏰ Latest candle: {latest} ({time_diff.total_seconds():.0f} seconds ago)")
                    except Exception as e:
                        results["issues"].append(f"❌ ERROR QUERYING {tf} CANDLES: {str(e)}")
                        print(f"  ❌ Error querying candles: {e}")
            else:
                results["issues"].append(f"❌ {tf} CONTINUOUS AGGREGATE DOES NOT EXIST")
                print(f"❌ {tf} continuous aggregate missing")
        
        # Check if continuous aggregates need manual refresh
        print("\n📋 Checking if continuous aggregates need data...")
        for tf in timeframes:
            if results["candle_counts"].get(tf, 0) == 0 and results["continuous_aggregates_exist"].get(tf, False):
                print(f"  ⚠️  {tf} aggregate has no data - may need: CALL refresh_continuous_aggregate('{view_names[tf]}', NULL, NULL);")
        
    except Exception as e:
        results["issues"].append(f"❌ ERROR CHECKING CANDLE DATA: {str(e)}")
        logger.error(f"Error checking candle data: {e}")
    
    return results


async def check_data_coverage(session: AsyncSession) -> dict:
    """Check data coverage across all pairs"""
    print("\n" + "="*80)
    print("AUDIT: Data Coverage Across Pairs")
    print("="*80)
    
    results = {
        "symbols_with_ticks": [],
        "symbols_without_ticks": [],
        "symbols_with_candles": {},
        "coverage_issues": []
    }
    
    try:
        # Get all configured symbols
        from nexwave.common.pairs import get_all_symbols
        all_symbols = get_all_symbols()
        print(f"📊 Total configured symbols: {len(all_symbols)}")
        
        # Check which symbols have tick data
        result = await session.execute(
            text("""
                SELECT DISTINCT symbol 
                FROM ticks
                WHERE time >= NOW() - INTERVAL '24 hours'
            """)
        )
        symbols_with_recent_ticks = {row[0] for row in result}
        
        for symbol in all_symbols:
            if symbol in symbols_with_recent_ticks:
                results["symbols_with_ticks"].append(symbol)
            else:
                results["symbols_without_ticks"].append(symbol)
                results["coverage_issues"].append(f"⚠️  {symbol} has NO TICK DATA in last 24 hours")
        
        print(f"✅ Symbols with recent ticks: {len(results['symbols_with_ticks'])}")
        print(f"⚠️  Symbols without recent ticks: {len(results['symbols_without_ticks'])}")
        
        if results["symbols_without_ticks"]:
            print(f"   Missing: {', '.join(results['symbols_without_ticks'])}")
        
        # Check candle coverage for each timeframe
        timeframes = ["1m", "5m", "15m", "1h", "4h", "1d"]
        ohlcv_views = {
            "1m": "candles_1m_ohlcv",
            "5m": "candles_5m_ohlcv",
            "15m": "candles_15m_ohlcv",
            "1h": "candles_1h_ohlcv",
            "4h": "candles_4h_ohlcv",
            "1d": "candles_1d_ohlcv"
        }
        
        for tf in timeframes:
            ohlcv_view = ohlcv_views[tf]
            result = await session.execute(
                text(f"""
                    SELECT DISTINCT symbol 
                    FROM {ohlcv_view}
                    WHERE time >= NOW() - INTERVAL '24 hours'
                """)
            )
            symbols_with_candles = {row[0] for row in result}
            results["symbols_with_candles"][tf] = list(symbols_with_candles)
            
            missing = set(all_symbols) - symbols_with_candles
            if missing:
                print(f"  ⚠️  {tf} candles missing for: {', '.join(missing)}")
                results["coverage_issues"].append(f"⚠️  {tf} candles missing for {len(missing)} symbols")
    
    except Exception as e:
        results["coverage_issues"].append(f"❌ ERROR CHECKING DATA COVERAGE: {str(e)}")
        logger.error(f"Error checking data coverage: {e}")
    
    return results


async def main():
    """Run complete data storage audit"""
    print("\n" + "="*80)
    print("NEXWAVE DATA STORAGE AUDIT")
    print("="*80)
    print(f"Timestamp: {datetime.utcnow().isoformat()}")
    
    setup_logging(level=settings.log_level)
    
    async with AsyncSessionLocal() as session:
        # Run all audits
        tick_results = await check_tick_data_storage(session)
        candle_results = await check_candle_data_generation(session)
        coverage_results = await check_data_coverage(session)
        
        # Summary
        print("\n" + "="*80)
        print("AUDIT SUMMARY")
        print("="*80)
        
        all_issues = (
            tick_results.get("issues", []) +
            candle_results.get("issues", []) +
            coverage_results.get("coverage_issues", [])
        )
        
        if not all_issues:
            print("✅ ALL CHECKS PASSED - Data storage is working correctly!")
        else:
            print(f"⚠️  FOUND {len(all_issues)} ISSUE(S):")
            for issue in all_issues:
                print(f"  {issue}")
        
        print("\n" + "="*80)
        print("RECOMMENDATIONS")
        print("="*80)
        
        # Generate recommendations
        if not tick_results["ticks_table_exists"]:
            print("1. Run database migrations to create ticks table")
        
        if tick_results.get("hypertable_status") != "hypertable":
            print("2. Convert ticks table to hypertable: SELECT create_hypertable('ticks', 'time');")
        
        if tick_results.get("recent_ticks", 0) == 0:
            print("3. Check if market-data service is running and connected to Pacifica")
            print("4. Check if db-writer service is running and consuming from Redis")
        
        if any(candle_results.get("candle_counts", {}).get(tf, 0) == 0 for tf in ["1m", "5m", "15m", "1h"]):
            print("5. Refresh continuous aggregates to populate candle data:")
            print("   CALL refresh_continuous_aggregate('candles_1m', NULL, NULL);")
            print("   CALL refresh_continuous_aggregate('candles_5m', NULL, NULL);")
            print("   CALL refresh_continuous_aggregate('candles_15m', NULL, NULL);")
            print("   CALL refresh_continuous_aggregate('candles_1h', NULL, NULL);")
        
        if not all(candle_results.get("refresh_policies", {}).get(tf) for tf in ["1m", "5m", "15m", "1h"]):
            print("6. Add refresh policies for continuous aggregates (run migration 002)")
        
        if coverage_results.get("symbols_without_ticks"):
            print(f"7. {len(coverage_results['symbols_without_ticks'])} symbols missing tick data - check market-data service subscriptions")
        
        print("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(main())

