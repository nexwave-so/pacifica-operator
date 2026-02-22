# Database Initialization & Trading Engine Reactivation - November 14, 2025

## Overview

Successfully reactivated the Nexwave trading engine after database initialization. The database was empty and required complete schema setup including tables, hypertables, and continuous aggregates.

## Issues Resolved

### 1. Empty Database Schema

**Problem:**
- Database had no tables (relations not found)
- Trading engine failing with "relation 'ticks' does not exist"
- All services attempting to write to non-existent tables

**Solution:**
- Created all core tables using SQLAlchemy models as reference
- Set up TimescaleDB hypertable for `ticks` table
- Added foreign key constraints for referential integrity

**Tables Created:**
```sql
-- Core time-series data
ticks (TimescaleDB hypertable, partitioned by time)

-- Trading pairs configuration
pairs (34 symbols: BTC, ETH, SOL, etc.)

-- Order management
orders (audit trail for all orders)
positions (current open positions)

-- Analytics
whale_activities (large order detection)
```

### 2. Missing Pairs Data

**Problem:**
- Ticks table had 34 unique symbols (TRUMP, ICP, NEAR, STRK + original 30)
- Pairs table only configured for 30 symbols initially
- Foreign key constraint violations preventing data integrity

**Solution:**
- Added missing pairs: TRUMP, ICP, NEAR, STRK
- Categorized appropriately (emerging/small-cap)
- Total: 34 active trading pairs

**Pair Distribution:**
- Major: 3 pairs (BTC, ETH, SOL)
- Mid-Cap: 7 pairs (HYPE, ZEC, BNB, XRP, PUMP, AAVE, ENA)
- Emerging: 18 pairs (ASTER, VIRTUAL, FARTCOIN, DOGE, ICP, NEAR, STRK, etc.)
- Small-Cap: 6 pairs (WLFI, PENGU, 2Z, MON, LDO, CRV)

### 3. Continuous Aggregates Not Created

**Problem:**
- Trading engine requires `candles_15m_ohlcv` view for strategy calculations
- TimescaleDB continuous aggregates complex setup (toolkit functions, rollup chains)
- Error: "relation 'candles_15m_ohlcv' does not exist"

**Solution:**
- Created simplified view using standard PostgreSQL window functions
- Used `FIRST()` and `LAST()` for open/close prices
- Aggregates 15-minute OHLCV candles from tick data in real-time

**View Definition:**
```sql
CREATE OR REPLACE VIEW candles_15m_ohlcv AS
SELECT
    time_bucket('15 minutes', time) AS time,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume,
    SUM(price * volume) / NULLIF(SUM(volume), 0) AS vwap
FROM ticks
GROUP BY time_bucket('15 minutes', time), symbol;
```

### 4. Trading Engine Not Running

**Problem:**
- Trading engine service was disabled/stopped
- Container not present in `docker compose ps` output

**Solution:**
- Started trading engine with `docker compose up -d --remove-orphans trading-engine`
- Service now scanning all 34 pairs every 60 seconds
- Healthy status confirmed

## Current System Status

### Services (12/12 Healthy)
```
✅ postgres          - TimescaleDB with 1.1M+ ticks
✅ redis             - Pub/sub and caching layer
✅ kafka/zookeeper   - Message queue for order flow
✅ market-data       - WebSocket client collecting ticks
✅ db-writer         - Batch writing ticks to database
✅ whale-tracker     - Detecting large orders
✅ api-gateway       - REST API serving dashboard
✅ order-management  - Order lifecycle management
✅ trading-engine    - VWM strategy signal generation
✅ frontend          - Next.js dashboard
✅ nginx             - Reverse proxy with SSL
```

### Data Collection
- **Ticks Collected:** 1,110,112 ticks
- **Time Range:** 2025-11-14 16:35:26 to 18:00:30 UTC (~1.5 hours)
- **Candles Available:** 7 per symbol (15-minute intervals)
- **Pairs Active:** 34 symbols across all categories

### Trading Engine Status
- **State:** Running and healthy
- **Strategy:** Volume-Weighted Momentum (VWM)
- **Scan Interval:** 60 seconds
- **Lookback Required:** 20 candles (5 hours of data)
- **Current Status:** Waiting for sufficient historical data
  - Have: 7 candles (~1.75 hours)
  - Need: 20 candles (~5 hours)
  - ETA for signals: ~3 more hours

## Trading Strategy Configuration

From `.env` (live trading config):
```bash
STRATEGY=volume_weighted_momentum
STRATEGY_ID=vwm_momentum_1
PAPER_TRADING=false  # LIVE TRADING ENABLED

# VWM Parameters (Hackathon Demo Mode)
VWM_MOMENTUM_THRESHOLD=0.0005    # 0.05% entry signal
VWM_EXIT_THRESHOLD=0.0003        # 0.03% exit signal
VWM_VOLUME_MULTIPLIER=1.0        # Requires 1x average volume
VWM_LOOKBACK_PERIOD=20           # 20 candles (5 hours)
VWM_BASE_POSITION_PCT=5.0        # 5% base allocation
VWM_MAX_POSITION_PCT=15.0        # 15% max allocation

# Portfolio
PORTFOLIO_VALUE=100000           # $100K paper portfolio (or actual if live)

# Pacifica DEX Credentials
PACIFICA_API_URL=https://api.pacifica.fi/api/v1
PACIFICA_API_KEY=[configured]
PACIFICA_AGENT_WALLET_PUBKEY=[configured]
PACIFICA_AGENT_WALLET_PRIVKEY=[configured]
```

## Files Modified

### SQL Migrations Applied
1. Created all core tables (`ticks`, `pairs`, `orders`, `positions`, `whale_activities`)
2. Enabled TimescaleDB extensions (`timescaledb`, `timescaledb_toolkit`)
3. Created hypertable for `ticks` with 1-day chunks
4. Added indexes for performance (symbol+time, time+symbol)
5. Set up foreign key constraints for data integrity
6. Created `candles_15m_ohlcv` view for real-time aggregation
7. Inserted/updated 34 trading pairs with metadata

### Docker Services
- Started `trading-engine` service
- All 12 services now running and healthy

## Next Steps

1. **Wait for Data Accumulation** (~3 hours)
   - Need 20+ candles for VWM strategy
   - Currently at 7 candles, growing by 1 every 15 minutes

2. **Monitor First Signals**
   - Trading engine will automatically generate signals when data sufficient
   - Watch logs: `docker logs -f nexwave-trading-engine`

3. **Consider Lowering Lookback** (Optional)
   - Could reduce `VWM_LOOKBACK_PERIOD` from 20 to 10 for faster startup
   - Trade-off: Less historical context but quicker signal generation
   - Update `.env` and restart trading-engine if desired

4. **Future Optimizations**
   - Implement full TimescaleDB continuous aggregates (1m, 5m, 1h, 4h, 1d)
   - Add compression policy for ticks older than 7 days
   - Set up retention policy (90-day default)
   - Create additional timeframe views as needed

## Database Schema Summary

### Ticks (Hypertable)
- Primary key: `(time, symbol)`
- Indexed on: `(symbol, time)`, `(time, symbol)`
- Chunk interval: 1 day
- Foreign key: `symbol → pairs(symbol)`

### Pairs
- Primary key: `symbol`
- Fields: `max_leverage`, `min_order_size`, `tick_size`, `category`, `whale_threshold_usd`
- Categories: major, mid-cap, emerging, small-cap

### Orders
- Primary key: `id`
- Unique: `order_id`, `client_order_id`
- Indexed on: `(strategy_id, created_at)`, `(symbol, status, created_at)`
- Foreign key: `symbol → pairs(symbol)`

### Positions
- Primary key: `id`
- Unique constraint: `(strategy_id, symbol)`
- Fields: `side`, `amount`, `entry_price`, `unrealized_pnl`, `trailing_stop_price`
- Foreign key: `symbol → pairs(symbol)`

### Whale Activities
- Primary key: `id`
- Indexed on: `(symbol, detected_at)`, `total_value_usd`, `detected_at`
- Fields: `whale_type`, `direction`, `total_volume`, `confidence_score`
- Foreign key: `symbol → pairs(symbol)`

## Verification Commands

```bash
# Check all tables exist
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "\dt"

# Verify tick data
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "SELECT COUNT(*) FROM ticks;"

# Check candles available
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "
  SELECT symbol, COUNT(*) as candles
  FROM candles_15m_ohlcv
  GROUP BY symbol
  ORDER BY symbol
  LIMIT 5;
"

# Monitor trading engine
docker logs -f nexwave-trading-engine

# Check all services healthy
docker compose ps
```

## Known Limitations

1. **Simple View vs Continuous Aggregates**
   - Currently using standard PostgreSQL view
   - Recalculates on every query (acceptable for 1.5 hours of data)
   - Should migrate to TimescaleDB continuous aggregates for better performance with larger datasets

2. **Missing Timeframes**
   - Only 15-minute candles available
   - 1m, 5m, 1h, 4h, 1d aggregates not yet created
   - VWM strategy only uses 15m for now

3. **No Compression/Retention**
   - Ticks table will grow indefinitely
   - Should add compression after 7 days
   - Should add retention policy for 90-day limit

## References

- Trading Engine Fix (Nov 10): `TRADING_ENGINE_FIX_2025-11-10.md`
- Position Sync (Nov 8): Real-time position sync and P&L tracking
- CLAUDE.md: Complete project documentation
- migrations/004_add_pairs_table.sql: Pairs schema reference

---

**Completed:** November 14, 2025 18:00 UTC
**Services:** All 12 healthy and operational
**Status:** Trading engine active, waiting for data accumulation
