# Data Pipeline Status & Candle Warnings Analysis

**Date:** January 30, 2026  
**Time:** 03:25 UTC

## Executive Summary

The trading engine is **partially operational**. The Short-Term Momentum Strategy (5m scalper) has sufficient data and is ready to trade, but Long-Term strategies are blocked due to insufficient historical data. **The main issue is a hardcoded 5% breakout threshold preventing trades.**

## Current Data Status

### Candle Data by Timeframe

| Timeframe | Per Symbol (BTC/ETH/SOL) | Data Span | Status |
|-----------|---------------------------|-----------|--------|
| **5m** | 74 candles | 6h 10min | ✅ **Ready** |
| **1h** | 5 candles | 5 hours | ⚠️ **Limited** |
| **1d** | 0 candles | 0 hours | ❌ **None** |

**Data Collection Start:** January 29, 2026 @ 21:15 UTC  
**Current Runtime:** 6 hours, 10 minutes

## Trading Strategy Status

### 1. Short-Term Momentum Strategy ✅ DATA READY / ❌ NOT TRADING

- **Timeframe:** 5m
- **Lookback Required:** 20 candles
- **Current Data:** 74 candles ✅
- **Status:** Has data but **NOT trading due to overly strict entry criteria**

**Why No Trades?**

The strategy requires a **5% breakout** from the highest high in the lookback period:

```python
# src/nexwave/strategies/momentum/short_term_momentum.py:34
self.breakout_threshold = 1.05  # 5% breakout required
```

Entry conditions:
- **Long:** Price > highest_high * 1.05 (5% above recent high)
- **Short:** Price < lowest_low / 1.05 (5% below recent low)
- **Volume:** Current > 0.3x average (easily met)

**Problem:** A 5% breakout is extremely rare in normal market conditions. BTC would need to move from $82,000 to $86,100+ within the 100-minute lookback period.

### 2. Long-Term Momentum Strategy ❌ WAITING FOR DATA

- **Timeframe:** 1d (daily)
- **Lookback Required:** 10 days
- **Current Data:** 0 daily candles
- **ETA:** **8 more days** (February 7, 2026)

### 3. Momentum Short Strategy ❌ WAITING FOR DATA

- **Timeframe:** 1d (daily)
- **Lookback Required:** 14 days
- **Current Data:** 0 daily candles
- **ETA:** **12 more days** (February 11, 2026)

## Why No Daily Candles Yet?

Daily candles form on 24-hour UTC boundaries (00:00-23:59). Data collection started at 21:15 UTC (mid-day), so:

- **First complete day:** Today (Jan 30) 00:00-23:59 UTC
- **First daily candle available:** Tomorrow (Jan 31) @ ~00:23 UTC after refresh
- **10 days of data:** February 9, 2026
- **14 days of data:** February 13, 2026

## Recommendations

### IMMEDIATE FIX: Lower Breakout Threshold

**Option 1: Quick Code Change** (Recommended)

Edit `src/nexwave/strategies/momentum/short_term_momentum.py:34`:

```python
# Change from:
self.breakout_threshold = 1.05  # 5%

# To:
self.breakout_threshold = 1.015  # 1.5% (more realistic)
```

**Option 2: Make Configurable**

Add to `.env`:
```bash
VWM_BREAKOUT_THRESHOLD=1.015  # 1.5%
```

Then update strategy to read from config:
```python
self.breakout_threshold = getattr(settings, "vwm_breakout_threshold", 1.02)
```

### Testing & Monitoring

After lowering the threshold:

1. **Restart trading engine:** `docker compose restart trading-engine`
2. **Monitor logs:** `docker logs -f nexwave-trading-engine`
3. **Expected behavior:** Should see signals within 1-2 hours during active market hours
4. **Watch for:**
   - Signal generation messages
   - Entry/exit decisions
   - Risk manager filters (blacklist, cooldown, etc.)

### Alternative: Disable Long-Term Strategies

Until daily data accumulates (8-14 days), consider temporarily disabling long-term strategies to reduce log noise.

## Next Milestones

| Date | Milestone | Impact |
|------|-----------|--------|
| **Now** | Fix breakout threshold | Short-term strategy can trade |
| Jan 31 @ 00:23 UTC | First daily candle | Still need 9 more days |
| Feb 9, 2026 | 10 daily candles | Long-Term Momentum ready |
| Feb 13, 2026 | 14 daily candles | Momentum Short ready |

## Continuous Aggregate Refresh Schedule

- **5m candles:** Every 5 minutes (next: 03:28 UTC)
- **1h candles:** Every 1 hour (next: 03:23 UTC)
- **1d candles:** Every 24 hours (next: 21:23 UTC)

## Conclusion

**The trading engine is ready to trade but blocked by unrealistic entry criteria.**

**Action Required:** Lower `breakout_threshold` from 1.05 (5%) to 1.015-1.02 (1.5-2%) in the Short-Term Momentum Strategy.

**Timeline for Full Operation:** 8-14 days for long-term strategies to have sufficient data.

---
**Last Updated:** January 30, 2026 @ 03:25 UTC
