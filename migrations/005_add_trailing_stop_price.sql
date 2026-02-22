-- Migration: Add trailing_stop_price column to positions table
-- Date: 2025-11-11
-- Description: Add support for trailing stop loss feature

BEGIN;

-- Add trailing_stop_price column to positions table
ALTER TABLE positions
ADD COLUMN IF NOT EXISTS trailing_stop_price DOUBLE PRECISION;

-- Add comment for documentation
COMMENT ON COLUMN positions.trailing_stop_price IS 'Trailing stop price level for advanced position management (activates at 2x ATR profit)';

COMMIT;
