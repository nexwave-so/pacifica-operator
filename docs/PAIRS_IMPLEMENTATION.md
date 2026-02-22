# Nexwave: All 30 Pacifica Pairs Implementation

## Overview

Successfully expanded Nexwave to support all 30 trading pairs from Pacifica DEX (up from the original 3 pairs: BTC, ETH, SOL).

## Implementation Summary

### ✅ Completed

#### 1. Backend Infrastructure

**New Files:**
- `src/nexwave/common/pairs.py` - Centralized configuration for all 30 pairs
- `migrations/004_add_pairs_table.sql` - Database schema for pairs metadata

**Updated Files:**
- `src/nexwave/common/config.py` - Dynamic pair loading from pairs.py
- `src/nexwave/services/api_gateway/main.py` - New /api/v1/pairs endpoint, updated /api/v1/latest-prices
- `src/nexwave/services/whale_tracker/detector.py` - Pair-specific whale thresholds

#### 2. Frontend Components

**Updated Files:**
- `frontend/components/dashboard/market-prices.tsx` - Search, filter, sort for all 30 pairs
- `frontend/components/dashboard/whale-activity.tsx` - Symbol and category filters

### Pairs by Category (30 Total)

#### Major (3 pairs)
- **BTC** (50x leverage) - $25K whale threshold
- **ETH** (50x leverage) - $25K whale threshold
- **SOL** (20x leverage) - $25K whale threshold

#### Mid-Cap (7 pairs)
- **HYPE** (20x leverage) - $10K whale threshold
- **ZEC** (10x leverage) - $10K whale threshold
- **BNB** (10x leverage) - $10K whale threshold
- **XRP** (20x leverage) - $10K whale threshold
- **PUMP** (5x leverage) - $10K whale threshold
- **AAVE** (10x leverage) - $10K whale threshold
- **ENA** (10x leverage) - $10K whale threshold

#### Emerging (14 pairs)
- **ASTER** (5x) - $5K threshold
- **kBONK** (10x) - $5K threshold (1000x units)
- **kPEPE** (10x) - $5K threshold (1000x units)
- **LTC** (10x) - $5K threshold
- **PAXG** (10x) - $5K threshold
- **VIRTUAL** (5x) - $5K threshold
- **SUI** (10x) - $5K threshold
- **FARTCOIN** (10x) - $5K threshold
- **TAO** (10x) - $5K threshold
- **DOGE** (15x) - $5K threshold
- **XPL** (10x) - $5K threshold
- **AVAX** (10x) - $5K threshold
- **LINK** (10x) - $5K threshold
- **UNI** (10x) - $5K threshold

#### Small-Cap (6 pairs)
- **WLFI** (5x) - $2.5K threshold
- **PENGU** (5x) - $2.5K threshold
- **2Z** (3x) - $2.5K threshold
- **MON** (3x) - $2.5K threshold
- **LDO** (10x) - $2.5K threshold
- **CRV** (10x) - $2.5K threshold

## New API Endpoints

### GET /api/v1/pairs
Returns all trading pairs with metadata.

**Query Parameters:**
- `category` (optional): Filter by category (major, mid-cap, emerging, small-cap)
- `active_only` (default: true): Only return active pairs

**Response:**
```json
{
  "pairs": [
    {
      "symbol": "BTC",
      "quote": "USD",
      "max_leverage": 50,
      "min_order_size": 0.001,
      "tick_size": 0.1,
      "display_name": "Bitcoin",
      "category": "major",
      "whale_threshold_usd": 25000,
      "is_active": true
    }
  ],
  "count": 30
}
```

### GET /api/v1/latest-prices (Updated)
Now supports all 30 pairs with filtering.

**Query Parameters:**
- `symbols` (optional): Comma-separated list of symbols (e.g., "BTC,ETH,SOL")
- If omitted, returns all active pairs

**Response:**
```json
{
  "prices": [
    {
      "symbol": "BTC",
      "display_name": "Bitcoin",
      "price": 95234.50,
      "time": "2025-11-01T12:00:00Z",
      "change_24h_pct": 2.35,
      "bid": 95230.00,
      "ask": 95240.00,
      "category": "major"
    }
  ],
  "count": 30
}
```

## Configuration

### Environment Variables

Set in `.env` to control pair loading:
```bash
# Use all pairs from pairs.py
USE_ALL_PAIRS=true

# Or specify specific pairs (legacy mode)
USE_ALL_PAIRS=false
SYMBOLS=BTC,ETH,SOL
```

### Adding New Pairs

To add a new pair, edit `src/nexwave/common/pairs.py`:

```python
PairConfig(
    symbol="NEWTOKEN",
    quote_asset="USD",
    max_leverage=10,
    min_order_size=1.0,
    tick_size=0.0001,
    display_name="New Token",
    category=PairCategory.EMERGING,
    whale_threshold_usd=5000,
)
```

Then run the database migration to add it to the `pairs` table.

## Database Migration

Run the migration to create the `pairs` table:

```bash
psql -U nexwave -d nexwave -f migrations/004_add_pairs_table.sql
```

**Migration includes:**
- Creates `pairs` table with all metadata
- Inserts all 30 pairs with proper configuration
- Adds foreign key constraints to existing tables
- Creates indexes for efficient querying

## Frontend Features

### Market Prices Component
- **Search**: Filter pairs by symbol or name
- **Category Filter**: View pairs by category (All, Major, Mid-Cap, Emerging, Small-Cap)
- **Sorting**: Sort by symbol, price, or 24h change
- **Scrollable**: Handles 30+ pairs with smooth scrolling
- **Category Badges**: Color-coded badges for each pair category

### Whale Activity Component
- **Category Dropdown**: Filter by pair category
- **Symbol Dropdown**: Select specific pair within category
- **All Pairs View**: View whale activity across all pairs
- **Symbol Badges**: Show which pair each whale activity belongs to

## Whale Detection Thresholds

Whale detection thresholds are now category-specific:

```python
WHALE_THRESHOLDS = {
    'major': 25000,      # BTC, ETH, SOL
    'mid-cap': 10000,    # HYPE, XRP, AAVE, etc.
    'emerging': 5000,    # SUI, VIRTUAL, LINK, etc.
    'small-cap': 2500    # PENGU, 2Z, MON, etc.
}
```

This ensures whale detection is appropriate for each pair's typical volume and liquidity.

## Next Steps (Not Yet Implemented)

### 1. WebSocket Subscriptions
The WebSocket client (`src/nexwave/services/market_data/client.py`) already uses `settings.symbol_list`, which now returns all 30 pairs. **No code changes needed** - it will automatically subscribe to all pairs.

To test:
```bash
python -m nexwave.services.market_data.client
```

### 2. Database Initialization
Run the migration to populate the `pairs` table:
```bash
psql -U nexwave -d nexwave -f migrations/004_add_pairs_table.sql
```

### 3. Data Verification
After running the data ingestion service, verify all pairs are receiving data:
```sql
SELECT symbol, COUNT(*) as tick_count, MAX(time) as latest_tick
FROM ticks
WHERE time > NOW() - INTERVAL '1 hour'
GROUP BY symbol
ORDER BY symbol;
```

### 4. Performance Testing
Monitor performance with 30 concurrent streams:
- Database write throughput
- API response times
- Memory usage
- WebSocket connection stability

### 5. Frontend Data Fetching
Update the `useMarketPrices` hook to fetch from the new `/api/v1/latest-prices` endpoint to get all pairs.

### 6. Continuous Aggregates
Ensure TimescaleDB continuous aggregates (candlesticks) work for all 30 pairs:
```sql
SELECT symbol, COUNT(*) as candle_count
FROM candlestick_1h
WHERE time > NOW() - INTERVAL '24 hours'
GROUP BY symbol
ORDER BY symbol;
```

## Testing

### Backend Testing
```bash
# Test pairs endpoint
curl http://localhost:8000/api/v1/pairs

# Test latest prices for all pairs
curl http://localhost:8000/api/v1/latest-prices

# Test latest prices for specific pairs
curl http://localhost:8000/api/v1/latest-prices?symbols=BTC,ETH,SOL

# Test whale activity with symbol filter
curl http://localhost:8000/api/v1/whales?symbol=BTC&min_value_usd=25000
```

### Frontend Testing
1. Open dashboard at http://localhost:3000/dashboard
2. Verify Market Prices shows all 30 pairs
3. Test search functionality
4. Test category filtering
5. Test sorting options
6. Verify Whale Activity symbol filter works
7. Check mobile responsiveness with 30+ pairs

## Configuration Reference

### pairs.py Structure
```python
@dataclass
class PairConfig:
    symbol: str              # Trading symbol (e.g., "BTC")
    quote_asset: str         # Quote currency (always "USD")
    max_leverage: int        # Maximum leverage (3-50x)
    min_order_size: float    # Minimum order size
    tick_size: float         # Price increment
    display_name: str        # Human-readable name
    category: PairCategory   # MAJOR, MID_CAP, EMERGING, SMALL_CAP
    is_active: bool         # Whether pair is tradeable
    whale_threshold_usd: float  # Whale detection threshold
```

## Known Issues

1. **"k" Prefix Pairs**: kBONK and kPEPE represent 1000x units. Ensure UI displays correctly.
2. **Low Liquidity Pairs**: Some small-cap pairs may have sporadic data. Consider adding "No Activity" indicators.
3. **CRV Leverage**: Leverage was unknown, defaulted to 10x. Verify with Pacifica.

## Monitoring

Key metrics to track:
- Pair coverage (% of pairs with recent data)
- Whale detection rate per category
- API response times with 30 pairs
- Database query performance
- WebSocket connection stability

## Support

For issues or questions:
- Backend: Check `src/nexwave/common/pairs.py` configuration
- Frontend: Check dashboard components in `frontend/components/dashboard/`
- Database: Run `migrations/004_add_pairs_table.sql`
- API: Test with `curl` commands above

---

**Last Updated**: 2025-11-01
**Version**: 1.0.0
**Pairs Supported**: 30 (BTC, ETH, SOL, HYPE, ZEC, BNB, XRP, PUMP, AAVE, ENA, ASTER, kBONK, kPEPE, LTC, PAXG, VIRTUAL, SUI, FARTCOIN, TAO, DOGE, XPL, AVAX, LINK, UNI, WLFI, PENGU, 2Z, MON, LDO, CRV)
