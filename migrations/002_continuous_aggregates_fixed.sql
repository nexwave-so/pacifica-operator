-- TimescaleDB Continuous Aggregates for Candle Generation (Fixed)
-- Create aggregates directly from ticks table (not chained)

-- Ensure TimescaleDB Toolkit is installed
CREATE EXTENSION IF NOT EXISTS timescaledb_toolkit;

-- 1-minute candles already exist, skip

-- Create 5-minute candles directly from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_5m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('5 minutes', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'candles_5m',
    start_offset => INTERVAL '12 hours',
    end_offset => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => true
);

-- Create 15-minute candles directly from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'candles_15m',
    start_offset => INTERVAL '1 day',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => true
);

-- Create 1-hour candles directly from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'candles_1h',
    start_offset => INTERVAL '7 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => true
);

-- Create 4-hour candles directly from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_4h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('4 hours', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'candles_4h',
    start_offset => INTERVAL '30 days',
    end_offset => INTERVAL '4 hours',
    schedule_interval => INTERVAL '4 hours',
    if_not_exists => true
);

-- Create 1-day candles directly from ticks
CREATE MATERIALIZED VIEW IF NOT EXISTS candles_1d
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 day', time) AS bucket,
    symbol,
    candlestick_agg(time, price, volume) AS candlestick
FROM ticks
GROUP BY bucket, symbol
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
    'candles_1d',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '1 day',
    schedule_interval => INTERVAL '1 day',
    if_not_exists => true
);

-- Create indexes on continuous aggregates
CREATE INDEX IF NOT EXISTS idx_candles_5m_symbol_bucket ON candles_5m (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_15m_symbol_bucket ON candles_15m (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_1h_symbol_bucket ON candles_1h (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_4h_symbol_bucket ON candles_4h (symbol, bucket DESC);
CREATE INDEX IF NOT EXISTS idx_candles_1d_symbol_bucket ON candles_1d (symbol, bucket DESC);

-- Create OHLCV helper views
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
