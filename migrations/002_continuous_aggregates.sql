-- TimescaleDB Continuous Aggregates for Candle Generation
-- This migration creates materialized views that automatically aggregate tick data into candles

-- Ensure TimescaleDB Toolkit is installed (required for candlestick functions)
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;

-- Create 1-minute candles using candlestick_agg
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 1-minute candles (updates every minute)
SELECT add_continuous_aggregate_policy(
    'candles_1m',
    start_offset => INTERVAL '3 hours',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => true
);

-- Create 5-minute candles using rollup from 1m
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', bucket) AS bucket,
    symbol,
    rollup(candlestick) AS candlestick
FROM candles_1m
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 5-minute candles
SELECT add_continuous_aggregate_policy(
    'candles_5m',
    start_offset => INTERVAL '12 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => true
);

-- Create 15-minute candles using rollup from 5m
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', bucket) AS bucket,
    symbol,
    rollup(candlestick) AS candlestick
FROM candles_5m
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 15-minute candles
SELECT add_continuous_aggregate_policy(
    'candles_15m',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => true
);

-- Create 1-hour candles using rollup from 15m
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', bucket) AS bucket,
    symbol,
    rollup(candlestick) AS candlestick
FROM candles_15m
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 1-hour candles
SELECT add_continuous_aggregate_policy(
    'candles_1h',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true
);

-- Create 4-hour candles using rollup from 1h
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_4h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('4 hours', bucket) AS bucket,
    symbol,
    rollup(candlestick) AS candlestick
FROM candles_1h
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 4-hour candles
SELECT add_continuous_aggregate_policy(
    'candles_4h',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '4 hours',
    schedule_interval => INTERVAL '4 hours',
    if_not_exists => true
);

-- Create 1-day candles using rollup from 4h
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', bucket) AS bucket,
    symbol,
    rollup(candlestick) AS candlestick
FROM candles_4h
GROUP BY bucket, symbol
WITH NO DATA;

-- Add refresh policy for 1-day candles
SELECT add_continuous_aggregate_policy(
    'candles_1d',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => true
);

-- Create indexes on continuous aggregates for fast queries
CREATE INDEX IF NOT EXISTS idx_candles_1m_symbol_bucket ON candles_1m (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_5m_symbol_bucket ON candles_5m (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_15m_symbol_bucket ON candles_15m (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_1h_symbol_bucket ON candles_1h (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_4h_symbol_bucket ON candles_4h (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_1d_symbol_bucket ON candles_1d (symbol, bucket DESC);

-- Create helper view to easily query OHLCV data
CREATE OR REPLACE VIEW candles_1m_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_1m;

CREATE OR REPLACE VIEW candles_5m_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_5m;

CREATE OR REPLACE VIEW candles_15m_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_15m;

CREATE OR REPLACE VIEW candles_1h_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_1h;

CREATE OR REPLACE VIEW candles_4h_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_4h;

CREATE OR REPLACE VIEW candles_1d_ohlcv AS
SELECT
    bucket AS time,
    symbol,
    open(candlestick) AS open,
    high(candlestick) AS high,
    low(candlestick) AS low,
    close(candlestick) AS close,
    volume(candlestick) AS volume,
    vwap(candlestick) AS vwap
FROM candles_1d;

-- Grant permissions
GRANT SELECT ON ALL TABLES IN SCHEMA public TO nexwave;
GRANT SELECT ON ALL MATERIALIZED VIEWS IN SCHEMA public TO nexwave;

