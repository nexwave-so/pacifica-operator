# Fix: kBONK and kPEPE Market Data Retrieval

**Date:** November 8, 2025  
**Issue:** Market data warnings for kBONK and kPEPE symbols  
**Status:** ✅ RESOLVED

---

## Problem Summary

The trading engine was showing warnings:
```
⚠️  No market data available for kBONK, skipping signal generation
⚠️  No market data available for kPEPE, skipping signal generation
```

Despite having 151k+ ticks in the database for both symbols.

---

## Root Cause Analysis

### Issue 1: Market Data Query Case Sensitivity

**Location:** `src/nexwave/services/trading_engine/engine.py:get_market_data()`

**Problem:**
- Database stores symbols as `kBONK` and `kPEPE` (lowercase 'k')
- Query was using `.upper()` which converts to `KBONK`/`KPEPE`
- No match found → "No market data available" warning

**Fix:**
- Try exact symbol match first (case-sensitive)
- Fallback to uppercase match for other symbols
- Added debug logging when using database fallback

### Issue 2: Candle Query Case Sensitivity

**Location:** `src/nexwave/db/queries.py`

**Problem:**
- All candle query functions (`get_candles()`, `get_candles_count()`, `get_price_statistics()`) were using `.upper()`
- This converted `kBONK` → `KBONK`, causing no matches
- Result: "Not enough candles: 0 < 15" warnings

**Fix:**
- Try exact symbol match first (case-sensitive) in all functions
- Fallback to uppercase match for other symbols
- Applied to:
  - `get_candles()`
  - `get_candles_count()`
  - `get_price_statistics()`

---

## Changes Made

### File 1: `src/nexwave/services/trading_engine/engine.py`

**Function:** `get_market_data()`

**Before:**
```python
query = (
    select(Tick)
    .where(Tick.symbol == symbol.upper())  # ❌ Converts kBONK → KBONK
    .order_by(Tick.time.desc())
    .limit(1)
)
```

**After:**
```python
# Try exact symbol match first (case-sensitive)
query = (
    select(Tick)
    .where(Tick.symbol == symbol)  # ✅ Handles kBONK correctly
    .order_by(Tick.time.desc())
    .limit(1)
)
result = await session.execute(query)
tick = result.scalar_one_or_none()

# If not found, try uppercase (for other symbols)
if not tick:
    query = (
        select(Tick)
        .where(Tick.symbol == symbol.upper())
        .order_by(Tick.time.desc())
        .limit(1)
    )
    result = await session.execute(query)
    tick = result.scalar_one_or_none()
```

### File 2: `src/nexwave/db/queries.py`

**Functions Updated:**
1. `get_candles()` - Line 62-85
2. `get_candles_count()` - Line 144-164
3. `get_price_statistics()` - Line 199-219

**Pattern Applied:**
```python
# Before: params = {"symbol": symbol.upper()}  # ❌

# After:
params = {"symbol": symbol}  # ✅ Try exact match first
result = await session.execute(text(query), params)
rows = result.fetchall()

# If no results, try uppercase
if not rows:
    params_upper = params.copy()
    params_upper["symbol"] = symbol.upper()
    result = await session.execute(text(query), params_upper)
    rows = result.fetchall()
```

---

## Verification

### Before Fix
```
⚠️  No market data available for kBONK, skipping signal generation
⚠️  Not enough candles for kBONK: 0 < 15. Need 15 more candles.
```

### After Fix
```
✅ Retrieved market data for kBONK from database (fallback)
✅ kBONK Signal Check: VWM=-0.000406... Candles=25
✅ kPEPE Signal Check: VWM=-0.000140... Candles=25
```

### Database Verification
- **Ticks:** 151k+ for both kBONK and kPEPE ✅
- **Candles:** 406 candles each in `candles_15m_ohlcv` ✅
- **Latest Data:** Current (within seconds) ✅

---

## Impact

### Before
- ❌ Market data warnings for kBONK and kPEPE
- ❌ No signal generation for these symbols
- ❌ "Not enough candles" errors
- ❌ Trading engine skipping 2 out of 30 symbols

### After
- ✅ Market data retrieved successfully
- ✅ Candles found (25+ available)
- ✅ Signal generation working
- ✅ All 30 symbols being processed

---

## Technical Details

### Why This Happened

Symbols with mixed case (like `kBONK`, `kPEPE`) require case-sensitive matching:
- Database stores: `kBONK` (lowercase 'k')
- `.upper()` converts to: `KBONK` (uppercase 'K')
- No match → Query fails

### Solution Pattern

The fix uses a two-step approach:
1. **Exact match first** - Handles mixed-case symbols correctly
2. **Uppercase fallback** - Maintains compatibility with other symbols

This pattern ensures:
- Mixed-case symbols work (kBONK, kPEPE)
- Standard symbols still work (BTC, ETH, SOL)
- No breaking changes

---

## Files Modified

1. `src/nexwave/services/trading_engine/engine.py`
   - `get_market_data()` method
   - Lines 131-163

2. `src/nexwave/db/queries.py`
   - `get_candles()` method
   - `get_candles_count()` method
   - `get_price_statistics()` method
   - Lines 62-240

---

## Testing

### Manual Verification
```bash
# Check database has data
docker exec nexwave-postgres psql -U nexwave -d nexwave -c \
  "SELECT symbol, COUNT(*) FROM ticks WHERE symbol IN ('kBONK', 'kPEPE') GROUP BY symbol;"

# Check candles exist
docker exec nexwave-postgres psql -U nexwave -d nexwave -c \
  "SELECT symbol, COUNT(*) FROM candles_15m_ohlcv WHERE symbol IN ('kBONK', 'kPEPE') GROUP BY symbol;"

# Monitor logs
docker logs nexwave-trading-engine -f | grep -E "kBONK|kPEPE"
```

### Expected Results
- ✅ No "No market data available" warnings
- ✅ "Retrieved market data" debug messages
- ✅ "Signal Check" messages with candle counts > 0
- ✅ No "Not enough candles" warnings

---

## Related Issues

This fix also resolves similar issues for any other symbols with mixed case that might be added in the future.

---

## Commits

1. `016efbf` - fix: improve market data retrieval for kBONK and kPEPE symbols
2. `1a4a7a9` - fix: improve candle queries for kBONK and kPEPE symbols

---

## Status

✅ **RESOLVED** - All errors eliminated, both symbols processing correctly.

