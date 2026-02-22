# TP/SL Bug Fix - November 8, 2025

## Problem

Orders were being placed successfully on Pacifica, but TP/SL (Take Profit/Stop Loss) parameters were not being attached to the orders.

### Root Cause

The trading engine (`engine.py`) was calling `PacificaClient.create_market_order()` with an `entry_price` parameter (line 331):

```python
response = await self.pacifica_client.create_market_order(
    symbol=signal.symbol,
    side=order_side,
    amount=rounded_amount,
    reduce_only=is_closing,
    client_order_id=client_order_id,
    stop_loss=stop_loss,
    take_profit=take_profit,
    entry_price=signal.price,  # Pass entry price for validation
)
```

However, the `create_market_order()` method signature in `pacifica_client.py` (line 300-310) did **not** accept this parameter:

```python
async def create_market_order(
    self,
    symbol: str,
    side: str,
    amount: float,
    reduce_only: bool = False,
    slippage_percent: float = 0.5,
    client_order_id: Optional[str] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    # entry_price: Optional[float] = None,  # <-- MISSING!
) -> Dict[str, Any]:
```

This caused a **TypeError** on every order placement attempt:

```
ERROR: PacificaClient.create_market_order() got an unexpected keyword argument 'entry_price'
```

As a result:
- ❌ All orders failed during TP/SL validation
- ❌ No orders were placed with TP/SL attached
- ❌ The validation logic at lines 342-360 couldn't execute because `entry_price` was undefined

### Error Log Evidence

```
[32m2025-11-08 20:09:14[0m | [1mINFO    [0m | [...] Placing bid order on Pacifica: MON 780.23
[31m[1mERROR   [0m | [...] PacificaClient.create_market_order() got an unexpected keyword argument 'entry_price'
[33m[1mWARNING [0m | [...] ⚠️  Order creation returned None for MON (buy). Check logs for errors.
```

This pattern repeated for every symbol that generated a trading signal.

## Solution

### Fix Applied

Added `entry_price` parameter to the `create_market_order()` method signature:

```python
async def create_market_order(
    self,
    symbol: str,
    side: str,
    amount: float,
    reduce_only: bool = False,
    slippage_percent: float = 0.5,
    client_order_id: Optional[str] = None,
    stop_loss: Optional[float] = None,
    take_profit: Optional[float] = None,
    entry_price: Optional[float] = None,  # ✅ ADDED
) -> Dict[str, Any]:
```

**File Modified:** `src/nexwave/services/order_management/pacifica_client.py`
**Lines Changed:** 300-311

### What This Enables

With `entry_price` now properly accepted, the TP/SL validation logic (lines 342-360) can execute correctly:

1. **Tick Size Rounding**: TP/SL prices are rounded to valid tick sizes for each symbol
   - BTC/ETH: 0.01 tick size
   - DOGE/kPEPE: 0.000001 tick size
   - Default: 0.0001 tick size

2. **Directional Validation**: Ensures TP/SL makes logical sense
   - **Long positions**: SL < entry_price, TP > entry_price
   - **Short positions**: SL > entry_price, TP < entry_price

3. **API Compliance**: Prevents Pacifica API rejections like:
   - ❌ "Take profit stop price 717.6186140714286 is not a multiple of tick size 0.01"
   - ✅ Prices now rounded correctly: 717.62

### Deployment

```bash
# Rebuild trading engine with fix
docker compose build --no-cache trading-engine

# Restart with new code
docker compose up -d --no-deps --remove-orphans trading-engine
```

**Container Restarted:** November 8, 2025 20:11:42 UTC

## Verification

### Expected Behavior (After Fix)

When a trading signal is generated with TP/SL:

1. ✅ Trading engine calls `create_market_order()` with `entry_price`
2. ✅ `validate_tpsl()` executes successfully
3. ✅ TP/SL prices are rounded to tick sizes
4. ✅ Validation logs show original vs rounded values:
   ```
   BTC TP/SL validation: entry=98500.00, SL=97000.00 (was 97000.15), TP=100000.00 (was 99999.87), tick_size=0.01
   ```
5. ✅ Order payload includes `stop_loss` and `take_profit` objects
6. ✅ Pacifica API accepts the order with TP/SL attached

### Logs to Monitor

```bash
# Watch for TP/SL validation logs
docker logs nexwave-trading-engine -f | grep -i "TP/SL"

# Watch for successful order placement
docker logs nexwave-trading-engine -f | grep "Order placed"
```

Look for:
- **Debug logs**: `{symbol} TP/SL validation: entry=..., SL=..., TP=...`
- **Info logs**: `Creating order with TP/SL for {symbol}: SL=..., TP=...`
- **Success logs**: `✅ Order placed: {symbol} {side} {amount} (pacifica_id=...) | SL=..., TP=...`

### Current Status

**Engine Status:** ✅ Running (restarted with fix)
**Next Signal:** Waiting for VWM conditions to be met
**Volume Threshold:** 1.2x (conservative, reduces signal frequency)
**Momentum Threshold:** 0.001 (0.1%)

The fix is deployed and ready. The next trading signal that meets VWM criteria will trigger an order with properly validated and rounded TP/SL values.

## Related Documentation

- **TP/SL Validation Logic**: See `TP_SL_VALIDATION.md`
- **Tick Size Mapping**: See `get_tick_size()` in `pacifica_client.py:158-188`
- **Validation Function**: See `validate_tpsl()` in `pacifica_client.py:196-287`

## Testing Notes

To manually test TP/SL attachment:
1. Lower volume threshold temporarily: `VWM_VOLUME_MULTIPLIER=0.8`
2. Restart trading engine
3. Wait for signal generation (every 60 seconds)
4. Check logs for TP/SL validation output
5. Verify order on Pacifica dashboard shows SL/TP attached

## Position Cleanup

### Closed Old Positions Without TP/SL

All 6 open positions that were created before the fix (without TP/SL) have been closed:

**Closed Positions (November 8, 2025 20:17 UTC):**
1. ✅ **ZEC**: 0.84 units @ $572.43 (order_id=881325545)
2. ✅ **BNB**: 0.28 units @ $994.35 (order_id=881325672)
3. ✅ **ASTER**: 210.17 units @ $1.02 (order_id=881325786)
4. ✅ **ETH**: 0.12 units @ $3374.23 (order_id=881325877)
5. ✅ **HYPE**: 9.37 units @ $40.08 (order_id=881325941)
6. ✅ **PUMP**: 21251 units @ $0.0037 (order_id=881326002)

**Total Closed:** 6 positions
**Method:** Market orders with `reduce_only=True`
**Script:** `close_positions.py`

All future positions will now be created with properly validated TP/SL attached.

## Date

**Fixed:** November 8, 2025 20:11 UTC
**Deployed:** November 8, 2025 20:11 UTC
**Positions Closed:** November 8, 2025 20:17 UTC
**Status:** ✅ Fully deployed, old positions cleaned up
