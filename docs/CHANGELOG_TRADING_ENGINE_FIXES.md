# Trading Engine Diagnostic Logging Improvements

**Date:** November 8, 2025  
**Type:** Bug Fix / Enhancement  
**Priority:** High

---

## Summary

Fixed silent blocking issues in the trading engine that prevented visibility into why orders weren't being placed. Enhanced logging now provides clear diagnostic information about signal generation conditions.

---

## Changes Made

### 1. Enhanced Signal Generation Logging (`engine.py`)

**File:** `src/nexwave/services/trading_engine/engine.py`

- **Line 566:** Changed market data failures from `logger.debug()` to `logger.warning()` with clear message
  - **Before:** Silent skip when market data unavailable
  - **After:** Visible warning: "⚠️  No market data available for {symbol}, skipping signal generation"

- **Line 583:** Changed signal generation failures from `logger.debug()` to `logger.info()`
  - **Before:** Silent skip when no signal generated
  - **After:** Visible info: "{symbol}: No signal generated (VWM/volume conditions not met or already in position)"

- **Line 605:** Enhanced error logging with full stack traces
  - **Before:** Basic error message
  - **After:** Full stack trace with `exc_info=True` for better debugging

### 2. Enhanced Strategy Diagnostic Logging (`volume_weighted_momentum_strategy.py`)

**File:** `src/nexwave/strategies/volume_weighted_momentum_strategy.py`

- **Line 226:** Changed candle insufficiency from `logger.debug()` to `logger.warning()`
  - **Before:** Silent return when insufficient candles
  - **After:** Visible warning with count: "⚠️  Not enough candles for {symbol}: {count} < {required}. Need {missing} more candles."

- **Line 248:** Added comprehensive diagnostic logging for signal generation
  - **New:** INFO-level logging showing:
    - VWM value vs threshold
    - Volume ratio vs required multiplier
    - ATR value
    - Candle count
    - Volume confirmation status
  - **Format:** "{symbol} Signal Check: VWM={vwm} (threshold=±{threshold}), Volume={ratio}x (required={multiplier}x), ATR={atr}, Candles={count}, VolumeConfirmed={status}"

---

## Impact

### Before
- No visibility into why orders weren't being placed
- Silent failures when market data unavailable
- Silent failures when candle data insufficient
- No diagnostic information about signal generation conditions
- Difficult to debug production issues

### After
- Clear visibility into all blocking conditions
- Warning messages for data availability issues
- Detailed diagnostic information for each symbol on every signal check
- Easy identification of why signals aren't being generated
- Full stack traces for error debugging

---

## Root Cause Identified

The enhanced logging immediately revealed the root cause:

**Volume Condition Blocking:**
- All symbols showing `VolumeConfirmed=False`
- Volume ratios ranging from 0.67x to 0.97x
- Required volume multiplier: 1.2x
- **Result:** Signals not generated because volume condition not met, even when VWM conditions are satisfied

**Example from logs:**
```
XPL Signal Check: VWM=0.002219 (threshold=±0.001), Volume=0.94x (required=1.2x), VolumeConfirmed=False
```

---

## Testing

- ✅ Container rebuilt with `--no-cache` flag
- ✅ Container restarted with `--remove-orphans` flag
- ✅ New logging confirmed active in production logs
- ✅ Diagnostic information now visible at INFO level
- ✅ No breaking changes to signal generation logic

---

## Files Modified

1. `src/nexwave/services/trading_engine/engine.py`
   - Enhanced market data failure logging
   - Enhanced signal generation failure logging
   - Enhanced error logging with stack traces

2. `src/nexwave/strategies/volume_weighted_momentum_strategy.py`
   - Enhanced candle insufficiency logging
   - Added comprehensive signal diagnostic logging

3. `TRADING_ENGINE_BLOCKING_ISSUES.md` (new)
   - Complete audit documentation
   - Root cause analysis
   - Recommended fixes (all implemented)

---

## Related Documentation

- See `TRADING_ENGINE_BLOCKING_ISSUES.md` for complete audit details
- See `STRATEGY_EVALUATION_2025.md` for strategy evaluation context

---

## Notes

- All changes are backward compatible
- No changes to signal generation logic, only logging
- Logging level remains INFO (no DEBUG noise)
- Enhanced visibility without performance impact

