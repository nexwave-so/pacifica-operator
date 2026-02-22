# TP/SL Validation and Rounding

## Overview
To ensure orders with TP/SL are accepted by the Pacifica API, we validate and round TP/SL prices to match symbol-specific tick size requirements.

## Validation Process

### 1. **Tick Size Detection**
The system uses a tick size mapping for known symbols, with a fallback default:
- **High-value assets** (BTC, ETH, BNB, ZEC): `0.01`
- **Mid-value assets** (LINK, UNI): `0.0001`
- **Low-value assets** (DOGE, kPEPE, kBONK): `0.000001`
- **Default fallback**: `0.0001`

**Note**: Ideally, tick sizes should be fetched from Pacifica API symbol metadata. The current implementation uses a mapping based on observed error messages.

### 2. **Price Rounding**
All TP/SL prices are rounded to the nearest valid tick size:
```python
rounded_price = round(price / tick_size) * tick_size
```

### 3. **Directional Validation**

#### For Long Positions (bid):
- **Stop Loss**: Must be **below** entry price
  - If SL >= entry: Set to `None` (invalid)
  - After rounding, if SL >= entry: Round down one more tick
  
- **Take Profit**: Must be **above** entry price
  - If TP <= entry: Set to `None` (invalid)
  - After rounding, if TP <= entry: Round up one more tick

#### For Short Positions (ask):
- **Stop Loss**: Must be **above** entry price
  - If SL <= entry: Set to `None` (invalid)
  - After rounding, if SL <= entry: Round up one more tick
  
- **Take Profit**: Must be **below** entry price
  - If TP >= entry: Set to `None` (invalid)
  - After rounding, if TP >= entry: Round down one more tick

### 4. **Limit Price Rounding**
Both `stop_price` and `limit_price` in TP/SL objects are rounded to tick size:
- `limit_price` = `stop_price * (1 ± slippage)` (0.1% slippage)
- Both values rounded to tick size

## Implementation

### Functions

#### `get_tick_size(symbol: str) -> float`
Returns the tick size for a symbol based on the mapping or default.

#### `round_to_tick_size(price: float, tick_size: float) -> float`
Rounds a price to the nearest valid tick size.

#### `validate_tpsl(symbol, side, entry_price, stop_loss, take_profit) -> (validated_sl, validated_tp)`
Validates and rounds TP/SL prices:
1. Checks directional validity (SL/TP relative to entry)
2. Rounds to tick size
3. Ensures still valid after rounding
4. Returns `(None, None)` if invalid

### Usage

```python
# In create_market_order()
validated_sl, validated_tp = self.validate_tpsl(
    symbol, side, entry_price, stop_loss, take_profit
)

# Only include in payload if validated
if validated_sl:
    payload["stop_loss"] = {
        "stop_price": str(validated_sl),
        "limit_price": str(rounded_limit_price),
    }
```

## Error Prevention

### Before Validation:
- ❌ `"Take profit stop price 717.6186140714286 is not a multiple of tick size 0.01"`
- ❌ `"Stop loss stop price 0.3024176428571429 is not a multiple of tick size 0.0001"`

### After Validation:
- ✅ Prices rounded to valid tick sizes
- ✅ Directional validation ensures logical TP/SL placement
- ✅ Invalid TP/SL set to `None` (order placed without TP/SL)

## Logging

The system logs:
- **TP/SL validation results**: Shows original and validated values
- **Invalid TP/SL warnings**: When TP/SL is rejected due to directional issues
- **Order creation**: Whether order includes TP/SL or not

Example log:
```
{symbol} TP/SL validation: entry=3372.24, SL=3350.00 (was 3349.876), TP=3400.00 (was 3399.543), tick_size=0.01
```

## Future Improvements

1. **Fetch from API**: Get tick size and lot size from Pacifica API symbol metadata endpoint
2. **Cache metadata**: Cache symbol metadata to avoid repeated API calls
3. **Dynamic updates**: Update tick size mapping based on API error messages
4. **Lot size rounding**: Apply similar validation to order amounts

## Date
2025-11-08

