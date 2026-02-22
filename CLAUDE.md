# CLAUDE.md - Nexwave Development Context

## Project Overview

**Nexwave** is an autonomous trading agent and data intelligence platform for Pacifica perpetual DEX on Solana. Operated by OpenClaw Agent and Nexwave, providing real-time market data and algorithmic trading strategies.

**Core Mission:** Deliver high-performance algorithmic trading with institutional-grade risk management and real-time market intelligence.

## Critical Recent Updates

### Database Infrastructure Fix (Dec 7, 2025) - CRITICAL

**Problem:** Trading engine non-functional for 14+ hours due to missing database tables

**Issues Found & Resolved:**
1. **Missing Continuous Aggregates** - Only `candles_1m` existed, missing 5 other timeframes (`5m/15m/1h/4h/1d`)
   - Root cause: Original migration used unsupported hierarchical rollup syntax
   - Fix: Created `migrations/002_continuous_aggregates_fixed.sql` with direct aggregation from ticks
2. **Missing Database Column** - `positions.trailing_stop_price` column missing, causing crashes
   - Fix: Ran migration `005_add_trailing_stop_price.sql`
3. **Data Pipeline Stalled** - No new ticks for 2 hours (Redis consumer group error)
   - Fix: Restarted market-data and db-writer services, data flow restored (370 ticks/min)

**Current Status:**
- ✅ All database infrastructure operational
- ⏳ Awaiting sufficient historical data for strategy execution
  - Short-term strategies (1h): Need 24 candles, have 13 → Active in ~11 hours
  - Long-term strategies (1d): Need 10 candles, have 2 → Active in ~8 days
- ✅ Risk management verified functional (blacklist, frequency limits, position sizing)
- ⚠️ Docker health checks failing (cosmetic only - services working)

**See:** `docs/AUDIT_2025_12_07.md` for complete audit report

### Codebase Cleanup (Dec 6, 2025) - RECENT

**Removed unused services and dead code (~1,500 lines, 4 Docker containers):**
- **Whale Tracking System** - Not working (data mismatch), not used by trading engine
- **Kafka + Zookeeper** - Trading engine places orders directly via Pacifica API
- **Order Management Service** - Trading engine bypasses it completely
- **VolumeWeightedMomentumStrategy** - Imported but never instantiated

**Result:** Leaner codebase, reduced Docker footprint (~500MB saved), faster startup

### Risk Management Overhaul (Nov 15, 2025) - PRIORITY

**Problem:** 8 days of trading revealed 14.6% win rate, -$217 P&L, 83 trades/day (should be 15-20)

**Solutions Implemented:**
- **Symbol Blacklist** (`risk_manager.py:50-57`): Blocks XPL, ASTER, FARTCOIN, PENGU, CRV, SUI (-$176 combined)
- **Trade Frequency Limits**: 5-min cooldown, max 10 trades/symbol/day
- **Minimum Position Size**: $50 (was $10) - eliminates fee bleeding
- **Profit Viability Check**: Rejects trades requiring >5% move or <$2 profit after fees

**Expected Results:** Trade frequency 76% reduction, win rate 2-3x improvement, break-even to +$10-30/day

### Volatility-Adjusted Profit Taking (Nov 15, 2025)

**Problem:** Fixed 4x ATR targets unrealistic for low-volatility assets (BTC 0.5% ATR → 2% target)

**Solution:** Dynamic targets - low volatility (≤1.5% ATR) uses 1-5% fixed, high volatility uses 2-6x ATR
- **Fixed vwap query bug** preventing candle data retrieval

### Trading Engine Fixes (Nov 10, 2025)

**Enabled live order execution:**
- Lowered volume threshold: 1.2x → 0.5x for off-peak trading
- Added lot/tick size rounding to comply with Pacifica API
- First successful trades: VIRTUAL & FARTCOIN @ 5x leverage

### Position Sync & P&L Tracking (Nov 8, 2025)

- Real-time sync with Pacifica API every 60s
- Accurate P&L calculation for long/short positions
- Proper leverage display from pair configuration

### Data Pipeline Fixes (Nov 3-7, 2025)

- **Redis Fix:** Promoted from read-only replica to master
- **WebSocket Format:** Matched Pacifica's array data format
- **30 Pairs Support:** Expanded from 3 to all 30 Pacifica markets

## Architecture

```
Pacifica DEX (WebSocket/REST)
  ↓
Market Data Service → Redis Pub/Sub
  ↓
Database Writer
  ↓
TimescaleDB (time-series optimization)
  ↓
API Gateway (FastAPI) ← Trading Engine
```

### Core Database Tables

- **`ticks`** - TimescaleDB hypertable, 1-day chunks, compressed after 7 days
- **`pairs`** - 30 trading pairs config (symbol, leverage, category, thresholds)
- **`positions`** - Open positions with real-time P&L tracking
- **`orders`** - Complete order audit trail
- **Continuous Aggregates:** `candlestick_1m/5m/15m/1h/4h/1d` (auto-refreshing)

## Configuration

### Critical Environment Variables

```bash
USE_ALL_PAIRS=true
PACIFICA_API_URL=https://api.pacifica.fi/api/v1
PACIFICA_WS_URL=wss://ws.pacifica.fi/ws
DATABASE_URL=postgresql://nexwave:password@postgres:5432/nexwave

# Trading Strategy (Pacifica = dominant scalper; Baddie Quant = swing/long-term)
VWM_TIMEFRAME=5m              # 5m candles for scalping (1m/5m/15m/1h/4h/1d)
VWM_MOMENTUM_THRESHOLD=0.001  # 0.1% entry signal
VWM_EXIT_THRESHOLD=0.0005     # 0.05% exit signal
VWM_VOLUME_MULTIPLIER=2.0     # 2x volume confirmation
VWM_LOOKBACK_PERIOD=12        # 12 candles (e.g. 1h on 5m)
VWM_BASE_POSITION_PCT=1.0     # 1% base position (scalping)
VWM_MAX_POSITION_PCT=5.0      # 5% max
VWM_STOP_LOSS_ATR_MULTIPLIER=1.5
VWM_TAKE_PROFIT_ATR_MULTIPLIER=2.5
TRADE_COOLDOWN_SECONDS=300    # 5 min between trades

# Volatility-Adjusted Take Profit
VWM_TP_VOLATILITY_THRESHOLD=0.015  # 1.5% dividing line
VWM_TP_MIN_PROFIT_PCT=1.0          # Min 1% profit
VWM_TP_MAX_PROFIT_PCT=5.0          # Max 5% for low volatility
VWM_TP_MIN_ATR_MULTIPLE=2.0        # Min 2x ATR
VWM_TP_MAX_ATR_MULTIPLE=6.0        # Max 6x ATR
```

### Pair Categories

- **Major** (BTC, ETH, SOL)
- **Mid-Cap** (HYPE, XRP, AAVE)
- **Emerging** (DOGE, LINK, SUI)
- **Small-Cap** (PENGU, LDO, CRV)

Config file: `src/nexwave/common/pairs.py`

## Key API Endpoints

- `GET /api/v1/pairs` - All 30 trading pairs with metadata
- `GET /api/v1/latest-prices` - Real-time prices with 24h change
- `GET /api/v1/positions` - Current open positions
- `GET /api/v1/performance` - Trading performance metrics
- `GET /api/analytics` - Analytics data
- **OpenClaw Agent:** `GET /api/v1/strategy-config` - Current strategy/risk params (safe, no secrets)
- **Agent Integration:** `PATCH /api/v1/strategy-config` - Merge overrides (writes to `AGENT_OVERRIDES_PATH` or `config/agent_strategy_overrides.json`); trading engine reloads every 60s

## Development

### Starting Services

```bash
# Backend services
python -m src.nexwave.services.market_data.client
python -m src.nexwave.services.db_writer.service
python -m src.nexwave.services.api_gateway.main
python -m src.nexwave.services.trading_engine.engine

# Database migrations
psql -U nexwave -d nexwave -f migrations/004_add_pairs_table.sql
```

### Docker Commands

**IMPORTANT:** Always use `docker compose` (no dash) with required flags:

```bash
# Standard startup
docker compose up -d --remove-orphans

# Full rebuild
docker compose down
docker compose build --no-cache
docker compose up -d --remove-orphans

# Rebuild specific service (example: api-gateway)
docker compose up -d --build --no-cache --no-deps --remove-orphans api-gateway

# Maintenance (run weekly)
docker system prune -a --volumes -f
```

### Common Issues & Solutions

**"WebSocket not connecting"**
- Verify Pacifica URLs in `.env`
- Check logs: `docker logs nexwave-market-data`

**"No trades executing"**
- Check volume threshold (should be 0.5 for off-peak)
- Verify symbol not in blacklist (XPL, ASTER, FARTCOIN, PENGU, CRV, SUI)
- Check trade frequency limits (5-min cooldown, 10/day max)

**"API not accessible"**
- Verify API Gateway is running: `docker logs nexwave-api`
- Check port 8000 is accessible: `curl http://localhost:8000/health`
- Ensure database and Redis are healthy

## Code Style

### Python
- Async/await for all I/O operations
- Python 3.11+ type hints everywhere
- Google-style docstrings
- `snake_case` for functions/variables, `PascalCase` for classes

### Database
- Index on (symbol, time) for time-series queries
- Never modify existing migrations, create new ones
- Use foreign keys for referential integrity

## Performance Notes

- TimescaleDB continuous aggregates for candlesticks
- Batch inserts (5000 ticks) reduce write overhead
- Redis caching (<5s TTL) for market prices
- Single WebSocket connection per service with auto-reconnect

## Documentation

- **[README.md](README.md)** - Project overview
- **[SCALPING_STRATEGY.md](docs/SCALPING_STRATEGY.md)** - Scalping defaults and config (Pacifica vs Baddie Quant swing)
- **[AUDIT_2025_12_07.md](docs/AUDIT_2025_12_07.md)** - Trading engine audit report
- **[PAIRS_IMPLEMENTATION.md](docs/PAIRS_IMPLEMENTATION.md)** - 30-pair implementation guide
- **API Docs** - `/docs` endpoint (OpenAPI/Swagger)

## Deployment

**Production Stack:** Internet → Docker Compose → API Gateway (port 8000)

**Monitoring Targets:**
- API response: <50ms
- DB write rate: 5000+ ticks/sec
- WebSocket uptime: 99.99%

## Contact

- GitHub: https://github.com/nexwave-so/pacifica-operator
- Website: https://nexwave.so
- Twitter: https://x.com/nexwave_so

---

**Last Updated:** January 29, 2026
**Version:** 2.5.0 (Backend-only: removed frontend and NGINX)
