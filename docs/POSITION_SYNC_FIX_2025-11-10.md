# Position Sync Fix - November 10, 2025

## Overview

Fixed critical issue where closed positions on Pacifica DEX were not being removed from Nexwave's local database, causing the dashboard to display stale positions and generating errors when the trading engine tried to close already-closed positions.

## Problem Description

### Symptoms
- Dashboard showed 16 positions, but Pacifica API returned 0 active positions
- Trading engine logs showing repeated errors:
  ```
  ERROR: Pacifica API error: 422
  API error details: {"error":"No position found for reduce-only order: HVXrj9PFN5sLqkvWhs5quGsQHKsbaeb75sroPtTiCUWU WLFI"}
  ```
- VWM strategy generating close signals for positions that were already closed on exchange
- Position sync logging "No positions from Pacifica" but database contained 16 positions

### Root Cause
The `sync_positions_from_pacifica()` function only handled two scenarios:
1. **Updating** existing positions when they existed on Pacifica
2. **Creating** new positions when found on Pacifica but not in DB

It was missing a critical third scenario:
3. **Deleting** positions from DB when they no longer exist on Pacifica

When positions were closed on Pacifica (manually or via stop loss/take profit), the sync would see an empty response from Pacifica and do nothing, leaving stale positions in the database indefinitely.

## Solution

### Code Changes

**File:** `src/nexwave/services/trading_engine/engine.py`

Modified the `sync_positions_from_pacifica()` method (lines 472-577) to:

1. **Fetch both sides**: Get all positions from database AND from Pacifica API
2. **Build active set**: Create set of symbols that have active positions on Pacifica
3. **Delete stale positions**: Loop through database positions and delete any not in Pacifica's active set
4. **Update/create as before**: Continue with existing update and create logic

### Key Logic

```python
# Get all our current positions
result = await session.execute(
    select(Position).where(
        Position.strategy_id == self.strategy_id
    )
)
db_positions = result.scalars().all()

# Create set of symbols from Pacifica (active positions)
pacifica_symbols = {p.get('symbol') for p in pacifica_positions if float(p.get('amount', 0)) > 0}

# Delete positions that no longer exist on Pacifica
deleted_count = 0
for db_pos in db_positions:
    if db_pos.symbol not in pacifica_symbols:
        logger.info(
            f"🗑️  Removing closed position from database: {db_pos.symbol} "
            f"({db_pos.amount} @ ${db_pos.entry_price:.4f})"
        )
        await session.delete(db_pos)
        deleted_count += 1
```

### Enhanced Logging

Updated sync completion message to show all operations:
```python
logger.info(
    f"Position sync complete: {len(pacifica_positions)} active, "
    f"{updated_count} updated, {created_count} created, {deleted_count} deleted"
)
```

## Results

### Initial Sync (First Run After Fix)

```
[18:35:38] INFO - 🗑️  Removing closed position from database: VIRTUAL (49.5 @ $1.6078)
[18:35:38] INFO - 🗑️  Removing closed position from database: FARTCOIN (235.9 @ $0.3376)
[18:35:38] INFO - 🗑️  Removing closed position from database: 2Z (180.0 @ $0.1992)
[18:35:38] INFO - 🗑️  Removing closed position from database: BNB (0.05 @ $1015.1900)
[18:35:38] INFO - 🗑️  Removing closed position from database: XRP (30.0 @ $2.4251)
[18:35:38] INFO - 🗑️  Removing closed position from database: ASTER (53.9 @ $1.1244)
[18:35:38] INFO - 🗑️  Removing closed position from database: PENGU (4048.0 @ $0.0158)
[18:35:38] INFO - 🗑️  Removing closed position from database: LDO (64.7 @ $0.8621)
[18:35:38] INFO - 🗑️  Removing closed position from database: CRV (112.9 @ $0.4928)
[18:35:38] INFO - 🗑️  Removing closed position from database: ENA (207.0 @ $0.3410)
[18:35:38] INFO - 🗑️  Removing closed position from database: XPL (242.0 @ $0.3286)
[18:35:38] INFO - 🗑️  Removing closed position from database: WLFI (601.0 @ $0.1324)
[18:35:38] INFO - 🗑️  Removing closed position from database: PUMP (15296.0 @ $0.0043)
[18:35:38] INFO - 🗑️  Removing closed position from database: MON (549.0 @ $0.0592)
[18:35:38] INFO - 🗑️  Removing closed position from database: ZEC (0.1 @ $649.2000)
[18:35:38] INFO - 🗑️  Removing closed position from database: SUI (25.8 @ $2.1764)
[18:35:38] INFO - Position sync complete: 0 active, 0 updated, 0 created, 16 deleted
```

### Verification

**Database Check:**
```sql
SELECT COUNT(*) FROM positions;
-- Before: 16 positions
-- After:  1 position (legitimate new ZEC short opened during startup)
```

**API Check:**
```bash
curl http://localhost:8000/api/v1/positions
# Response: {"positions": [{"symbol": "ZEC", "side": "ASK", "amount": 0.1, ...}]}
```

**Pacifica API Check:**
```python
pacifica_client.get_positions()
# Response: {'success': True, 'data': [{'symbol': 'ZEC', 'side': 'ask', 'amount': '0.1', ...}]}
```

Dashboard now shows exactly 1 position, matching Pacifica exactly.

## Impact

### Before Fix
- ❌ Dashboard showed 16 stale positions
- ❌ Trading engine generated close signals for non-existent positions
- ❌ "No position found" errors every 60 seconds
- ❌ Impossible to determine actual trading state
- ❌ Database bloat with closed positions

### After Fix
- ✅ Dashboard shows only active positions
- ✅ Database automatically cleaned when positions close
- ✅ No more "position not found" errors
- ✅ Position sync reports deleted count
- ✅ Real-time accuracy between dashboard and exchange
- ✅ Runs every 60 seconds automatically

## Technical Details

### Sync Frequency
Position sync runs on two schedules:
1. **Startup**: Immediate sync when trading engine starts
2. **Periodic**: Every 60 seconds during signal processing loop

### Edge Cases Handled
- **Empty Pacifica response**: When all positions closed, deletes all DB positions
- **Partial matches**: Updates positions that exist on both sides, deletes others
- **New positions**: Creates positions found on Pacifica but not in DB
- **Amount = 0**: Treats zero-amount positions as closed (excluded from active set)

### Transaction Safety
All database operations (deletes, updates, creates) happen within a single async session transaction:
```python
async with AsyncSessionLocal() as session:
    # ... all operations ...
    await session.commit()
```

If any error occurs, entire transaction rolls back, maintaining database consistency.

## Testing

### Manual Testing
```bash
# 1. Check Pacifica positions
docker exec nexwave-trading-engine python3 -c "
from nexwave.services.order_management.pacifica_client import PacificaClient
import asyncio
asyncio.run(PacificaClient().get_positions())
"

# 2. Check database positions
docker exec nexwave-postgres psql -U nexwave -d nexwave -c "SELECT COUNT(*) FROM positions;"

# 3. Check API positions
curl http://localhost:8000/api/v1/positions | jq '.positions | length'

# 4. Monitor sync logs
docker logs nexwave-trading-engine -f | grep "Position sync complete"
```

### Expected Behavior
- Counts should match across all three sources
- Sync logs should show "0 deleted" when positions match
- Deleted positions should log with 🗑️ emoji and details
- No "No position found" errors in trading engine logs

## Files Modified

1. **src/nexwave/services/trading_engine/engine.py** (lines 472-577)
   - Enhanced `sync_positions_from_pacifica()` method
   - Added position deletion logic
   - Improved logging with operation counts

2. **docker/Dockerfile.trading-engine**
   - Rebuilt container to include updated code

## Deployment

```bash
# Rebuild trading engine with fix
docker compose build --no-cache trading-engine

# Restart with new image
docker compose up -d --remove-orphans trading-engine

# Verify sync working
docker logs nexwave-trading-engine | grep "Removing closed position"
```

## Future Improvements

1. **Realized P&L Tracking**: When position deleted, calculate and store realized P&L
2. **Position History**: Archive closed positions to `positions_history` table instead of deleting
3. **Sync on Position Close**: Trigger immediate sync when close signal executed
4. **Metrics**: Track sync statistics (avg deletes per day, sync duration, etc.)
5. **Alerting**: Notify when large number of positions deleted (possible sync issue)

## Related Issues

- Fixed order execution errors for positions that no longer exist
- Resolved dashboard showing outdated position data
- Eliminated confusion between actual and displayed trading state

## Commit

```
fix: sync closed positions from Pacifica and remove from database

- Modified sync_positions_from_pacifica() to delete DB positions not on Pacifica
- Prevents stale positions in dashboard after positions close on exchange
- Eliminated "No position found for reduce-only order" errors
- Added detailed logging for deleted positions with 🗑️ emoji
- Position sync now reports: active, updated, created, deleted counts
- Successfully removed 16 stale positions on first sync after fix
```

---

**Author:** Claude Code
**Date:** November 10, 2025
**Tested:** Production deployment on nexwave.so
**Status:** ✅ Deployed and verified working
