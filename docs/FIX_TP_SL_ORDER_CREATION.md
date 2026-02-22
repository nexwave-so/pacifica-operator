# Fix: Stop Loss and Take Profit in Order Creation

## Issue
Stop loss and take profit were not being set on orders. The system was attempting to set TP/SL via a separate API call after order creation, which was failing with authorization errors:
```
"HVXrj9PFN5sLqkvWhs5quGsQHKsbaeb75sroPtTiCUWU is unauthorized to sign on behalf of HVXrj9PFN5sLqkvWhs5quGsQHKsbaeb75sroPtTiCUWU"
```

## Root Cause
According to Pacifica DEX API documentation, stop loss and take profit must be included **directly in the order creation payload**, not set via a separate endpoint. The previous implementation tried to set TP/SL after order placement using `/positions/tpsl`, which requires different authorization.

## Solution
Modified the order creation flow to include TP/SL parameters directly in the market order payload:

### Changes Made

1. **`pacifica_client.py`** - Updated `create_market_order()`:
   - Added `stop_loss` and `take_profit` parameters to function signature
   - Added logic to include TP/SL objects in the order payload when provided
   - TP/SL objects include `stop_price` and `limit_price` (with 0.1% slippage buffer)

2. **`engine.py`** - Updated order creation:
   - Pass `stop_loss` and `take_profit` directly to `create_market_order()`
   - Removed separate `set_position_tpsl()` call
   - Updated logging to show TP/SL values in order confirmation

### Technical Details

**TP/SL Payload Structure:**
```json
{
  "stop_loss": {
    "stop_price": "48000",
    "limit_price": "47950"
  },
  "take_profit": {
    "stop_price": "55000",
    "limit_price": "54950"
  }
}
```

**Slippage Calculation:**
- For long positions (bid): limit_price = stop_price * (1 - 0.001)
- For short positions (ask): limit_price = stop_price * (1 + 0.001)
- This ensures the limit order executes even with slight price movement

## Benefits
- ✅ TP/SL is now set atomically with order creation
- ✅ No separate API call needed (reduces latency and potential failures)
- ✅ Proper authorization (uses same signature as order creation)
- ✅ Better logging shows TP/SL values in order confirmations

## Testing
After deployment, orders should include TP/SL in the order creation payload. Logs will show:
```
✅ Order placed: ETH bid 0.0158 (pacifica_id=880946210) | SL=3350.00, TP=3400.00
🛡️  TP/SL included in order: ETH SL=3350.00, TP=3400.00
```

## Date
2025-11-08

