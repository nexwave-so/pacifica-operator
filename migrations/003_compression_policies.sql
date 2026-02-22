-- Compression Policies for TimescaleDB Tables and Continuous Aggregates
-- Compress data older than 30 days to save storage space

-- Enable compression on ticks table (segment by symbol for efficiency)
ALTER TABLE ticks SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'time DESC'
);

-- Add compression policy for ticks (compress after 30 days)
SELECT add_compression_policy(
    'ticks',
    compress_after => INTERVAL '30 days',
    if_not_exists => true
);

-- Enable compression on continuous aggregates
-- Compress 1-minute candles after 7 days
ALTER MATERIALIZED VIEW candles_1m SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_1m',
    compress_after => INTERVAL '7 days',
    if_not_exists => true
);

-- Compress 5-minute candles after 30 days
ALTER MATERIALIZED VIEW candles_5m SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_5m',
    compress_after => INTERVAL '30 days',
    if_not_exists => true
);

-- Compress 15-minute candles after 60 days
ALTER MATERIALIZED VIEW candles_15m SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_15m',
    compress_after => INTERVAL '60 days',
    if_not_exists => true
);

-- Compress 1-hour candles after 90 days
ALTER MATERIALIZED VIEW candles_1h SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_1h',
    compress_after => INTERVAL '90 days',
    if_not_exists => true
);

-- Compress 4-hour candles after 180 days
ALTER MATERIALIZED VIEW candles_4h SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_4h',
    compress_after => INTERVAL '180 days',
    if_not_exists => true
);

-- Compress 1-day candles after 365 days
ALTER MATERIALIZED VIEW candles_1d SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'symbol',
    timescaledb.compress_orderby = 'bucket DESC'
);

SELECT add_compression_policy(
    'candles_1d',
    compress_after => INTERVAL '365 days',
    if_not_exists => true
);

-- Optional: Add retention policies (uncomment if needed)
-- These will automatically drop data older than specified interval

-- Retain tick data for 90 days
-- SELECT add_retention_policy(
--     'ticks',
--     drop_after => INTERVAL '90 days',
--     if_not_exists => true
-- );

-- Retain 1-minute candles for 30 days
-- SELECT add_retention_policy(
--     'candles_1m',
--     drop_after => INTERVAL '30 days',
--     if_not_exists => true
-- );

