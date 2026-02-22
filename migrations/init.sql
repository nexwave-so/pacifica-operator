-- Nexwave Database Initialization Script
-- TimescaleDB setup for tick data and continuous aggregates

-- Enable TimescaleDB extension
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;

-- Create ticks hypertable (will be created by Alembic models, but ensure it's a hypertable)
-- This should be run after tables are created by Alembic
-- SELECT create_hypertable('ticks', 'time', chunk_time_interval => INTERVAL '1 day');

-- Create candles via continuous aggregates
-- Note: These will be created after ticks table exists

-- Compression policies (run after tables are populated)
-- ALTER TABLE ticks SET (
--     timescaledb.compress,
--     timescaledb.compress_segmentby = 'symbol',
--     timescaledb.compress_orderby = 'time DESC'
-- );
-- SELECT add_compression_policy('ticks', compress_after => INTERVAL '7 days');

-- Retention policy
-- SELECT add_retention_policy('ticks', drop_after => INTERVAL '90 days');

