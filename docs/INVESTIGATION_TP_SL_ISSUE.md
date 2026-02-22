# Investigation: Orders Without TP/SL via Pacifica API

## Issue
Orders cannot be placed without TP/SL via the Pacifica API. All orders are failing with 400 errors.

## Root Cause Analysis

### Current Behavior
1. **Strategy Always Generates TP/SL**: The `VolumeWeightedMomentumStrategy` always calculates `stop_loss` and `take_profit` values (lines 416-417 in `volume_weighted_momentum_strategy.py`). These are never `None`.

2. **TP/SL Prices Not Rounded to Tick Size**: When TP/SL is included, the prices must match the symbol's tick size requirements. Current errors show:
   - `"Take profit stop price 717.6186140714286 is not a multiple of tick size 0.01"`
   - `"Take profit stop price 0.3024176428571429 is not a multiple of tick size 0.0001"`

3. **API Validation**: The Pacifica API validates that:
   - Order amounts must be multiples of lot size
   - TP/SL prices must be multiples of tick size (when provided)

### Findings

**API Error Patterns:**
1. **Tick Size Errors** (when TP/SL included):
   ```
   "Take profit stop price X is not a multiple of tick size Y"
   "Stop loss stop price X is not a multiple of tick size Y"
   ```

2. **Lot Size Errors** (separate issue):
   ```
   "Market order amount X is not a multiple of lot size Y"
   ```

### Solution Options

#### Option 1: Place Orders Without TP/SL (Immediate Fix)
- Modify strategy to allow `None` for TP/SL
- Skip TP/SL in order creation when values are invalid or None
- Test that orders can be placed successfully without TP/SL

#### Option 2: Fix TP/SL Tick Size Rounding (Proper Fix)
- Fetch symbol metadata (tick size, lot size) from Pacifica API
- Round TP/SL prices to correct tick size before including in order
- This requires symbol-specific configuration

#### Option 3: Make TP/SL Optional in Strategy
- Add configuration to enable/disable TP/SL generation
- Allow strategy to generate signals without TP/SL when disabled

## Current Implementation Status

### Code Changes Made
1. **`pacifica_client.py`**: 
   - Updated TP/SL inclusion logic to check `is not None and > 0`
   - Added debug logging for TP/SL inclusion

2. **`engine.py`**:
   - Added validation to only include TP/SL if both are valid (> 0)
   - However, strategy always generates TP/SL values, so this doesn't help yet

### Next Steps
1. **Test orders without TP/SL**: Temporarily set TP/SL to None in strategy to verify API accepts orders without TP/SL
2. **Implement tick size rounding**: Fetch symbol metadata and round TP/SL prices appropriately
3. **Make TP/SL optional**: Add configuration flag to enable/disable TP/SL generation

## Testing

To test orders without TP/SL:
1. Modify strategy to return `None` for `stop_loss` and `take_profit`
2. Verify orders are placed successfully
3. Confirm API accepts orders without TP/SL fields

## Implementation

### Changes Made
1. **Strategy TP/SL Calculation**: Made TP/SL optional - set to `None` if:
   - ATR is invalid or zero
   - Price calculation fails
   - Calculated values are invalid (e.g., negative, wrong direction)

2. **Order Creation**: Only include TP/SL in payload if both are valid (> 0)

3. **Debug Logging**: Added logging to show when orders are created with/without TP/SL

### Current Status
- Orders CAN be created without TP/SL (when strategy sets them to None)
- However, most signals still have valid TP/SL values
- The remaining issue is **tick size rounding** for TP/SL prices

### Remaining Issues
1. **Tick Size Rounding**: TP/SL prices must be rounded to symbol-specific tick sizes
   - Example: `"Take profit stop price 717.6186140714286 is not a multiple of tick size 0.01"`
   - Solution: Fetch symbol metadata and round TP/SL prices appropriately

2. **Lot Size Rounding**: Order amounts must be rounded to symbol-specific lot sizes
   - Example: `"Market order amount 39.36 is not a multiple of lot size 0.1"`
   - Solution: Fetch symbol metadata and round amounts appropriately

## Conclusion

**Answer to "Why can't we place orders without TP/SL?":**
- We CAN place orders without TP/SL - the API accepts them
- The current issue is that TP/SL prices aren't rounded to tick sizes
- When TP/SL is None (invalid calculation), orders are created without TP/SL
- The strategy now validates TP/SL and sets to None when invalid

**Next Steps:**
1. Implement symbol metadata fetching (tick size, lot size)
2. Round TP/SL prices to correct tick sizes
3. Round order amounts to correct lot sizes

## Date
2025-11-08

