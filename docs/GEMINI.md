# GEMINI.md - Nexwave Development Context for Google AI Engineers

## Project Overview

**Nexwave** is an autonomous trading agent and data intelligence platform for Pacifica perpetual DEX on Solana. Operated by an [OpenClaw](https://github.com/openclaw/openclaw) agent (such as our instance, **Nexbot**) and Nexwave, providing real-time market data and algorithmic trading strategies.

**Core Mission:** Deliver high-performance algorithmic trading with institutional-grade risk management and real-time market intelligence.

**Tech Stack:**
- **Backend:** Python 3.11+, FastAPI, AsyncIO
- **Database:** TimescaleDB (PostgreSQL extension), Redis
- **Message Queue:** Kafka + Zookeeper
- **Frontend:** Next.js 14, React, TypeScript, TailwindCSS
- **Infrastructure:** Docker Compose, NGINX
- **External APIs:** Pacifica DEX (WebSocket + REST)

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│              Pacifica DEX (Solana)                      │
│         WebSocket: wss://ws.pacifica.fi/ws              │
│         REST API: https://api.pacifica.fi/api/v1        │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│           Market Data Service (Python)                  │
│  - WebSocket client with auto-reconnect                 │
│  - Handles 30 trading pairs (BTC, ETH, SOL, etc.)      │
│  - Publishes to Redis Pub/Sub                          │
└─────────┬─────────────────┬─────────────────────────────┘
          │                 │
          ▼                 ▼
┌──────────────────┐  ┌──────────────────────────────────┐
│  DB Writer       │  │  Whale Tracker Service           │
│  - Batch insert  │  │  - Detects large orders          │
│  - 5000/batch    │  │  - Confidence scoring            │
│  - TimescaleDB   │  │  - Category-based thresholds     │
└────────┬─────────┘  └────────┬─────────────────────────┘
         │                     │
         ▼                     ▼
┌────────────────────────────────────────────────────────┐
│              TimescaleDB (PostgreSQL)                  │
│  - Hypertables: ticks (1-day chunks)                   │
│  - Continuous Aggregates: candlestick_1m to 1d         │
│  - Auto-compression after 7 days                       │
│  - Tables: ticks, pairs, whale_activities,             │
│             positions, orders                           │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              Trading Engine (Python)                   │
│  - Volume-Weighted Momentum Strategy                   │
│  - Risk Manager (blacklist, limits, viability)         │
│  - Position Management                                 │
│  - Order Execution via Pacifica API                    │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│            API Gateway (FastAPI)                       │
│  Endpoints: /api/v1/pairs, /latest-prices,             │
│             /whales, /positions, /analytics            │
│  - OpenAPI docs at /docs                               │
│  - CORS enabled for frontend                           │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│              NGINX Reverse Proxy                       │
│  - SSL/TLS termination (Let's Encrypt)                 │
│  - Routes /api/* to API Gateway                        │
│  - Routes /* to Frontend                               │
└────────────────────┬───────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│            Frontend Dashboard (Next.js)                │
│  - Real-time price updates (5s polling)                │
│  - Trading signals (10s polling)                       │
│  - Whale activity feed (30s polling)                   │
│  - Position tracking & P&L                             │
└────────────────────────────────────────────────────────┘
```

## Critical Recent Updates

### Risk Management Overhaul (November 15, 2025) - HIGH PRIORITY

**Problem Identified:**
- 8 days of live trading revealed poor performance
- Win rate: 14.6% (unacceptable)
- P&L: -$217 USD
- Trade frequency: 83 trades/day (target: 15-20)

**Root Causes:**
1. Bad symbols bleeding capital (XPL, ASTER, FARTCOIN, etc.)
2. Over-trading on certain pairs
3. Position sizes too small ($10) - fees eating profits
4. Unrealistic profit targets for low volatility assets

**Solutions Implemented:**

1. **Symbol Blacklist** (`src/nexwave/services/trading_engine/risk_manager.py:50-57`)
   - Blocks: XPL, ASTER, FARTCOIN, PENGU, CRV, SUI
   - Combined loss from these: -$176 USD

2. **Trade Frequency Limits**
   - 5-minute cooldown between trades on same symbol
   - Maximum 10 trades per symbol per day
   - Prevents over-trading on volatile pairs

3. **Minimum Position Size**
   - Raised from $10 to $50 USD
   - Ensures fees don't eat into profits
   - Calculated in `risk_manager.py:validate_trade_viability()`

4. **Profit Viability Check**
   - Rejects trades requiring >5% price move
   - Rejects trades with <$2 expected profit after fees
   - Accounts for Pacifica fee structure (0.05% maker, 0.07% taker)

**Expected Results:**
- Trade frequency reduction: 76% (83 → 20 trades/day)
- Win rate improvement: 2-3x (14.6% → 30-45%)
- P&L target: Break-even to +$10-30/day

### Volatility-Adjusted Take Profit (November 15, 2025)

**Problem:**
Fixed 4x ATR targets were unrealistic for low-volatility assets:
- BTC with 0.5% ATR → 2% target = unrealistic
- High volatility meme coins → too conservative

**Solution:** Dynamic profit targets based on ATR
```python
# Low volatility (ATR ≤ 1.5%)
if atr_pct <= VWM_TP_VOLATILITY_THRESHOLD:
    target_pct = random.uniform(VWM_TP_MIN_PROFIT_PCT, VWM_TP_MAX_PROFIT_PCT)
    # 1-5% fixed targets

# High volatility (ATR > 1.5%)
else:
    atr_multiple = random.uniform(VWM_TP_MIN_ATR_MULTIPLE, VWM_TP_MAX_ATR_MULTIPLE)
    target_pct = atr_pct * atr_multiple
    # 2-6x ATR targets
```

**Also Fixed:**
- VWAP query bug preventing candle data retrieval
- File: `src/nexwave/db/queries.py`

### Trading Engine Fixes (November 10, 2025)

**Enabled Live Order Execution:**
1. Lowered volume threshold: 1.2x → 0.5x for off-peak trading
2. Added lot/tick size rounding to comply with Pacifica API
3. First successful live trades: VIRTUAL & FARTCOIN @ 5x leverage

**Key Files:**
- `src/nexwave/services/trading_engine/engine.py`
- `src/nexwave/services/order_management/pacifica_client.py`

### Position Sync & P&L Tracking (November 8, 2025)

- Real-time sync with Pacifica API every 60 seconds
- Accurate P&L calculation for long/short positions
- Proper leverage display from pair configuration
- File: `sync_pacifica_positions.py`

### Data Pipeline Fixes (November 3-7, 2025)

1. **Redis Fix:** Promoted from read-only replica to master
2. **Frontend Routing:** Fixed double `/api/api` prefix issue
3. **WebSocket Format:** Matched Pacifica's array data format
4. **30 Pairs Support:** Expanded from 3 to all 30 Pacifica markets

## Database Schema

### Core Tables

**`ticks` (TimescaleDB Hypertable)**
```sql
CREATE TABLE ticks (
    id SERIAL,
    symbol VARCHAR(20) NOT NULL,
    time TIMESTAMPTZ NOT NULL,
    price DECIMAL(20,8) NOT NULL,
    volume DECIMAL(20,8),
    PRIMARY KEY (symbol, time)
);

-- Converted to hypertable with 1-day chunks
SELECT create_hypertable('ticks', 'time', chunk_time_interval => INTERVAL '1 day');

-- Compression policy (after 7 days)
ALTER TABLE ticks SET (timescaledb.compress);
```

**`pairs` (Trading Pairs Configuration)**
```sql
CREATE TABLE pairs (
    symbol VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    leverage INTEGER NOT NULL,
    category VARCHAR(20) NOT NULL,
    whale_threshold DECIMAL(20,2) NOT NULL,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

**`whale_activities` (Whale Detection)**
```sql
CREATE TABLE whale_activities (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    detected_at TIMESTAMPTZ NOT NULL,
    order_size DECIMAL(20,8) NOT NULL,
    order_value DECIMAL(20,2) NOT NULL,
    confidence_score DECIMAL(5,2) NOT NULL,
    threshold_used DECIMAL(20,2) NOT NULL,
    direction VARCHAR(10),
    FOREIGN KEY (symbol) REFERENCES pairs(symbol)
);
```

**`positions` (Open Positions)**
```sql
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    entry_price DECIMAL(20,8) NOT NULL,
    quantity DECIMAL(20,8) NOT NULL,
    leverage INTEGER NOT NULL,
    unrealized_pnl DECIMAL(20,2),
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    FOREIGN KEY (symbol) REFERENCES pairs(symbol)
);
```

**`orders` (Order Audit Trail)**
```sql
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    order_type VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,
    price DECIMAL(20,8),
    quantity DECIMAL(20,8) NOT NULL,
    status VARCHAR(20) NOT NULL,
    pacifica_order_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    filled_at TIMESTAMPTZ,
    FOREIGN KEY (symbol) REFERENCES pairs(symbol)
);
```

### Continuous Aggregates (Auto-Refreshing Candlesticks)

```sql
-- 1-minute candles
CREATE MATERIALIZED VIEW candlestick_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    FIRST(price, time) AS open,
    MAX(price) AS high,
    MIN(price) AS low,
    LAST(price, time) AS close,
    SUM(volume) AS volume
FROM ticks
GROUP BY bucket, symbol;

-- Similar views for: 5m, 15m, 1h, 4h, 1d
```

### Performance Indexes

```sql
CREATE INDEX idx_ticks_symbol_time ON ticks (symbol, time DESC);
CREATE INDEX idx_whale_activities_symbol_time ON whale_activities (symbol, detected_at DESC);
CREATE INDEX idx_positions_symbol ON positions (symbol);
CREATE INDEX idx_orders_status ON orders (status);
CREATE INDEX idx_orders_symbol_created ON orders (symbol, created_at DESC);
```

## Configuration

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://nexwave:password@postgres:5432/nexwave
POSTGRES_PASSWORD=your_secure_password

# Redis
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=change_me_in_production_use_strong_password

# Pacifica API
PACIFICA_API_URL=https://api.pacifica.fi/api/v1
PACIFICA_WS_URL=wss://ws.pacifica.fi/ws
PACIFICA_API_KEY=your_api_key_here

# Trading Configuration
USE_ALL_PAIRS=true
TRADING_ENABLED=true

# Volume-Weighted Momentum Strategy Parameters
VWM_MOMENTUM_THRESHOLD=0.001      # 0.1% entry signal
VWM_EXIT_THRESHOLD=0.0005         # 0.05% exit signal
VWM_VOLUME_MULTIPLIER=0.5         # Volume filter (0.5x = relaxed for off-peak)
VWM_LOOKBACK_PERIOD=15            # Number of candles to analyze

# Volatility-Adjusted Take Profit
VWM_TP_VOLATILITY_THRESHOLD=0.015 # 1.5% ATR dividing line
VWM_TP_MIN_PROFIT_PCT=1.0         # Minimum 1% profit target
VWM_TP_MAX_PROFIT_PCT=5.0         # Maximum 5% for low volatility
VWM_TP_MIN_ATR_MULTIPLE=2.0       # Minimum 2x ATR for high volatility
VWM_TP_MAX_ATR_MULTIPLE=6.0       # Maximum 6x ATR for high volatility

# Risk Management
RISK_MAX_POSITION_SIZE=1000       # Max position size in USD
RISK_MAX_LEVERAGE=10              # Maximum leverage allowed
RISK_STOP_LOSS_PCT=2.0            # Stop loss percentage
```

### Pair Categories & Whale Thresholds

Configured in `src/nexwave/common/pairs.py`:

| Category   | Pairs | Whale Threshold | Examples |
|------------|-------|-----------------|----------|
| **Major**  | 3     | $25,000         | BTC, ETH, SOL |
| **Mid-Cap**| 10    | $10,000         | HYPE, XRP, AAVE, LINK |
| **Emerging**| 10   | $5,000          | DOGE, MATIC, SUI, ARB |
| **Small-Cap**| 7   | $2,500          | PENGU, LDO, CRV, FTM |

**Total:** 30 trading pairs actively monitored

## Development Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL client (psql)
- Git
- **UV (Python package manager)**

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/nexwave-so/pacifica-operator.git
cd pacifica-operator

# 2. Copy environment variables
cp env.example .env
# Edit .env with your Pacifica API credentials

# 3. Install Python dependencies
uv pip install -e ".[dev]"

# 4. Start all services
docker compose up -d --remove-orphans

# 4. Check service health
docker ps
docker logs nexwave-market-data
docker logs nexwave-api-gateway
docker logs nexwave-frontend

# 5. Access dashboard
# http://localhost:3000 (or your domain)
```

### Running Services Individually (Development)

```bash
# Terminal 1: Market Data Service
python -m src.nexwave.services.market_data.client

# Terminal 2: Database Writer
python -m src.nexwave.services.db_writer.service

# Terminal 3: Whale Tracker
python -m src.nexwave.services.whale_tracker.service

# Terminal 4: Trading Engine (if enabled)
python -m src.nexwave.services.trading_engine.engine

# Terminal 5: API Gateway
python -m src.nexwave.services.api_gateway.main

# Terminal 6: Frontend
cd frontend
npm install
npm run dev
```

### Database Migrations

```bash
# Apply new migration
psql -U nexwave -d nexwave -f migrations/005_new_migration.sql

# Or via Docker
docker exec -i nexwave-postgres psql -U nexwave -d nexwave < migrations/005_new_migration.sql

# Check TimescaleDB chunks
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -c \
  "SELECT * FROM timescaledb_information.chunks WHERE hypertable_name='ticks';"
```

### Docker Commands Reference

**IMPORTANT:** Always use `docker compose` (no dash, V2 syntax)

```bash
# Standard startup
docker compose up -d --remove-orphans

# View logs
docker compose logs -f market-data
docker compose logs -f api-gateway --tail=100

# Restart specific service
docker compose restart trading-engine

# Full rebuild (after code changes)
docker compose down
docker compose build --no-cache
docker compose up -d --remove-orphans

# Rebuild single service without affecting others
docker compose up -d --build --no-cache --no-deps --remove-orphans frontend

# Stop all services
docker compose down

# Stop and remove volumes (DANGER: deletes all data!)
docker compose down -v

# Weekly maintenance (clean up unused images/containers)
docker system prune -a --volumes -f
```

### Frontend Development

```bash
cd frontend

# Install dependencies
npm install

# Development server (hot reload)
npm run dev

# Production build
npm run build

# Type checking
npm run type-check

# Linting
npm run lint
```

## API Reference

### Base URL
- Development: `http://localhost:8000`
- Production: `https://nexwave.so/api`

### Interactive Documentation
- Swagger UI: `/docs`
- ReDoc: `/redoc`

### Endpoints

**GET /api/v1/pairs**
- Returns all 30 trading pairs with metadata
- Response includes: symbol, name, leverage, category, whale_threshold

**GET /api/v1/latest-prices**
- Real-time prices for all pairs
- Includes 24h change percentage
- Cached in Redis (5s TTL)

**GET /api/v1/whales**
- Recent whale activity
- Query params: `?symbol=BTC` (optional filter)
- Returns: order_size, order_value, confidence_score, timestamp

**GET /api/v1/positions**
- Current open positions
- Returns: symbol, side, entry_price, quantity, leverage, unrealized_pnl

**GET /api/analytics**
- Dashboard analytics summary
- Returns: total_volume, active_pairs, whale_count, position_count

**POST /api/v1/orders**
- Place new order (authenticated)
- Body: `{symbol, side, order_type, quantity, price?}`

## Trading Strategy: Volume-Weighted Momentum (VWM)

### Strategy Logic

**Entry Conditions:**
1. Price momentum > 0.1% over 15 candles
2. Volume > 0.5x average (relaxed for off-peak)
3. Symbol not in blacklist
4. Passes trade frequency limits
5. Passes viability check (fees, profit potential)

**Exit Conditions:**
1. Take Profit: Volatility-adjusted (1-5% or 2-6x ATR)
2. Stop Loss: 2% fixed (configurable)
3. Momentum reversal: < 0.05% threshold

**Position Sizing:**
```python
position_size = min(
    RISK_MAX_POSITION_SIZE,
    account_balance * 0.02  # 2% risk per trade
)
```

**Leverage:**
- Determined per pair (1x to 10x)
- Major pairs: 3-5x
- Mid-cap: 5-7x
- Emerging/Small-cap: 7-10x

### Risk Management Features

1. **Symbol Blacklist**
   - File: `src/nexwave/services/trading_engine/risk_manager.py`
   - Blocks: XPL, ASTER, FARTCOIN, PENGU, CRV, SUI

2. **Trade Frequency Limits**
   - 5-minute cooldown per symbol
   - Max 10 trades per symbol per day

3. **Profit Viability Check**
   ```python
   def validate_trade_viability(self, symbol, entry_price, quantity):
       # Check position size
       if position_value < 50:  # $50 minimum
           return False

       # Check required price move
       if required_move_pct > 5.0:  # >5% unrealistic
           return False

       # Check expected profit after fees
       if net_profit < 2.0:  # <$2 not worth it
           return False
   ```

4. **Max Drawdown Protection**
   - Daily loss limit: 5% of account
   - Pauses trading if exceeded

## Common Issues & Troubleshooting

### Dashboard Not Loading / 502 Bad Gateway

**Cause:** NGINX caches old container IP addresses after restart

**Solution:**
```bash
docker restart nexwave-nginx

# Verify API Gateway is reachable
docker exec nexwave-nginx wget -q -O- http://api-gateway:8000/health
```

### Dashboard Shows Spinners But No Data

**Cause:** Double `/api/api` prefix in frontend routes

**Solution:**
```bash
# Rebuild frontend
docker compose up -d --build --no-deps --no-cache frontend

# Hard refresh browser
# Ctrl+Shift+R (Chrome/Firefox) or Cmd+Shift+R (Mac)
```

**Verify Fix:**
Open browser console (F12), check Network tab for 404 errors

### WebSocket Not Connecting

**Cause:** Incorrect Pacifica URLs or network issues

**Debug:**
```bash
# Check market data service logs
docker logs nexwave-market-data --tail=50

# Verify environment variables
docker exec nexwave-market-data env | grep PACIFICA

# Test WebSocket manually
wscat -c wss://ws.pacifica.fi/ws
```

**Solution:**
- Verify `PACIFICA_WS_URL` in `.env`
- Check Pacifica API status: https://status.pacifica.fi
- Restart market data service: `docker compose restart market-data`

### No Trades Executing

**Possible Causes:**
1. Symbol in blacklist
2. Volume threshold too high
3. Trade frequency limits exceeded
4. Viability check failing

**Debug:**
```bash
# Check trading engine logs
docker logs nexwave-trading-engine --tail=100

# Check risk manager decisions
grep "REJECTED" logs/trading_engine.log

# Verify configuration
docker exec nexwave-trading-engine env | grep VWM_
```

**Solution:**
- Check `VWM_VOLUME_MULTIPLIER` (should be 0.5 for off-peak)
- Verify symbol not in blacklist: XPL, ASTER, FARTCOIN, PENGU, CRV, SUI
- Check last trade time: `SELECT * FROM orders WHERE symbol='BTC' ORDER BY created_at DESC LIMIT 5;`

### Database Connection Errors

**Cause:** PostgreSQL not ready or connection pool exhausted

**Solution:**
```bash
# Check PostgreSQL health
docker exec nexwave-postgres pg_isready -U nexwave

# Check active connections
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -c \
  "SELECT count(*) FROM pg_stat_activity WHERE datname='nexwave';"

# Restart database (last resort - will interrupt services)
docker compose restart postgres
```

### Redis Connection Errors

**Cause:** Redis password mismatch or service down

**Solution:**
```bash
# Test Redis connection
docker exec -it nexwave-redis redis-cli -a your_redis_password ping

# Check Redis logs
docker logs nexwave-redis

# Verify password in .env matches docker-compose.yml
```

### Frontend Build Errors

**Cause:** Dependency issues or TypeScript errors

**Solution:**
```bash
cd frontend

# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Check for TypeScript errors
npm run type-check

# Rebuild
npm run build
```

## Code Style & Best Practices

### Python

**Style Guidelines:**
- Use `async`/`await` for all I/O operations
- Python 3.11+ type hints everywhere
- Google-style docstrings
- `snake_case` for functions/variables
- `PascalCase` for classes

**Example:**
```python
async def fetch_market_data(symbol: str) -> Optional[MarketData]:
    """Fetches market data for a given symbol.

    Args:
        symbol: Trading pair symbol (e.g., 'BTC', 'ETH')

    Returns:
        MarketData object if successful, None otherwise

    Raises:
        ConnectionError: If WebSocket connection fails
    """
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/markets/{symbol}") as response:
            data = await response.json()
            return MarketData.parse_obj(data)
```

**FastAPI Endpoints:**
```python
@router.get("/pairs", response_model=List[PairSchema])
async def get_pairs(
    db: AsyncSession = Depends(get_db),
    category: Optional[str] = Query(None, description="Filter by category")
) -> List[PairSchema]:
    """Get all trading pairs with optional category filter."""
    query = select(Pair)
    if category:
        query = query.where(Pair.category == category)
    result = await db.execute(query)
    return result.scalars().all()
```

### TypeScript

**Style Guidelines:**
- Strict mode enabled in `tsconfig.json`
- Interfaces over types
- Functional components with hooks
- `camelCase` for variables/functions
- `PascalCase` for components/interfaces

**Example Component:**
```typescript
interface PriceCardProps {
  symbol: string;
  price: number;
  change24h: number;
}

export const PriceCard: React.FC<PriceCardProps> = ({
  symbol,
  price,
  change24h
}) => {
  const isPositive = change24h >= 0;

  return (
    <div className="bg-nexwave-dark rounded-lg p-4">
      <h3 className="text-xl font-bold">{symbol}</h3>
      <p className="text-2xl">${price.toFixed(2)}</p>
      <p className={isPositive ? "text-green-500" : "text-red-500"}>
        {isPositive ? "+" : ""}{change24h.toFixed(2)}%
      </p>
    </div>
  );
};
```

**API Hooks:**
```typescript
export const useMarketData = (symbol: string) => {
  const [data, setData] = useState<MarketData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`/api/v1/latest-prices?symbol=${symbol}`);
        const json = await response.json();
        setData(json);
      } catch (err) {
        setError(err as Error);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, [symbol]);

  return { data, loading, error };
};
```

### Database

**Guidelines:**
- Always use indexes on (symbol, time) for time-series queries
- Never modify existing migrations, create new ones
- Use foreign keys for referential integrity
- Use transactions for multi-table updates

**Example Migration:**
```sql
-- migrations/006_add_performance_metrics.sql
BEGIN;

CREATE TABLE performance_metrics (
    id SERIAL PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    win_rate DECIMAL(5,2) NOT NULL,
    total_trades INTEGER NOT NULL,
    net_pnl DECIMAL(20,2) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    FOREIGN KEY (symbol) REFERENCES pairs(symbol),
    UNIQUE(symbol, date)
);

CREATE INDEX idx_performance_metrics_symbol_date
ON performance_metrics (symbol, date DESC);

COMMIT;
```

## Performance Optimization

### Backend Optimization

1. **TimescaleDB Continuous Aggregates**
   - Pre-computed candlesticks (1m, 5m, 15m, 1h, 4h, 1d)
   - Auto-refresh on new data
   - 100x faster than on-demand aggregation

2. **Batch Inserts**
   - DB Writer batches 5000 ticks before insert
   - Reduces write overhead by 95%
   - File: `src/nexwave/services/db_writer/service.py`

3. **Redis Caching**
   - Latest prices cached (5s TTL)
   - Reduces database load by 80%
   - Invalidated on new tick data

4. **Connection Pooling**
   - PostgreSQL: 20 connections per service
   - Redis: Connection pool with auto-reconnect
   - Async database driver (asyncpg)

5. **Single WebSocket Connection**
   - One connection per service (not per pair)
   - Subscribe to all 30 pairs on single socket
   - Auto-reconnect with exponential backoff

### Frontend Optimization

1. **Staggered Polling**
   - Prices: 5s (time-critical)
   - Trading signals: 10s (moderate)
   - Whale activity: 30s (low priority)

2. **Input Debouncing**
   - Search input debounced (300ms)
   - Prevents excessive re-renders

3. **Memoization**
   ```typescript
   const filteredPairs = useMemo(() => {
     return pairs.filter(p => p.symbol.includes(searchTerm));
   }, [pairs, searchTerm]);
   ```

4. **Code Splitting**
   - Dynamic imports for routes
   - Reduces initial bundle size
   ```typescript
   const Dashboard = dynamic(() => import('./Dashboard'), {
     loading: () => <LoadingSpinner />
   });
   ```

5. **Image Optimization**
   - Next.js Image component
   - Automatic WebP conversion
   - Lazy loading

### Database Query Optimization

**Bad Query:**
```sql
-- Scans entire table
SELECT * FROM ticks WHERE symbol = 'BTC' ORDER BY time DESC LIMIT 100;
```

**Good Query:**
```sql
-- Uses index, TimescaleDB chunk pruning
SELECT time, price, volume
FROM ticks
WHERE symbol = 'BTC'
  AND time > NOW() - INTERVAL '1 hour'
ORDER BY time DESC
LIMIT 100;
```

**Use Continuous Aggregates:**
```sql
-- Instead of aggregating raw ticks
SELECT * FROM candlestick_5m
WHERE symbol = 'BTC'
  AND bucket > NOW() - INTERVAL '24 hours'
ORDER BY bucket DESC;
```

## Testing

### Python Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_risk_manager.py

# Run with coverage
pytest --cov=src/nexwave --cov-report=html

# Run specific test
pytest tests/test_risk_manager.py::test_symbol_blacklist
```

**Example Test:**
```python
import pytest
from src.nexwave.services.trading_engine.risk_manager import RiskManager

@pytest.fixture
def risk_manager():
    return RiskManager()

def test_symbol_blacklist(risk_manager):
    """Test that blacklisted symbols are rejected."""
    blacklisted = ["XPL", "ASTER", "FARTCOIN"]

    for symbol in blacklisted:
        result = risk_manager.validate_symbol(symbol)
        assert result is False, f"{symbol} should be blacklisted"

def test_trade_frequency_limit(risk_manager):
    """Test that trade frequency limits are enforced."""
    symbol = "BTC"

    # First trade should pass
    assert risk_manager.check_trade_frequency(symbol) is True

    # Immediate second trade should fail (5-min cooldown)
    assert risk_manager.check_trade_frequency(symbol) is False
```

### Frontend Tests

```bash
cd frontend

# Run tests
npm test

# Run tests in watch mode
npm test -- --watch

# Run tests with coverage
npm test -- --coverage
```

### Integration Tests

```bash
# End-to-end test (requires all services running)
python test_end_to_end.py

# Order placement test
python test_order_debug.py

# Strategy test
python test_vwm_strategy.py
```

### Manual Testing Checklist

See `docs/DASHBOARD_TESTING.md` for comprehensive testing procedures.

**Quick Checks:**
1. Dashboard loads without errors
2. Latest prices update every 5s
3. Whale activity feed shows recent alerts
4. Position table shows accurate P&L
5. Chart displays correctly for all timeframes

## Monitoring & Observability

### Service Logs

```bash
# View all logs
docker compose logs -f

# Specific service logs
docker logs -f nexwave-market-data
docker logs -f nexwave-trading-engine --tail=100

# Follow trading signals
./monitor_live.sh

# Watch order placement
./monitor_order_placement.sh

# Real-time order monitoring
./monitor_orders_realtime.sh
```

### Health Checks

**API Gateway Health:**
```bash
curl http://localhost:8000/health
```

**Database Health:**
```bash
docker exec -it nexwave-postgres psql -U nexwave -d nexwave -c \
  "SELECT
    (SELECT COUNT(*) FROM ticks) as tick_count,
    (SELECT COUNT(*) FROM positions WHERE closed_at IS NULL) as open_positions,
    (SELECT COUNT(*) FROM whale_activities WHERE detected_at > NOW() - INTERVAL '1 hour') as recent_whales;"
```

**Redis Health:**
```bash
docker exec -it nexwave-redis redis-cli -a your_password INFO stats
```

### Performance Metrics

**Database Write Rate:**
```sql
SELECT
  hypertable_name,
  num_chunks,
  uncompressed_heap_size,
  compressed_heap_size,
  compression_ratio
FROM timescaledb_information.compressed_hypertable_stats
WHERE hypertable_name = 'ticks';
```

**API Response Times:**
```bash
# Using Apache Bench
ab -n 1000 -c 10 http://localhost:8000/api/v1/latest-prices
```

**Trading Performance:**
```sql
SELECT
  symbol,
  COUNT(*) as total_trades,
  SUM(CASE WHEN unrealized_pnl > 0 THEN 1 ELSE 0 END) as winning_trades,
  ROUND(AVG(unrealized_pnl), 2) as avg_pnl,
  ROUND(SUM(unrealized_pnl), 2) as total_pnl
FROM positions
WHERE opened_at > NOW() - INTERVAL '24 hours'
GROUP BY symbol
ORDER BY total_pnl DESC;
```

## Deployment

### Production Stack

```
Internet
  ↓
Cloudflare (DDoS protection, CDN)
  ↓
NGINX (SSL/TLS termination)
  ↓
Docker Compose Services
  ├── Frontend (Next.js)
  ├── API Gateway (FastAPI)
  ├── Trading Engine
  ├── Market Data Service
  ├── DB Writer
  ├── Whale Tracker
  ├── PostgreSQL (TimescaleDB)
  ├── Redis
  └── Kafka + Zookeeper
```

### SSL/TLS Setup

**Using Let's Encrypt:**
```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d nexwave.so -d www.nexwave.so

# Auto-renewal is configured via cron
sudo certbot renew --dry-run
```

**NGINX Configuration:**
```nginx
server {
    listen 443 ssl http2;
    server_name nexwave.so;

    ssl_certificate /etc/letsencrypt/live/nexwave.so/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/nexwave.so/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location /api/ {
        proxy_pass http://api-gateway:8000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        proxy_pass http://frontend:3000/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Environment-Specific Configuration

**Development (.env.dev):**
```bash
TRADING_ENABLED=false
LOG_LEVEL=DEBUG
```

**Production (.env.prod):**
```bash
TRADING_ENABLED=true
LOG_LEVEL=INFO
SENTRY_DSN=your_sentry_dsn
```

### Backup & Recovery

**Database Backup:**
```bash
# Backup (run daily via cron)
docker exec nexwave-postgres pg_dump -U nexwave -Fc nexwave > backups/nexwave_$(date +%Y%m%d).dump

# Restore
docker exec -i nexwave-postgres pg_restore -U nexwave -d nexwave < backups/nexwave_20251205.dump
```

**Volume Backup:**
```bash
# Backup Docker volumes
docker run --rm -v nexwave_postgres_data:/data -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_data_$(date +%Y%m%d).tar.gz -C /data .
```

### Monitoring Targets

- API response time: < 50ms (p95)
- Database write rate: > 5000 ticks/second
- WebSocket uptime: 99.99%
- Dashboard load time: < 2s
- Trade execution latency: < 100ms

## x402 Integration (Future)

**Vision:** Enable AI agents to access Nexwave data via HTTP 402 micropayments on Solana.

**Pricing Model:**
- Whale alerts: $0.0001 per alert
- Order book snapshots: $0.00005 per snapshot
- Candle data: $0.00002 per candle
- Position tracking: $0.0005 per snapshot

**Architecture:**
```
AI Agent
  ↓
Payment Gateway (Solana x402)
  ↓
Agent SDK (authentication + billing)
  ↓
API Middleware (rate limiting + metering)
  ↓
Nexwave API
  ↓
Agent Dashboard (usage analytics)
```

**Implementation Files:**
- `src/nexwave/services/api_gateway/x402_middleware.py`
- `test_x402_payment.py`
- `docs/X402_IMPLEMENTATION.md`

## Resources & Documentation

### Project Documentation
- **[README.md](README.md)** - Project overview and quickstart
- **[PAIRS_IMPLEMENTATION.md](docs/PAIRS_IMPLEMENTATION.md)** - 30-pair implementation guide
- **[DASHBOARD_TESTING.md](docs/DASHBOARD_TESTING.md)** - Testing procedures
- **[TRADING_PARAMS_UPDATE_2025-11-16.md](TRADING_PARAMS_UPDATE_2025-11-16.md)** - Latest parameter changes
- **[TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)** - Comprehensive troubleshooting guide
- **[2025-12-06_data-pipeline-diagnostic.md](docs/diagnostics/2025-12-06_data-pipeline-diagnostic.md)** - Data pipeline diagnostic report
- **[X402_IMPLEMENTATION.md](docs/X402_IMPLEMENTATION.md)** - x402 integration details

### API Documentation
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### External Resources
- **Pacifica DEX:** https://pacifica.fi
- **Pacifica API Docs:** https://docs.pacifica.fi
- **TimescaleDB Docs:** https://docs.timescale.com
- **FastAPI Docs:** https://fastapi.tiangolo.com
- **Next.js Docs:** https://nextjs.org/docs

### Community & Support
- **GitHub:** https://github.com/nexwave-so/pacifica-operator
- **Website:** https://nexwave.so
- **Twitter:** https://x.com/nexwave_so

## Key File Locations

### Backend
- **Trading Engine:** `src/nexwave/services/trading_engine/engine.py`
- **Risk Manager:** `src/nexwave/services/trading_engine/risk_manager.py`
- **Strategy:** `src/nexwave/strategies/volume_weighted_momentum_strategy.py`
- **Market Data:** `src/nexwave/services/market_data/client.py`
- **API Gateway:** `src/nexwave/services/api_gateway/main.py`
- **Database Models:** `src/nexwave/db/models.py`
- **Database Queries:** `src/nexwave/db/queries.py`
- **Pair Config:** `src/nexwave/common/pairs.py`

### Frontend
- **Dashboard:** `frontend/app/dashboard/page.tsx`
- **Price Cards:** `frontend/components/dashboard/price-cards.tsx`
- **Whale Feed:** `frontend/components/dashboard/whale-activity.tsx`
- **Positions Table:** `frontend/components/dashboard/positions-table.tsx`
- **API Hooks:** `frontend/lib/api.ts`

### Configuration
- **Docker Compose:** `docker-compose.yml`
- **Environment:** `.env`
- **NGINX:** `nginx/nginx.conf`
- **Migrations:** `migrations/*.sql`

### Scripts
- **Position Sync:** `sync_pacifica_positions.py`
- **Trading Status:** `check_trading_status.py`
- **Close Positions:** `close_all_positions.py`
- **Live Monitor:** `monitor_live.sh`

## Getting Help

### Debugging Process

1. **Check Service Status**
   ```bash
   docker ps
   docker compose logs --tail=50
   ```

2. **Verify Configuration**
   ```bash
   # Check environment variables
   docker exec nexwave-api-gateway env | grep -E "(PACIFICA|DATABASE|REDIS)"
   ```

3. **Test Connectivity**
   ```bash
   # Database
   docker exec -it nexwave-postgres psql -U nexwave -d nexwave -c "SELECT 1;"

   # Redis
   docker exec -it nexwave-redis redis-cli -a password ping

   # API Gateway
   curl http://localhost:8000/health
   ```

4. **Review Logs**
   ```bash
   # Service-specific
   docker logs nexwave-market-data --tail=100

   # Search for errors
   docker compose logs | grep -i error
   ```

5. **Check Database State**
   ```sql
   -- Recent ticks
   SELECT symbol, time, price FROM ticks ORDER BY time DESC LIMIT 10;

   -- Open positions
   SELECT * FROM positions WHERE closed_at IS NULL;

   -- Recent orders
   SELECT * FROM orders ORDER BY created_at DESC LIMIT 10;
   ```

### Common Error Messages

**"Connection refused"**
- Service not running or wrong port
- Solution: Check `docker ps` and restart service

**"psycopg2.OperationalError: FATAL: password authentication failed"**
- Wrong database credentials
- Solution: Verify `DATABASE_URL` in `.env`

**"redis.exceptions.ConnectionError: Error 10061"**
- Redis not accessible or wrong password
- Solution: Check `REDIS_PASSWORD` matches in all configs

**"WebSocket connection failed"**
- Pacifica API down or incorrect URL
- Solution: Verify `PACIFICA_WS_URL` and check status page

**"Rate limit exceeded"**
- Too many API requests to Pacifica
- Solution: Increase polling intervals or contact Pacifica for higher limits

### Support Channels

For issues specific to:
- **Nexwave:** Open GitHub issue at https://github.com/nexwave-so/pacifica-operator/issues
- **Pacifica API:** Contact via Discord or support@pacifica.fi

---

**Last Updated:** January 29, 2026
**Version:** 2.5.0 (Backend-only architecture)
**Operated by:** Nexwave and an [OpenClaw](https://github.com/openclaw/openclaw) Agent
**For:** Google AI Engineers using Gemini
